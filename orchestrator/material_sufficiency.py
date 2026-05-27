"""Material sufficiency checks for evidence-bound paper writing."""

from __future__ import annotations

import re
from typing import Iterable


EXPERIMENT_HINTS = {
    "experiment", "experimental", "evaluation", "result", "benchmark",
    "dataset", "accuracy", "ablation", "subject", "trial", "prediction",
    "forecast", "forecasting", "predictive",
    "实验", "结果", "数据", "准确率", "受试", "评估", "对比", "预测", "预报",
}
METHOD_HINTS = {"method", "pipeline", "design", "protocol", "方法", "系统", "流程", "采集"}
RESULT_HINTS = {"result", "accuracy", "metric", "table", "figure", "结果", "准确率", "指标", "表", "图"}
TEXT_FILE_TYPES = {".docx", ".txt", ".pdf"}


def assess_material_sufficiency(
    *,
    topic: str = "",
    material_text: str = "",
    result_evidence: str = "",
    references: Iterable[dict] | None = None,
    approved_assets: Iterable[dict] | None = None,
    materials: Iterable[dict] | None = None,
    allow_degraded_writing: bool = False,
    degraded_reason: str = "",
) -> dict:
    """Return the writing scope supported by the available evidence."""
    references = list(references or [])
    approved_assets = [asset for asset in (approved_assets or []) if asset.get("approved")]
    materials = list(materials or [])

    readable_materials = [
        material for material in materials
        if material.get("parse_status") == "parsed"
        and material.get("material_role") in {"source_text", "reference_material"}
        and material.get("extracted_text")
    ]
    result_materials = [
        material for material in materials
        if material.get("parse_status") == "parsed"
        and material.get("material_role") == "result_dataset"
        and material.get("data_summary")
    ]
    uploaded_images = [
        material for material in materials
        if material.get("parse_status") == "parsed"
        and material.get("material_role") == "image_asset"
        and material.get("metadata", {}).get("source_kind") != "docx_embedded_image"
    ]
    unreadable_text_materials = [
        material for material in materials
        if material.get("parse_status") == "failed"
        and material.get("file_type") in TEXT_FILE_TYPES
    ]

    material_text = material_text or "\n".join(
        material.get("extracted_text", "") for material in readable_materials
    )
    combined = " ".join([topic, material_text, result_evidence]).lower()
    experimental = any(hint in combined for hint in EXPERIMENT_HINTS)

    missing: list[str] = []
    if unreadable_text_materials and not readable_materials:
        missing.append("unreadable_source_material")
    if not (topic.strip() or material_text.strip() or readable_materials):
        missing.append("research_problem")
    if experimental and not _contains_hint(material_text, METHOD_HINTS):
        missing.append("method_materials")
    if experimental and not (result_evidence.strip() or result_materials):
        missing.append("missing_result_dataset")
    if experimental and not (
        result_evidence.strip() or result_materials or _contains_hint(material_text, RESULT_HINTS)
    ):
        missing.append("result_evidence")
    if not references:
        missing.append("references")
    if experimental and not approved_assets and not _contains_hint(
        material_text, {"figure", "image", "photo", "图", "图片"}
    ):
        missing.append("figure_or_image_plan")
    if uploaded_images and not any(asset.get("material_id") for asset in approved_assets):
        missing.append("unbound_uploaded_image_asset")

    blocking_missing = {
        item for item in missing
        if item == "research_problem"
        or (item == "unreadable_source_material" and not topic.strip())
    }
    degraded_allowed = bool(allow_degraded_writing and missing and not blocking_missing)
    if not missing:
        status = "sufficient"
    elif degraded_allowed:
        status = "DEGRADED_WRITING_ALLOWED"
    else:
        status = "WAITING_REQUIRED_USER_MATERIALS"
    return {
        "status": status,
        "missing_materials": missing,
        "blocking_missing_materials": sorted(blocking_missing),
        "supported_scope": (
            "full_manuscript"
            if not missing
            else "degraded_manuscript_or_literature_supported_draft"
            if degraded_allowed
            else "outline_or_scaffold_only"
        ),
        "next_action": (
            "write_sections"
            if not missing
            else "write_sections_with_quality_risk_disclosure"
            if degraded_allowed
            else "request_real_materials_before_writing"
        ),
        "quality_risk_acknowledged": degraded_allowed,
        "degraded_reason": degraded_reason.strip() if degraded_allowed else "",
        "degraded_writing_available": bool(missing and not blocking_missing),
        "degraded_writing_requirements": (
            {
                "allow_degraded_writing": True,
                "user_acknowledgement": (
                    "User confirmed the missing materials cannot be provided and accepts "
                    "a lower-confidence manuscript based on available materials and literature."
                ),
            }
            if missing and not blocking_missing
            else {}
        ),
        "experimental": experimental,
        "material_counts": {
            "readable_text": len(readable_materials),
            "result_datasets": len(result_materials),
            "uploaded_images": len(uploaded_images),
        },
    }


def _topic_supports_engineering_assets(topic: str) -> bool:
    """Return whether generated workflow/result visuals are meaningful for the topic."""
    normalized = str(topic or "").lower()
    indicators = (
        "算法", "模型", "系统", "检测", "识别", "预测", "分类", "控制", "优化",
        "深度学习", "机器学习", "神经网络", "图神经", "脑电", "脑机", "机械臂",
        "机器人", "空气质量", "x光", "x-ray", "computer vision", "machine learning",
        "deep learning", "neural network", "eeg", "bci", "robotic", "forecast",
        "detection", "classification",
    )
    return any(indicator in normalized for indicator in indicators)


def build_asset_plan(sections: Iterable[dict], *, topic: str = "") -> list[dict]:
    """Generate topic-safe visual requirements for an outline."""
    plan = []
    engineering_assets = _topic_supports_engineering_assets(topic) if str(topic or "").strip() else True
    for section in sections or []:
        title = str(section.get("title", ""))
        section_id = section.get("id") or section.get("section_id") or title
        title_lower = title.lower()
        if engineering_assets and any(token in title_lower for token in ("method", "方法", "system", "系统")):
            plan.append({
                "section_id": section_id,
                "asset_type": "searched_image_or_diagram",
                "purpose": "system_or_device_context",
                "required": True,
            })
        if engineering_assets and any(token in title_lower for token in ("result", "experiment", "结果", "实验")):
            plan.extend([
                {
                    "section_id": section_id,
                    "asset_type": "data_figure",
                    "purpose": "result_evidence",
                    "required": True,
                },
                {
                    "section_id": section_id,
                    "asset_type": "data_table",
                    "purpose": "comparison_or_metric_summary",
                    "required": True,
                },
            ])
        if engineering_assets and any(token in title_lower for token in ("introduction", "引言")):
            plan.append({
                "section_id": section_id,
                "asset_type": "searched_image",
                "purpose": "application_context",
                "required": False,
            })
    return plan


def _contains_hint(text: str, hints: set[str]) -> bool:
    lowered = text.lower()
    return any(re.search(re.escape(hint), lowered) for hint in hints)
