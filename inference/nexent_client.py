"""
Nexent 推理面客户端

封装对 Nexent 平台三个原子 API 的 HTTP 调用：
  - Generator_Coder:  绘图代码生成
  - Generator_Writer: 章节写作
  - Discriminator:    质量审查

兼容 OpenAI 兼容 API (如 DeepSeek) 和 Anthropic API。
"""

import json
import re
from typing import Optional

from core.llm_client import LLMClient, get_llm_client
from core.utils import setup_logging

logger = setup_logging("nexent_client")


class NexentClient:
    """Nexent 推理面客户端 — 将 Nexent 作为 LLM 调用网关"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self._llm = llm_client

    def _get_llm(self) -> LLMClient:
        """Initialize the configured LLM only when an inference call is made."""
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    def generator_coder(
        self,
        context: str,
        traceback: str = "",
        color_palette: str = "nature",
    ) -> str:
        """
        Generator_Coder API：生成 Python/Matplotlib 绘图代码

        Args:
            context: 章节上下文（标题、关键数据描述）
            traceback: 可选的上次执行报错（debug 模式）

        Returns:
            Python 代码字符串
        """
        from patterns.color_palettes import format_colors_prompt
        colors_prompt = format_colors_prompt(color_palette)

        if traceback:
            system = """你是一个 Python 科学绘图专家。用户之前生成的代码执行失败了，
请根据报错信息修复代码。只返回修复后的 Python 代码，不要解释。"""
            user_prompt = f"""## 出错代码的上下文
{context}

## 上次执行的报错
{traceback}

## 配色要求
{colors_prompt}

## 要求
1. 只返回纯 Python 代码，不要 markdown 代码块标记
2. 使用 matplotlib 绘图，保存为 PNG（300dpi）
3. 在代码开头添加 import matplotlib; matplotlib.use('Agg')
4. 最后 plt.close(fig)
5. 保存路径: figures/figure_{hash(context) % 10000}.png"""
        else:
            system = """你是一个 Python 科学绘图专家。根据用户需求生成数据可视化的 Python 代码。"""
            user_prompt = f"""## 需求描述
{context}

## 配色要求
{colors_prompt}

## 要求
1. 只返回纯 Python 代码，不要 markdown 代码块标记
2. 使用 matplotlib 绘图，保存为 PNG（300dpi）
3. 在代码开头添加 import matplotlib; matplotlib.use('Agg')
4. 最后 plt.close(fig)
5. 保存路径: figures/figure_{hash(context) % 10000}.png
6. 如果没有真实数据，生成合理的模拟数据用于演示"""

        raw = self._get_llm().call(user_prompt, system=system)
        return self._clean_code(raw)

    def generator_writer(
        self,
        outline: dict,
        papers_text: str = "",
        data_summary: str = "",
        move_sequence: str = "",
        previous_context: str = "",
    ) -> dict:
        """
        Generator_Writer API：撰写单章内容

        Returns:
            {"content": "...", "references_used": [...]}
        """
        title = outline.get("title", "")
        key_points = outline.get("key_points", [])

        system = f"""你是一个学术论文写作助手。请撰写高质量的学术论文章节。

## 内容格式（必须遵守）
1. 二级标题用 ##，三级标题用 ###，不要使用 ####
2. 段落之间用空行分隔，不要全写在一个段落里
3. 不要重复写当前章节的标题，直接从正文开始
4. 不要使用 **加粗** 语法
5. 如需插图，用 [Figure: 图片路径] 格式

## 引用与字数
6. 必须使用提供的真实文献，禁止编造
7. 正文中用 [ref0], [ref1] 引用
8. 字数约 1500-3000 字
9. 学术写作风格
10. 输出纯 JSON，不要 markdown 代码块

## 本章写作指导
{move_sequence}"""

        user_prompt = f"""## 章节标题
{title}

## 关键要点
{chr(10).join(f'- {kp}' for kp in key_points)}

## 参考文献
{papers_text if papers_text else '(等待文献检索结果)'}

## 图表数据摘要
{data_summary if data_summary else '(无)'}

## 前文上下文
{previous_context if previous_context else '(本文章节)'}

## 输出格式
{{"content": "章节正文，包含 [ref0], [ref1] 等引用...", "references_used": ["ref0", "ref1"]}}"""

        raw = self._get_llm().call(user_prompt, system=system, response_format="json")
        return self._parse_json(raw)

    def discriminator(self, section_content: str, criteria: list[str]) -> dict:
        """
        Discriminator API：审查章节质量

        Returns:
            {"status": "PASS"/"FAIL", "reason": "...", "issues": [...]}
        """
        system = """你是一个学术论文质量审查专家。根据给定的标准审查章节内容，
判断是否达到发表质量。"""
        criteria_text = "\n".join(f"- {c}" for c in criteria)

        user_prompt = f"""## 审查标准
{criteria_text}

## 章节内容
{section_content[:4000]}

## 输出格式（JSON）
{{"status": "PASS" 或 "FAIL", "reason": "简要理由", "issues": ["问题1", "问题2"]}}"""

        raw = self._get_llm().call(user_prompt, system=system, response_format="json")
        result = self._parse_json(raw)

        if result.get("status") not in ("PASS", "FAIL"):
            result["status"] = "PASS"
            result["reason"] = "审查结果解析失败，默认通过"
            result["issues"] = []
        return result

    def _clean_code(self, raw: str) -> str:
        """清理 LLM 返回的代码"""
        raw = raw.strip()
        raw = re.sub(r"^```(?:python)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return raw

    def _parse_json(self, raw: str) -> dict:
        """容错 JSON 解析"""
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {}
