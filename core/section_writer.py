import json
import re

from .llm_client import get_llm_client
from .literature_search import format_papers_for_prompt
from .content_normalizer import normalize_content
from .utils import setup_logging

logger = setup_logging("section_writer")

BASE_SYSTEM_PROMPT = """你是一个学术论文写作助手。你的任务是撰写高质量的学术论文章节。

## 内容格式要求（必须遵守）
1. 二级标题用「## 标题名」格式，三级标题用「### 标题名」格式，不要使用 #### 或其他级别
2. 段落之间用空行分隔（连续两个换行符 = 新段落开始），不要把所有内容写在一个段落里
3. 不要重复写当前章节的标题（渲染器会自动添加一级标题）。直接从正文内容开始
4. 不要使用 markdown 加粗语法（如 **text**），直接写纯文本
5. 如需要插入图表，使用 [Figure: 图片路径] 格式（不含多余空格）

## 引用要求
6. 必须使用提供的真实文献，禁止编造数据或引用
7. 在正文中使用 [ref0], [ref1] 等格式引用文献

## 字数与风格
8. 每章字数约 1500-3000 字（引言1500-2000，方法2000-4000，结果2000-4000，讨论1500-3000，视章节类型调整）
9. 学术写作风格，语言正式、严谨
10. 输出纯 JSON 格式，不要包含 markdown 代码块标记"""


def write_section(
    section_outline: dict,
    papers: list[dict],
    context: str = "",
    move_sequence: str = "",
) -> dict:
    """写作单个章节

    Args:
        move_sequence: nature 写作步骤指令（由 patterns/move_sequences.py 生成）
    """
    title = section_outline.get("title", "")
    key_points = section_outline.get("key_points", [])
    section_id = section_outline.get("id", "")

    # 注入 nature move 序列
    system_prompt = BASE_SYSTEM_PROMPT
    if move_sequence:
        system_prompt += f"\n\n## 本章写作结构指导\n{move_sequence}"

    papers_text = format_papers_for_prompt(papers)
    key_points_text = "\n".join(f"- {kp}" for kp in key_points)

    prompt = f"""请撰写以下论文章节：

章节标题：{title}
关键要点：
{key_points_text}

参考文献：
{papers_text}

前文上下文（供参考）：
{context}

要求：
1. 二级标题用 ##，三级标题用 ###（不要用 ####）
2. 段落之间用空行分隔
3. 不要重复章节标题
4. 引用格式 [ref0], [ref1]
5. 字数 1500-3000 字
6. 学术风格

请输出以下 JSON 格式（不要包含 markdown 代码块）：
{{"content": "章节正文...", "references_used": ["ref0", "ref2"]}}"""

    try:
        client = get_llm_client()
        raw = client.call(prompt, system=system_prompt, response_format="json")
        result = _parse_json_response(raw)

        content = result.get("content", "")
        refs_used = result.get("references_used", [])

        # 后处理：规范化 LLM 输出的内容（不受 prompt 约束影响）
        content = normalize_content(content, section_title=title)

        # 验证引用合法性
        valid_keys = {p.get("citation_key") for p in papers}
        refs_used = [k for k in refs_used if k in valid_keys]

        logger.info(f"章节 '{title}' 写作完成，{len(content)} 字")

        return {
            "section_id": section_id,
            "title": title,
            "content": content,
            "references_used": refs_used,
        }

    except Exception as e:
        logger.error(f"章节 '{title}' 写作失败: {e}")
        return {
            "section_id": section_id,
            "title": title,
            "content": f"【章节写作失败: {e}】",
            "references_used": [],
        }


def _parse_json_response(raw: str) -> dict:
    """从 LLM 响应中解析 JSON，兼容各种格式问题"""
    raw = raw.strip()
    # 移除 markdown 代码块标记
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # 尝试提取 {...} 部分
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"content": raw, "references_used": []}
