"""
Nature 写作 — 章节 Move 序列

定义了学术论文各章节的标准修辞步骤 (moves)，用于指导 Generator_Writer
和 Discriminator 进行结构化写作与审查。
"""


# 每个章节的 move 序列
SECTION_MOVES = {
    "abstract": {
        "label": "Abstract",
        "moves": [
            "background: 领域背景与重要性",
            "problem: 当前瓶颈或挑战",
            "gap: 现有方法的不足之处",
            "question: 本研究要解决的问题",
            "approach: 方法/实验概述",
            "implication: 主要发现与意义",
        ],
        "diagnostics": [
            "如果以 'Here, we' 开头，可能缺少上下文背景",
            "如果以宽泛承诺结尾，需要控制 scope",
            "如果没有具体数字或对比，结论缺乏支撑",
        ],
    },
    "introduction": {
        "label": "Introduction",
        "moves": [
            "field_importance: 领域重要性的确立",
            "bottleneck: 当前实践中的瓶颈",
            "prior_review: 对现有工作的公正回顾",
            "capability_gap: 现有能力的不足与差距",
            "study_response: 本研究作为回应",
        ],
        "diagnostics": [
            "引入应像漏斗一样从宽到窄收缩",
            "对 prior work 的批评应公正且有据",
            "最后一段应清晰说明本文贡献",
        ],
    },
    "related_work": {
        "label": "相关工作",
        "moves": [
            "categorize: 对现有工作进行分类",
            "compare: 与本研究的方法对比",
            "highlight_diff: 强调本研究的差异与优势",
        ],
        "diagnostics": [
            "不要写成流水账式的文献罗列",
            "每段应有明确的分类标准",
            "与本文的方法对比应具体",
        ],
    },
    "methods": {
        "label": "方法",
        "moves": [
            "overview: 方法整体流程概述",
            "data: 数据来源与预处理",
            "implementation: 核心方法实现细节",
            "evaluation: 评估指标与设置",
        ],
        "diagnostics": [
            "应提供足够的实验复现细节",
            "公式应清晰定义每个符号含义",
            "参数设置应具体",
        ],
    },
    "results": {
        "label": "结果",
        "moves": [
            "system_overview: 系统/实验概览",
            "validation: 方法验证",
            "primary_result: 主要实验结果",
            "comparison: 与基准方法的公平对比",
            "analysis: 机制分析/消融实验",
            "scalability: 扩展性/泛化性验证",
        ],
        "diagnostics": [
            "每个结果小节应以 'To test [question], we [action]' 开头",
            "每个主要声明必须有定量数据支撑",
            "对比实验应控制变量",
        ],
    },
    "discussion": {
        "label": "讨论",
        "moves": [
            "central_advance: 核心进展的总结",
            "evidence_support: 证据对结论的支持",
            "workflow_change: 对实践流程的影响",
            "relation_to_prior: 与现有工作的关系",
            "limitations: 方法局限性",
            "future_work: 未来研究方向",
        ],
        "diagnostics": [
            "不要复述所有图表结果",
            "选择能改变解释的证据",
            "局限性应具体而非泛泛而谈",
        ],
    },
    "conclusion": {
        "label": "结论",
        "moves": [
            "main_contribution: 主要贡献的概括",
            "decisive_evidence: 决定性证据的回顾",
            "broader_implication: 更广泛的意义",
            "boundary: 适用范围的边界说明",
        ],
        "diagnostics": [
            "不要引入新的数据或结果",
            "结论应与引言中的问题呼应",
        ],
    },
}


def get_moves_for_section(title: str) -> list[str]:
    """根据章节标题返回对应的 move 序列"""
    title_lower = title.lower().strip()

    # 精确匹配
    for key, info in SECTION_MOVES.items():
        if key in title_lower or info["label"].lower() in title_lower:
            return info["moves"]

    # 模糊匹配
    for key, info in SECTION_MOVES.items():
        label_lower = info["label"].lower()
        if label_lower in title_lower:
            return info["moves"]

    # 默认返回通用 moves
    return [
        "overview: 章节概述",
        "details: 详细内容",
        "summary: 小结",
    ]


def get_diagnostics_for_section(title: str) -> list[str]:
    """返回对应章节的诊断规则"""
    title_lower = title.lower().strip()
    for key, info in SECTION_MOVES.items():
        if key in title_lower or info["label"].lower() in title_lower:
            return info["diagnostics"]
    return []


def format_moves_prompt(title: str) -> str:
    """将 move 序列格式化为可注入 Prompt 的文本"""
    moves = get_moves_for_section(title)
    lines = [f"  步骤 {i+1}: {move}" for i, move in enumerate(moves)]
    return "请遵循以下写作步骤：\n" + "\n".join(lines)
