"""
上下文构建器

为章节写作组装上下文：前文摘要 + 图表数据。
"""


def build_section_context(
    section_title: str,
    previous_sections: list[dict],
    prev_context: str = "",
    figure_summary: str = "",
    max_previous: int = 3,
) -> str:
    """构建单章写作的完整上下文"""
    parts = []

    # 前文上下文
    if prev_context:
        parts.append(f"【前文上下文】\n{prev_context}")
    elif previous_sections:
        ctx = _get_previous_context(previous_sections, max_count=max_previous)
        parts.append(f"【前文上下文】\n{ctx}")

    # 图表数据
    if figure_summary:
        parts.append(f"【图表数据摘要】\n{figure_summary}")

    return "\n\n".join(parts) if parts else ""


def _get_previous_context(sections: list[dict], max_count: int = 3) -> str:
    """获取前 N 章节的摘要（前 300 字）"""
    recent = sections[-max_count:] if max_count else sections
    parts = []
    for s in recent:
        title = s.get("title", "")
        content = s.get("content", "")
        summary = content[:300] + "..." if len(content) > 300 else content
        parts.append(f"=== {title} ===\n{summary}")
    return "\n\n".join(parts)
