"""Deterministic non-data figures for manuscript method sections."""

from __future__ import annotations

from pathlib import Path


def _chinese_font():
    """Use a local CJK font so embedded Chinese diagrams render legibly."""
    from matplotlib.font_manager import FontProperties

    for path in (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ):
        if path.exists():
            return FontProperties(fname=str(path))
    return None


def render_system_workflow_diagram(
    output_path: str | Path,
    language: str = "中文",
    topic: str = "",
) -> str:
    """Render a topic-matched conceptual workflow without asserting result data."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    chinese = str(language or "").strip().lower() not in {"english", "en", "英文"}
    lowered_topic = str(topic or "").lower()
    if any(token in lowered_topic for token in ("空气质量", "air quality", "pm2.5")):
        labels = (
            ["站点监测数据", "数据预处理", "动态图构建", "时空图网络", "空气质量预测"]
            if chinese else
            ["Station data", "Preprocessing", "Dynamic graph", "ST-GNN", "Air-quality forecast"]
        )
        feedback_label = "误差评估与更新" if chinese else "Evaluation and update"
    elif any(token in lowered_topic for token in ("脑电", "脑机", "eeg", "bci", "运动想象", "机械臂")):
        labels = (
            ["EEG采集", "信号预处理", "特征与分类", "机械臂控制", "触觉反馈"]
            if chinese else
            ["EEG acquisition", "Preprocessing", "Feature/classifier", "Arm control", "Tactile feedback"]
        )
        feedback_label = "闭环反馈" if chinese else "Closed-loop feedback"
    else:
        labels = (
            ["输入数据", "预处理", "特征建模", "模型推理", "输出评估"]
            if chinese else
            ["Input data", "Preprocessing", "Feature model", "Inference", "Evaluation"]
        )
        feedback_label = "评估与迭代" if chinese else "Evaluation and iteration"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cjk_font = _chinese_font() if chinese else None

    fig, ax = plt.subplots(figsize=(12, 3.1), dpi=180)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.axis("off")

    colors = ["#1F5B78", "#237B74", "#2A6F97", "#C36A34", "#65743A"]
    x_positions = [0.35, 2.75, 5.15, 7.55, 9.95]
    for index, (label, x_pos, color) in enumerate(zip(labels, x_positions, colors)):
        box = FancyBboxPatch(
            (x_pos, 1.05),
            1.72,
            0.82,
            boxstyle="round,pad=0.08,rounding_size=0.08",
            facecolor=color,
            edgecolor="none",
        )
        ax.add_patch(box)
        ax.text(
            x_pos + 0.86,
            1.46,
            label,
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontproperties=cjk_font,
        )
        if index < len(x_positions) - 1:
            ax.add_patch(FancyArrowPatch(
                (x_pos + 1.74, 1.46),
                (x_positions[index + 1] - 0.06, 1.46),
                arrowstyle="-|>",
                mutation_scale=14,
                linewidth=1.4,
                color="#3D4650",
            ))
    ax.add_patch(FancyArrowPatch(
        (10.8, 1.0),
        (8.4, 0.55),
        connectionstyle="arc3,rad=-0.22",
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.2,
        linestyle="--",
        color="#65743A",
    ))
    ax.text(
        7.35,
        0.3,
        feedback_label,
        ha="center",
        va="center",
        fontsize=9,
        color="#44515A",
        fontproperties=cjk_font,
    )
    fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(output_path.resolve())


def render_research_framework_diagram(
    output_path: str | Path,
    language: str = "中文",
    topic: str = "",
) -> str:
    """Render a topic-matched research framework map without claiming evidence."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    chinese = str(language or "").strip().lower() not in {"english", "en", "英文"}
    lowered = str(topic or "").lower()
    if any(token in lowered for token in ("空气质量", "air quality", "pm2.5")):
        center = "城市空气质量预测" if chinese else "Urban air-quality forecast"
        branches = (
            ["监测站点", "气象协变量", "时空依赖", "预测评估"]
            if chinese else ["Stations", "Weather covariates", "Spatiotemporal links", "Evaluation"]
        )
    elif any(token in lowered for token in ("脑电", "脑机", "eeg", "bci", "机械臂")):
        center = "脑机控制研究框架" if chinese else "BCI control framework"
        branches = (
            ["运动想象任务", "EEG特征", "控制指令", "反馈评估"]
            if chinese else ["Motor imagery", "EEG features", "Control command", "Feedback"]
        )
    elif any(token in lowered for token in ("x光", "x-ray", "安检", "违禁品")):
        center = "X光违禁品检测" if chinese else "X-ray contraband detection"
        branches = (
            ["安检图像", "特征提取", "目标检测", "部署应用"]
            if chinese else ["Security images", "Features", "Detection", "Deployment"]
        )
    else:
        center = "研究问题" if chinese else "Research question"
        branches = (
            ["数据来源", "方法设计", "结果验证", "应用讨论"]
            if chinese else ["Data source", "Method", "Validation", "Implication"]
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font = _chinese_font() if chinese else None
    fig, ax = plt.subplots(figsize=(9, 5.3), dpi=180)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    center_box = FancyBboxPatch(
        (3.6, 2.35), 2.8, 1.1,
        boxstyle="round,pad=0.1,rounding_size=0.14",
        facecolor="#1F5B78", edgecolor="none",
    )
    ax.add_patch(center_box)
    ax.text(5, 2.9, center, ha="center", va="center", color="white", fontsize=12, fontproperties=font)
    positions = [(0.4, 4.55), (6.95, 4.55), (0.4, 0.75), (6.95, 0.75)]
    colors = ["#D9EAF1", "#DAEFEA", "#F2E5DC", "#E7ECD9"]
    for label, (x, y), color in zip(branches, positions, colors):
        box = FancyBboxPatch(
            (x, y), 2.65, 0.75,
            boxstyle="round,pad=0.08,rounding_size=0.1",
            facecolor=color, edgecolor="#52616B", linewidth=0.8,
        )
        ax.add_patch(box)
        ax.text(x + 1.325, y + 0.375, label, ha="center", va="center", fontsize=10, color="#24343D", fontproperties=font)
        start = (5, 3.45 if y > 3 else 2.35)
        target = (x + 1.325, y if y > 3 else y + 0.75)
        ax.add_patch(FancyArrowPatch(start, target, arrowstyle="-|>", mutation_scale=13, linewidth=1.15, color="#5D6972"))
    fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(output_path.resolve())
