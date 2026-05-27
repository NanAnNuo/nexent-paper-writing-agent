"""
句式模板 — 每个 move 的常用学术句式

来自 Academic Phrasebank 和 Nature 已发表文章。用作 Generator_Writer
Prompt 中的风格参考，不是模板填空。
"""


PHRASE_TEMPLATES = {
    "background": [
        "Recent years have seen increasing interest in ...",
        "The study of ... has become a central concern in ...",
        "... plays a critical role in ...",
        "The ability to ... is fundamental to ...",
    ],
    "problem": [
        "However, a key challenge remains: ...",
        "Despite these advances, ... remains poorly understood.",
        "A major bottleneck in ... is ...",
        "The complexity of ... poses significant difficulties for ...",
    ],
    "gap": [
        "However, little is known about ...",
        "To date, no study has systematically examined ...",
        "The mechanisms underlying ... remain elusive.",
        "It remains an open question whether ...",
    ],
    "approach": [
        "Here, we introduce ... to address this challenge.",
        "In this work, we propose a novel framework for ...",
        "We present ... that enables ...",
        "To overcome this limitation, we develop ...",
    ],
    "observation": [
        "The most notable finding was that ...",
        "We observed that ...",
        "Figure 1 shows ...",
        "Consistent with our hypothesis, ...",
    ],
    "comparison": [
        "These results are consistent with prior work showing ...",
        "In contrast to previous findings, ...",
        "Compared to ..., our approach achieves ...",
        "This discrepancy may reflect ...",
    ],
    "limitation": [
        "These results should be interpreted with caution because ...",
        "Several limitations of this study should be noted.",
        "A potential limitation is that ...",
        "The generalizability of these findings is constrained by ...",
    ],
    "implication": [
        "An implication of this is that ...",
        "These findings suggest that ...",
        "Taken together, our results indicate that ...",
        "This work provides a foundation for ...",
    ],
    "future": [
        "Further work is needed to determine whether ...",
        "Future studies should investigate ...",
        "An important direction for future research is ...",
        "Extending this approach to ... would be valuable.",
    ],
}


def get_phrases_for_move(move_name: str) -> list[str]:
    """获取特定 move 的句式模板"""
    for key, phrases in PHRASE_TEMPLATES.items():
        if key == move_name or key in move_name:
            return phrases
    return []


def format_phrases_prompt(move_names: list[str]) -> str:
    """将句式模板格式化为 Prompt 参考"""
    parts = ["### 句式参考"]
    for name in move_names:
        phrases = get_phrases_for_move(name)
        if phrases:
            parts.append(f"\n{name}:")
            for p in phrases[:3]:  # 每个 move 最多 3 句
                parts.append(f"  - \"{p}\"")
    return "\n".join(parts)
