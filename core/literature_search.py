"""Literature retrieval with API throttling, quality filtering and task pools."""

from __future__ import annotations

import hashlib
import os
import re
import time
from typing import Optional

import requests

from .utils import setup_logging

logger = setup_logging("literature_search")

_SEARCH_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 1800
_last_request_time: float = 0
# The issued Semantic Scholar key permits one request per second.
_MIN_REQUEST_INTERVAL = 1.5
_LOW_VALUE_TITLE_MARKERS = {
    "editorial",
    "erratum",
    "correction",
    "retraction",
    "table of contents",
    "front matter",
    "conference program",
    "author index",
}
_TOKEN_STOPWORDS = {
    "based",
    "study",
    "research",
    "system",
    "using",
    "with",
    "from",
    "analysis",
    "method",
    "methods",
    "results",
    "paper",
    "the",
    "and",
}


def _cache_key(query: str, limit: int) -> str:
    return hashlib.md5(f"{query.lower().strip()}:{limit}".encode()).hexdigest()


def _get_from_cache(query: str, limit: int) -> Optional[list[dict]]:
    key = _cache_key(query, limit)
    cached = _SEARCH_CACHE.get(key)
    if cached is None:
        return None
    timestamp, data = cached
    if time.time() - timestamp < _CACHE_TTL:
        logger.info("  cache hit: '%s...' (%s papers)", query[:40], len(data))
        return [dict(item) for item in data]
    del _SEARCH_CACHE[key]
    return None


def _set_cache(query: str, limit: int, data: list[dict]) -> None:
    _SEARCH_CACHE[_cache_key(query, limit)] = (time.time(), [dict(item) for item in data])


def _rate_limit_wait() -> None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _parse_semantic_scholar(data: dict) -> list[dict]:
    papers = []
    for paper in data.get("data", []):
        authors = [author.get("name", "") for author in paper.get("authors", []) if author.get("name")]
        papers.append(
            {
                "citation_key": "",
                "title": paper.get("title", "Untitled"),
                "authors": authors,
                "year": paper.get("year") if isinstance(paper.get("year"), int) else None,
                "abstract": (paper.get("abstract") or "")[:500],
                "url": paper.get("url", ""),
                "venue": paper.get("venue", ""),
                "retrieval_source": "Semantic Scholar",
            }
        )
    return papers


def _search_semantic_scholar(query: str, limit: int) -> Optional[list[dict]]:
    params = {
        "query": query.strip(),
        "limit": min(limit, 10),
        "fields": "title,authors,year,abstract,url,venue",
    }
    headers: dict[str, str] = {}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    if api_key:
        headers["x-api-key"] = api_key
    _rate_limit_wait()
    response = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params=params,
        headers=headers,
        timeout=15,
    )
    if response.status_code == 429:
        logger.warning("  Semantic Scholar throttled (429)")
        return None
    response.raise_for_status()
    papers = _parse_semantic_scholar(response.json())
    logger.info("  Semantic Scholar: %s papers", len(papers))
    return papers


def _search_crossref(query: str, limit: int) -> Optional[list[dict]]:
    _rate_limit_wait()
    response = requests.get(
        "https://api.crossref.org/works",
        params={"query": query.strip(), "rows": min(limit, 10)},
        timeout=15,
    )
    if response.status_code == 429:
        logger.warning("  CrossRef throttled (429)")
        return None
    response.raise_for_status()
    papers = []
    for item in response.json().get("message", {}).get("items", []):
        authors = [
            f"{author.get('given', '')} {author.get('family', '')}".strip()
            for author in item.get("author", [])[:5]
            if author.get("family")
        ]
        parts = item.get("published-print", {}).get("date-parts", [[None]])[0]
        year = parts[0] if parts and parts[0] else item.get("created", {}).get("date-parts", [[None]])[0][0]
        papers.append(
            {
                "citation_key": "",
                "title": item.get("title", ["Untitled"])[0] if item.get("title") else "Untitled",
                "authors": authors,
                "year": year if isinstance(year, int) else None,
                "abstract": (item.get("abstract") or "")[:500],
                "url": item.get("URL", ""),
                "venue": item.get("container-title", [""])[0] if item.get("container-title") else "",
                "retrieval_source": "CrossRef",
            }
        )
    logger.info("  CrossRef: %s papers", len(papers))
    return papers


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}|[\u4e00-\u9fff]{2,}", str(text or "").lower())
    return {token for token in raw if token not in _TOKEN_STOPWORDS}


