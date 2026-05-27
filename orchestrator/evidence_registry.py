"""Build minimal claim-to-evidence links for manuscript ASTs."""

from __future__ import annotations

import re
from typing import Iterable


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")
NUMERIC_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|ms|s\b|Hz|kHz|p\s*[<=>])", re.IGNORECASE)
REFERENCE_RE = re.compile(r"\[(?:ref)?(\d+)\]")


def build_evidence_registry(
    sections: Iterable[dict],
    references: Iterable[dict],
    *,
    source_material: str = "",
    result_evidence: str = "",
    approved_assets: Iterable[dict] | None = None,
    materials: Iterable[dict] | None = None,
) -> dict:
    refs = list(references or [])
    assets = list(approved_assets or [])
    materials = list(materials or [])
    source_ids = [
        material.get("material_id")
        for material in materials
        if material.get("parse_status") == "parsed"
        and material.get("material_role") in {"source_text", "reference_material"}
    ]
    result_ids = [
        material.get("material_id")
        for material in materials
        if material.get("parse_status") == "parsed"
        and material.get("material_role") == "result_dataset"
    ]
    claims = []
    for section in sections or []:
        title = section.get("title", "")
        content = section.get("content") or section.get("section_content") or ""
        for sentence in SENTENCE_SPLIT_RE.split(content):
            sentence = sentence.strip()
            if not sentence or not NUMERIC_RE.search(sentence):
                continue
            ref_ids = REFERENCE_RE.findall(sentence)
            claims.append({
                "section": title,
                "claim": sentence[:500],
                "reference_ids": ref_ids,
                "evidence_sources": _evidence_sources(
                    ref_ids, source_material, result_evidence, assets, source_ids, result_ids
                ),
            })
    return {
        "materials": {
            "source_material_present": bool(source_material.strip() or source_ids),
            "result_evidence_present": bool(result_evidence.strip() or result_ids),
            "source_material_ids": source_ids,
            "result_dataset_ids": result_ids,
        },
        "reference_count": len(refs),
        "approved_image_asset_ids": [asset.get("asset_id") for asset in assets if asset.get("approved")],
        "claims": claims,
    }


def _evidence_sources(
    ref_ids: list[str],
    source_material: str,
    result_evidence: str,
    assets: list[dict],
    source_ids: list[str],
    result_ids: list[str],
) -> list[str]:
    sources = []
    if ref_ids:
        sources.append("references")
    if source_material.strip() or source_ids:
        sources.append("user_material")
    if result_evidence.strip() or result_ids:
        sources.append("result_evidence")
    if any(asset.get("approved") for asset in assets):
        sources.append("approved_assets")
    return sources
