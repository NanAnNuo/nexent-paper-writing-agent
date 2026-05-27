"""
论文结构校验规则

基于 Nature 期刊的论文结构要求，提供大纲校验功能。
"""

REQUIRED_SECTIONS = [
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusion",
]

RECOMMENDED_SECTIONS = [
    "related work",
    "experiments",
    "analysis",
]

SECTION_ORDER = [
    "abstract",
    "introduction",
    "related work",
    "methods",
    "experiments",
    "results",
    "discussion",
    "conclusion",
]


def validate_outline(sections: list[dict]) -> dict:
    """校验大纲结构，返回校验结果"""
    titles = [s.get("title", "").lower().strip() for s in sections]
    found_required = []
    missing_required = []

    for req in REQUIRED_SECTIONS:
        matched = any(req in t for t in titles)
        if matched:
            found_required.append(req)
        else:
            missing_required.append(req)

    warnings = []

    # 检查是否存在 hourglass 结构
    has_abstract = any("abstract" in t for t in titles)
    has_intro = any("introduction" in t or "引言" in t for t in titles)
    has_conclusion = any("conclusion" in t or "结论" in t for t in titles)

    if not has_abstract:
        warnings.append("建议包含摘要章节 (Abstract)")
    if not has_intro:
        warnings.append("缺少引言章节 (Introduction)")
    if not has_conclusion:
        warnings.append("建议包含结论章节 (Conclusion)")

    # 章节数量检查
    if len(sections) < 4:
        warnings.append(f"章节数偏少 ({len(sections)})，建议至少 5-8 章")
    elif len(sections) > 15:
        warnings.append(f"章节数偏多 ({len(sections)})，建议不超过 12 章")

    return {
        "is_valid": len(missing_required) == 0,
        "total_sections": len(sections),
        "required_found": len(found_required),
        "required_total": len(REQUIRED_SECTIONS),
        "missing_required": missing_required,
        "warnings": warnings,
    }


def get_section_type(title: str) -> str:
    """根据标题推断章节类型"""
    t = title.lower().strip()
    mapping = {
        "abstract": "abstract",
        "introduction": "introduction",
        "related": "related_work",
        "method": "methods",
        "experiment": "results",
        "result": "results",
        "discussion": "discussion",
        "conclusion": "conclusion",
    }
    for key, value in mapping.items():
        if key in t:
            return value
    return "general"
