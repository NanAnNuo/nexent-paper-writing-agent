"""
学术写作策略 — Claim / Evidence / Boundary 框架

每个重要的科学声明都应包含三个部分：
  - Claim: 声明什么
  - Evidence: 什么支撑它
  - Boundary: 声明在何处停止有效
"""


WRITING_STRATEGY_SYSTEM_PROMPT = """## 学术写作核心原则

### 1. Claim - Evidence - Boundary 框架
每个重要声明必须包含：
- **Claim（主张）**: 明确你的论点
- **Evidence（证据）**: 提供支撑数据或引用
- **Boundary（边界）**: 说明适用的范围或条件

### 2. 沙漏结构
- Introduction: 宽 -> 窄（从广阔背景收缩到具体问题）
- Results/Methods: 窄（聚焦于方法和发现）
- Discussion: 窄 -> 宽（从具体发现扩展到广泛意义）

### 3. 写作顺序（非阅读顺序）
推荐规划顺序：
1. Results（最核心的发现）
2. Introduction + Conclusion
3. Title
4. Discussion
5. Methods
6. Abstract（最后写）

### 4. 引用功能分类
每个引用应明确其修辞功能：
- **support**: 支持本研究的论点
- **borrow**: 借用已有方法或框架
- **contrast**: 与现有工作进行对比
- **reuse**: 复用的已有资源

### 5. 禁止过度声明
避免使用以下表述（除非有充分证据）：
- "prove" / "conclusively"
- "unprecedented"
- "best" / "state-of-the-art"
- 无条件的 "first"
"""


def get_review_criteria() -> list[str]:
    """返回 Discriminator 审查标准"""
    return [
        "每个主要声明是否有数据或引用支撑？(Claim/Evidence)",
        "声明的适用范围是否明确？(Boundary)",
        "引用是否被正确归类其修辞功能？",
        "是否存在过度声明或夸大？",
        "章节是否符合从宽到窄或从窄到宽的结构？",
    ]
