"""Image candidate discovery and approval storage."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
PUBLIC_IMAGE_HEADERS = {
    "User-Agent": "paper-agent-v6/1.0 (academic document assistant; Wikimedia Commons attribution retained)"
}


class ImageAssetStore:
    """Persist searched image candidates and approved assets."""

    def __init__(self, path: str | Path = "data/checkpoints/image_assets.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._assets = self._load()

    def register_candidates(self, candidates: Iterable[dict]) -> list[dict]:
        existing = {asset["asset_id"]: asset for asset in self._assets}
        registered = []
        for candidate in candidates:
            asset = {
                "asset_id": candidate.get("asset_id") or f"img-{uuid.uuid4().hex[:10]}",
                "approved": bool(candidate.get("approved", False)),
                "local_path": candidate.get("local_path", ""),
                **candidate,
            }
            existing[asset["asset_id"]] = asset
            registered.append(asset)
        self._assets = list(existing.values())
        self._save()
        return registered

    def approve(self, asset_ids: Iterable[str]) -> list[dict]:
        wanted = set(asset_ids)
        approved = []
        for asset in self._assets:
            if asset["asset_id"] in wanted:
                asset["approved"] = True
                approved.append(asset)
        self._save()
        return approved

    def bind_uploaded_material(
        self,
        material: dict,
        *,
        section_id: str,
        purpose: str,
        caption: str,
        job_id: str = "",
        output_dir: str | Path | None = None,
    ) -> dict:
        """Turn a user-uploaded image material into a renderable image asset."""
        if not section_id.strip() or not caption.strip():
            raise ValueError("section_id and caption are required for uploaded images")
        asset_id = f"user-{job_id}-{material['material_id']}" if job_id else f"user-{material['material_id']}"
        local_path = str(material.get("local_path", ""))
        if output_dir and local_path and Path(local_path).is_file():
            target_dir = Path(output_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(local_path).suffix.lower() or ".png"
            target = target_dir / f"{asset_id}{suffix}"
            shutil.copy2(local_path, target)
            local_path = str(target.resolve())
        bound = {
            "asset_id": asset_id,
            "approved": True,
            "job_id": job_id,
            "material_id": material["material_id"],
            "title": material.get("metadata", {}).get("filename", "uploaded image"),
            "section_id": section_id,
            "purpose": purpose or "user_provided_image",
            "source": "user_upload",
            "source_url": material.get("source_path", "user_upload"),
            "image_url": "",
            "thumbnail_url": "",
            "license": "user_provided",
            "attribution": "user",
            "caption": caption,
            "local_path": local_path,
        }
        self.register_candidates([bound])
        return bound

    def approved_assets(self) -> list[dict]:
        return [dict(asset) for asset in self._assets if asset.get("approved")]

    def all_assets(self) -> list[dict]:
        return [dict(asset) for asset in self._assets]

    def download_approved(
        self,
        output_dir: str | Path = "data/assets/images",
        *,
        asset_ids: Iterable[str] | None = None,
    ) -> list[dict]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        session = requests.Session()
        session.headers.update(PUBLIC_IMAGE_HEADERS)
        wanted = set(asset_ids or [])
        changed = False
        for asset in self._assets:
            if wanted and asset.get("asset_id") not in wanted:
                continue
            if not asset.get("approved") or asset.get("local_path"):
                continue
            urls = list(dict.fromkeys(
                url for url in (asset.get("image_url"), asset.get("thumbnail_url")) if url
            ))
            if not urls:
                continue
            response = None
            downloaded_url = ""
            errors = []
            for url in urls:
                try:
                    response = session.get(url, timeout=30)
                    response.raise_for_status()
                    downloaded_url = url
                    break
                except requests.RequestException as exc:
                    errors.append(str(exc))
            if response is None or not downloaded_url:
                asset["download_error"] = " | ".join(errors)
                changed = True
                continue
            suffix = _guess_suffix(downloaded_url, response.headers.get("content-type", ""))
            target = output_dir / f"{asset['asset_id']}{suffix}"
            target.write_bytes(response.content)
            asset["local_path"] = str(target.resolve())
            asset["downloaded_url"] = downloaded_url
            asset.pop("download_error", None)
            asset["retrieved_at"] = asset.get("retrieved_at") or datetime.now().isoformat(timespec="seconds")
            changed = True
        if changed:
            self._save()
        return self.approved_assets()

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self):
        self.path.write_text(json.dumps(self._assets, ensure_ascii=False, indent=2), encoding="utf-8")


def search_commons_candidates(query: str, purpose: str = "", section_id: str = "", limit: int = 5) -> list[dict]:
    """Search Wikimedia Commons and return structured image candidates."""
    session = requests.Session()
    session.headers.update(PUBLIC_IMAGE_HEADERS)
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"file:{query}",
        "gsrnamespace": 6,
        "gsrlimit": max(1, min(limit, 10)),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 480,
    }
    response = session.get(COMMONS_API, params=params, timeout=30)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    candidates = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        metadata = info.get("extmetadata", {})
        candidates.append({
            "title": page.get("title", ""),
            "section_id": section_id,
            "purpose": purpose,
            "source": "wikimedia_commons",
            "source_url": info.get("descriptionurl", ""),
            "image_url": info.get("url", ""),
            "thumbnail_url": info.get("thumburl", ""),
            "license": _metadata_value(metadata, "LicenseShortName"),
            "attribution": _clean_metadata(_metadata_value(metadata, "Artist")),
            "caption": _clean_metadata(_metadata_value(metadata, "ImageDescription")) or page.get("title", ""),
            "query": query,
        })
    return candidates


def search_openverse_candidates(query: str, purpose: str = "", section_id: str = "", limit: int = 5) -> list[dict]:
    """Search Openverse for reusable images when Commons has no usable asset."""
    session = requests.Session()
    session.headers.update(PUBLIC_IMAGE_HEADERS)
    response = session.get(
        OPENVERSE_API,
        params={"q": query, "page_size": max(1, min(limit, 10))},
        timeout=30,
    )
    response.raise_for_status()
    candidates = []
    for item in response.json().get("results", []):
        image_url = item.get("url") or item.get("thumbnail") or ""
        candidates.append({
            "title": item.get("title") or query,
            "section_id": section_id,
            "purpose": purpose,
            "source": "openverse",
            "source_url": item.get("foreign_landing_url") or item.get("detail_url") or "",
            "image_url": image_url,
            "thumbnail_url": item.get("thumbnail") or "",
            "license": item.get("license") or "",
            "attribution": item.get("creator") or item.get("provider") or "",
            "caption": item.get("title") or query,
            "query": query,
        })
    return candidates


def search_planned_commons_candidates(
    title: str,
    asset_plan: Iterable[dict],
    *,
    section_titles: dict[str, str] | None = None,
    limit_per_requirement: int = 3,
) -> list[dict]:
    """Search Commons for outline image requirements that need real visual assets."""
    section_titles = section_titles or {}
    candidates = []
    for requirement in asset_plan or []:
        asset_type = str(requirement.get("asset_type", ""))
        if "searched_image" not in asset_type:
            continue
        section_id = str(requirement.get("section_id", ""))
        purpose = str(requirement.get("purpose", ""))
        queries = _planned_queries(title, section_titles.get(section_id, ""), purpose)
        for provider in (search_commons_candidates, search_openverse_candidates):
            provider_added = False
            for query in queries:
                try:
                    found = provider(
                        query,
                        purpose=purpose,
                        section_id=section_id,
                        limit=limit_per_requirement,
                    )
                except requests.RequestException:
                    found = []
                for candidate in found:
                    if not _candidate_is_usable(candidate, purpose, title=title):
                        continue
                    candidate = dict(candidate)
                    candidate["section_id"] = section_id
                    candidate["purpose"] = purpose
                    candidate["planned_query"] = query
                    candidate["asset_plan_required"] = bool(requirement.get("required"))
                    if candidate.get("image_url") not in {item.get("image_url") for item in candidates}:
                        candidates.append(candidate)
                        provider_added = True
                    if len([item for item in candidates if item.get("section_id") == section_id]) >= limit_per_requirement:
                        break
                if provider_added:
                    break
    return candidates


def _metadata_value(metadata: dict, key: str) -> str:
    value = metadata.get(key) or {}
    return value.get("value", "") if isinstance(value, dict) else str(value or "")


def _clean_metadata(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def _guess_suffix(url: str, content_type: str) -> str:
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return suffix
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    return ".jpg"


def _planned_query(title: str, section_title: str, purpose: str) -> str:
    combined = f"{title} {section_title}".lower()
    domain_terms = []
    if any(term in combined for term in ("空气质量", "air quality", "pm2.5")):
        domain_terms.append("urban air quality monitoring station")
    if any(term in combined for term in ("x光", "x-ray", "安检", "违禁品", "security inspection")):
        domain_terms.append("airport x-ray baggage security inspection")
    if any(term in combined for term in ("脑电", "脑机", "eeg", "brain-computer", "brain computer")):
        domain_terms.append("EEG brain computer interface")
    if any(term in combined for term in ("机械臂", "机器人手臂", "robotic arm", "robot arm")):
        domain_terms.append("robotic arm")
    if not domain_terms:
        domain_terms.append(title.strip() or section_title.strip())
    purpose_terms = {
        "system_or_device_context": "device photograph",
        "application_context": "application scene",
    }.get(purpose, "research photograph")
    bits = domain_terms + [purpose_terms]
    return " ".join(bit for bit in bits if bit)


def _planned_queries(title: str, section_title: str, purpose: str) -> list[str]:
    """Return focused Commons queries in order of specificity."""
    primary = _planned_query(title, section_title, purpose)
    combined = f"{title} {section_title}".lower()
    fallbacks = []
    has_robot_arm = any(term in combined for term in ("机械臂", "机器人手臂", "robotic arm", "robot arm"))
    has_bci = any(term in combined for term in ("脑电", "脑机", "eeg", "brain-computer", "brain computer"))
    has_air_quality = any(term in combined for term in ("空气质量", "air quality", "pm2.5"))
    has_security_xray = any(term in combined for term in ("x光", "x-ray", "安检", "违禁品", "security inspection"))
    if has_robot_arm and has_bci:
        fallbacks.extend(["brain controlled robotic arm", "brain computer interface robotic arm"])
    if has_robot_arm:
        fallbacks.extend(["robotic arm", "robot arm rehabilitation"])
    if has_bci:
        fallbacks.extend(["electroencephalography EEG cap", "brain computer interface"])
    if has_air_quality:
        fallbacks.extend(["air quality monitoring station", "urban air pollution monitoring sensor"])
    if has_security_xray:
        fallbacks.extend(["airport baggage x-ray scanner", "security inspection x-ray baggage", "x-ray luggage scanner"])
    return list(dict.fromkeys([primary, *fallbacks]))


def _candidate_is_usable(candidate: dict, purpose: str, *, title: str = "") -> bool:
    """Reject documents and semantically unrelated search accidents."""
    image_url = str(candidate.get("image_url", "")).lower().split("?", 1)[0]
    if Path(image_url).suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        return False
    text = " ".join(
        str(candidate.get(field, "")).lower()
        for field in ("title", "caption", "source_url")
    )
    if any(term in text for term in {"nasa", "space station", "canadarm", "sts-", "rov manipulator"}):
        return False
    lowered_title = str(title or "").lower()
    bci_topic = any(term in lowered_title for term in ("脑电", "脑机", "eeg", "bci", "机械臂", "robotic arm"))
    air_topic = any(term in lowered_title for term in ("空气质量", "air quality", "pm2.5"))
    security_topic = any(term in lowered_title for term in ("x光", "x-ray", "安检", "违禁品", "security inspection"))
    context_terms = {"rehabil", "prosthe", "eeg", "electroenceph", "brain-computer", "brain computer", "bci", "brain controlled"}
    if air_topic:
        return any(term in text for term in {"air quality", "pollution", "monitoring", "sensor", "station", "pm2"})
    if security_topic:
        return any(term in text for term in {"x-ray", "xray", "baggage", "security", "inspection", "scanner"})
    if not bci_topic:
        return bool(candidate.get("license") or candidate.get("source_url"))
    if purpose == "system_or_device_context":
        return (
            any(term in text for term in {"eeg", "electroenceph", "brain-computer", "brain computer", "bci"})
            or (any(term in text for term in {"robot", "arm"}) and any(term in text for term in context_terms))
        )
    return any(term in text for term in context_terms)
