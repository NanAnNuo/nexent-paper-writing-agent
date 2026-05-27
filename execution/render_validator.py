"""Validation for final Word outputs.

Only conditions that cannot produce a usable Word file are hard errors. Paper
quality, citation, and asset gaps are warnings for the output-first pipeline.
"""

from __future__ import annotations

import os
import re


FIGURE_MARKER_RE = re.compile(r"\[Figure:\s*(.+?)\]")
REF_MARKER_RE = re.compile(r"\[(ref\d+)\]")


def validate_renderable_ast(ast: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    sections = ast.get("sections") or []
    if not sections:
        errors.append("paper has no sections")
    if not ast.get("references"):
        warnings.append("paper has no resolved references")

    refs_by_key = {
        ref.get("citation_key")
        for ref in ast.get("references", [])
        if ref.get("citation_key")
    }
    for section in sections:
        title = section.get("title") or section.get("section_id") or "untitled"
        content = section.get("content") or section.get("section_content") or ""
        if not content.strip():
            errors.append(f"empty section: {title}")
        for ref_key in REF_MARKER_RE.findall(content):
            if ref_key not in refs_by_key:
                warnings.append(f"unresolved citation {ref_key} in section {title}")
        for path in FIGURE_MARKER_RE.findall(content):
            if not os.path.exists(path.strip()):
                warnings.append(f"missing figure {path.strip()} in section {title}")

    entity_registry = ast.get("entity_registry") or {}
    approved_images = [
        image for image in list(entity_registry.get("images", [])) + list(entity_registry.get("figures", []))
        if image.get("approved")
    ]
    for requirement in ast.get("asset_plan") or []:
        asset_type = str(requirement.get("asset_type", ""))
        if not requirement.get("required") or "searched_image" not in asset_type:
            continue
        if not any(
            image.get("section_id") == requirement.get("section_id")
            and image.get("purpose") == requirement.get("purpose")
            for image in approved_images
        ):
            warnings.append(
                "required approved image asset missing for "
                f"{requirement.get('section_id', 'unknown')}:{requirement.get('purpose', 'image')}"
            )
    for image in entity_registry.get("images", []):
        if not image.get("approved"):
            warnings.append(f"unapproved image asset {image.get('asset_id', 'unknown')}")
            continue
        local_path = image.get("local_path", "")
        if not local_path or not os.path.exists(local_path):
            warnings.append(f"missing approved image file {image.get('asset_id', 'unknown')}")
        for field in ("caption", "source_url", "license", "attribution"):
            if not image.get(field):
                warnings.append(f"approved image missing {field}: {image.get('asset_id', 'unknown')}")

    materials = ast.get("materials") or []
    failed_text = [
        material for material in materials
        if material.get("parse_status") == "failed"
        and material.get("file_type") in {".docx", ".txt", ".pdf"}
    ]
    parsed_text = [
        material for material in materials
        if material.get("parse_status") == "parsed"
        and material.get("material_role") in {"source_text", "reference_material"}
    ]
    if failed_text and not parsed_text:
        warnings.append("source materials were uploaded but could not be parsed")

    uploaded_images = [
        material for material in materials
        if material.get("parse_status") == "parsed"
        and material.get("material_role") == "image_asset"
        and material.get("metadata", {}).get("source_kind") != "docx_embedded_image"
    ]
    bound_material_ids = {
        image.get("material_id")
        for image in entity_registry.get("images", [])
        if image.get("approved") and image.get("material_id")
    }
    for material in uploaded_images:
        if material.get("material_id") not in bound_material_ids:
            warnings.append(f"unbound uploaded image asset {material.get('material_id', 'unknown')}")

    if any("[图片:" in (section.get("content") or "") for section in sections):
        warnings.append("section contains image placeholder text")
    return {"ok": not errors, "errors": errors, "warnings": warnings}
