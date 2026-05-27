import json
import logging
import os
from pathlib import Path
from typing import Optional

from docx import Document


def read_document(file_path: str) -> str:
    """读取文档内容，支持 .txt 和 .docx 格式"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    elif suffix == ".docx":
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}（仅支持 .txt 和 .docx）")


def save_json(data: dict, file_path: str) -> None:
    """保存 JSON 到文件，自动创建父目录"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(file_path: str) -> Optional[dict]:
    """从文件加载 JSON"""
    path = Path(file_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def setup_logging(name: str = "paper_agent") -> logging.Logger:
    """配置日志"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    return logger


def format_papers_for_prompt(papers: list[dict]) -> str:
    """将论文列表格式化为 LLM 提示中可用的字符串"""
    lines = []
    for i, p in enumerate(papers):
        authors = ", ".join(p.get("authors", [])[:3])
        if len(p.get("authors", [])) > 3:
            authors += " et al."
        year = p.get("year", "n.d.")
        title = p.get("title", "Untitled")
        lines.append(f"[{i + 1}] {authors} ({year}). {title}.")
    return "\n".join(lines)


def get_previous_context(
    sections: list[dict], max_count: int = 3
) -> str:
    """获取前 N 章节的摘要，作为写作上下文"""
    recent = sections[-max_count:] if max_count else sections
    parts = []
    for s in recent:
        title = s.get("title", "")
        content = s.get("content", "")
        # 只取前 300 字作为摘要
        summary = content[:300] + "..." if len(content) > 300 else content
        parts.append(f"=== {title} ===\n{summary}")
    return "\n\n".join(parts)
