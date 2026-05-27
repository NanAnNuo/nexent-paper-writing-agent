"""
内容后处理器 — 对 LLM 输出做健壮性规范化

不管 LLM 输出什么格式，都能修复为 renderer 可处理的格式。
"""

import re


def normalize_content(content: str, section_title: str = "") -> str:
    """主入口：对 LLM 输出的章节内容做全面规范化"""
    if not content:
        return content

    # 1. 移除 markdown 代码块
    content = _remove_code_blocks(content)

    # 2. 规范化标题（任意级别 # → 只保留 ## 和 ###）
    content = _normalize_headings(content)

    # 3. 移除加粗/斜体标记
    content = _remove_bold_italic(content)

    # 4. 移除 blockquote
    content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)

    # 5. 移除误混入正文的写作指导/审稿元叙述
    content = _remove_meta_writing_sentences(content, section_title=section_title)

    # 6. 如果段落过长且没有空行分隔，强制拆分
    content = _ensure_paragraph_breaks(content)

    # 7. 清理每行首尾空白
    lines = [l.rstrip() for l in content.split("\n")]
    content = "\n".join(lines)

    return content.strip()


def _remove_meta_writing_sentences(content: str, section_title: str = "") -> str:
    """Drop prose about how to write a section rather than the study itself."""
    is_abstract = str(section_title or "").strip().lower() in {"摘要", "abstract"}
    patterns = [
        r"摘要作为论文的缩影[^。！？.!?]*[。！？.!?]",
        r"摘要(?:需要|应当|应该|须)[^。！？.!?]*(?:反映|概括|避免|包含)[^。！？.!?]*[。！？.!?]",
    ] if is_abstract else []
    patterns.extend([
        r"(?:本章|本节)(?:将|旨在)(?:介绍|论述|阐述|展开|说明)[^。！？.!?]*[。！？.!?]",
    ])
    for pattern in patterns:
        content = re.sub(pattern, "", content)
    return content


def _remove_code_blocks(content: str) -> str:
    """移除 ``` 代码块"""
    content = re.sub(r'```[\s\S]*?```', '', content)
    content = re.sub(r'~~~[\s\S]*?~~~', '', content)
    return content


def _normalize_headings(content: str) -> str:
    """
    规范化标题：
    - # 标题 → ## 标题（一级降为二级，因为 H1 已被章节标题占用）
    - ## 标题 → 保持不变（H2）
    - ### 标题 → 保持不变（H3）
    - #### 标题 → ### 标题（H4 降为 H3）
    - ##### 标题 → ### 标题（H5 降为 H3）
    """
    lines = content.split("\n")
    result = []
    for line in lines:
        stripped = line.lstrip()
        # 检测标题行（#开头，且后面有空格或中文全角空格）
        match = re.match(r'^(#{1,5})(?: |　)(.+)$', stripped)
        if match:
            hashes = match.group(1)
            text = match.group(2).strip()
            level = len(hashes)
            if level <= 1:
                # # → ##
                result.append(f"## {text}")
            elif level == 2:
                result.append(f"## {text}")
            elif level == 3:
                result.append(f"### {text}")
            else:
                # #### 及以上 → ###
                result.append(f"### {text}")
        else:
            result.append(line)
    return "\n".join(result)


def _remove_bold_italic(content: str) -> str:
    """移除 markdown 加粗/斜体标记"""
    # **text** → text
    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
    # *text* → text（但小心不要把星号乘法给去掉了）
    content = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', content)
    # __text__ → text
    content = re.sub(r'__(.+?)__', r'\1', content)
    return content


def _ensure_paragraph_breaks(content: str) -> str:
    """如果内容缺少段落分隔，在句子边界插入空行"""
    # 先检查是否已经有段落分隔
    if "\n\n" in content:
        return content

    lines = content.split("\n")
    if len(lines) <= 1:
        # 单行超长文本：在句子边界拆分
        text = lines[0]
        if len(text) > 600:
            # 在句号、问号、感叹号后拆分
            parts = re.split(r'(?<=[。！？.!?])\s+', text)
            return "\n\n".join(parts)
        return content

    # 多行但没有空行：检查是否有隐式段落（连续非空行太多）
    new_lines = []
    para_line_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped:
            para_line_count += 1
            new_lines.append(line)
            # 如果连续非空行超过 5 行且不是标题，插入空行
            if para_line_count >= 5 and not stripped.startswith("#"):
                new_lines.append("")
                para_line_count = 0
        else:
            new_lines.append(line)
            para_line_count = 0

    return "\n".join(new_lines)
