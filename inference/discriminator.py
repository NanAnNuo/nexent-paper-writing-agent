"""
Discriminator — 质量审查

对 Generator_Writer 输出的章节进行质量审查，返回 PASS/FAIL。
审查标准基于 nature writing strategy 和章节的 move 序列。
"""

from .nexent_client import NexentClient
from patterns.move_sequences import get_diagnostics_for_section
from patterns.writing_strategy import get_review_criteria


def review_section(
    section_content: str,
    section_title: str = "",
    client: NexentClient = None,
) -> dict:
    """审查单个章节"""
    client = client or NexentClient()

    # 构建审查标准
    criteria = get_review_criteria()
    diagnostics = get_diagnostics_for_section(section_title)
    criteria.extend(diagnostics)

    return client.discriminator(section_content, criteria)