def _normalise_title(title: str) -> str:
    return re.sub(r"\W+", " ", str(title or "").lower()).strip()


def _matches_domain_scope(searchable_text: str, query: str) -> bool:
    """Require at least one domain anchor for narrow experimental topics."""
    query_lower = str(query or "").lower()
    searchable_lower = str(searchable_text or "").lower()
    if "motor imagery" in query_lower:
        return any(
            anchor in searchable_lower
            for anchor in ("motor imagery", "robot", "tactile", "rehabilit")
        )
    return True


def _filter_rank_dedupe(papers: list[dict], query: str, limit: int) -> list[dict]:
    query_tokens = _tokens(query)
    ranked: list[tuple[int, dict]] = []
    seen: set[str] = set()
    english_query = any(token.isascii() for token in query_tokens)
    for paper in papers:
        title = str(paper.get("title") or "").strip()
        title_key = _normalise_title(title)
        if not title_key or title_key == "untitled":
            continue
        if any(marker in title_key for marker in _LOW_VALUE_TITLE_MARKERS):
            continue
        if title_key in seen:
            continue
        searchable_text = f"{title} {paper.get('abstract', '')} {paper.get('venue', '')}"
        if not _matches_domain_scope(searchable_text, query):
            continue
        text_tokens = _tokens(searchable_text)
        title_tokens = _tokens(title)
        overlap = len(query_tokens & text_tokens)
        if english_query and overlap == 0:
            continue
        score = overlap * 3 + len(query_tokens & title_tokens) * 2
        score += 1 if paper.get("year") else 0
        score += 1 if paper.get("abstract") else 0
        seen.add(title_key)
        ranked.append((score, dict(paper)))
    ranked.sort(key=lambda entry: entry[0], reverse=True)
    selected = [paper for _, paper in ranked[:limit]]
    for index, paper in enumerate(selected):
        paper["citation_key"] = f"ref{index}"
    return selected


def search_papers(query: str, limit: int = 8) -> list[dict]:
    """Retrieve and clean papers for one focused search query."""
    if not query or not query.strip():
        return []
    cached = _get_from_cache(query, limit)
    if cached is not None:
        return cached
    try:
        semantic = _search_semantic_scholar(query, min(limit, 10)) or []
    except requests.RequestException as exc:
        logger.warning("  Semantic Scholar request failed: %s", exc)
        semantic = []
    try:
        crossref = _search_crossref(query, min(limit, 10)) or []
    except requests.RequestException as exc:
        logger.warning("  CrossRef request failed: %s", exc)
        crossref = []
    papers = _filter_rank_dedupe(semantic + crossref, query, limit)
    if not papers:
        logger.warning("  no relevant literature found for query: %s", query[:60])
        return []
    _set_cache(query, limit, papers)
    return papers


def search_paper_pool(queries: list[str], target_count: int = 15, per_query_limit: int = 8) -> list[dict]:
    """Retrieve a deduplicated reference pool from multiple focused queries."""
    unique_queries: list[str] = []
    seen_queries: set[str] = set()
    for query in queries:
        clean_query = str(query or "").strip()
        key = clean_query.lower()
        if clean_query and key not in seen_queries:
            unique_queries.append(clean_query)
            seen_queries.add(key)
    papers: list[dict] = []
    for query in unique_queries:
        papers.extend(search_papers(query, limit=per_query_limit))
        selected = _filter_rank_dedupe(papers, " ".join(unique_queries), target_count)
        if len(selected) >= target_count:
            break
    selected = _filter_rank_dedupe(papers, " ".join(unique_queries), target_count)
    logger.info("  literature pool: %s / target %s papers", len(selected), target_count)
    return selected


def format_papers_for_prompt(papers: list[dict]) -> str:
    lines = []
    for paper in papers:
        authors = ", ".join(paper.get("authors", [])[:3])
        if len(paper.get("authors", [])) > 3:
            authors += " et al."
        year = paper.get("year", "n.d.")
        title = paper.get("title", "Untitled")
        venue = paper.get("venue", "")
        venue_text = f" {venue}." if venue else ""
        lines.append(f"[{paper.get('citation_key', '?')}] {authors} ({year}). {title}.{venue_text}")
    return "\n".join(lines)
