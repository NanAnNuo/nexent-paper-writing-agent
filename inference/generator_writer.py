"""
Generator_Writer — 章节写作

专门用于调用 Nexent API 撰写论文章节。
包含 nature move 序列注入逻辑。
"""

from .nexent_client import NexentClient
from patterns.move_sequences import format_moves_prompt, get_diagnostics_for_section


def write_section(
    outline: dict,
    papers_text: str = "",
    data_summary: str = "",
    previous_context: str = "",
    client: NexentClient = None,
) -> dict:
    """撰写单个章节，自动注入 nature move 序列"""
    client = client or NexentClient()
    title = outline.get("title", "")

    moves_prompt = format_moves_prompt(title)

    return client.generator_writer(
        outline=outline,
        papers_text=papers_text,
        data_summary=data_summary,
        move_sequence=moves_prompt,
        previous_context=previous_context,
    )
