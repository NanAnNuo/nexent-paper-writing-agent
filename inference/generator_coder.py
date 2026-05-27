"""
Generator_Coder — 绘图代码生成

专门用于调用 Nexent API 生成 Python/Matplotlib 绘图代码。
代理到 nexent_client.generator_coder()。
"""

from .nexent_client import NexentClient


def generate_code(
    context: str,
    traceback: str = "",
    palette: str = "nature",
    client: NexentClient = None,
) -> str:
    """生成绘图代码"""
    client = client or NexentClient()
    return client.generator_coder(context, traceback, palette)


def format_context(section_title: str, data_description: str = "") -> str:
    """将章节信息格式化为代码生成的上下文"""
    parts = [f"章节: {section_title}"]
    if data_description:
        parts.append(f"数据描述: {data_description}")
    return "\n".join(parts)
