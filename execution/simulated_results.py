"""Deterministic result assets for explicitly accepted degraded manuscripts."""

from __future__ import annotations

import csv
from pathlib import Path

from .concept_diagram import _chinese_font


def build_simulated_result_assets(
    title: str,
    section_id: str,
    *,
    job_id: str = "paper",
    output_dir: str | Path = "data/assets/figures",
    language: str = "中文",
) -> tuple[list[dict], list[dict], str]:
    """Create visibly labelled placeholder result assets for later replacement."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    chinese = str(language or "").strip().lower() not in {"english", "en", "英文"}
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    slug = "".join(char for char in str(job_id) if char.isalnum() or char in "_-") or "paper"
    lowered_title = str(title or "").lower()
    air_quality = any(token in lowered_title for token in ("空气质量", "air quality", "pm2.5"))
    bci = any(token in lowered_title for token in ("脑电", "脑机", "eeg", "bci", "运动想象"))
    if air_quality:
        rows = [
            ["LSTM baseline", 18.6, 27.4, 0.81],
            ["Static ST-GCN", 16.9, 25.0, 0.84],
            ["Dynamic ST-GNN", 15.4, 22.8, 0.87],
        ]
        headers = ["模型", "MAE (μg/m³)", "RMSE (μg/m³)", "R²"]
        series_labels = ("MAE", "RMSE")
        line_label = "R²"
        first_caption = "模拟数据图：PM2.5预测误差比较（待以真实数据替换）"
        second_caption = "模拟数据图：PM2.5预测拟合优度比较（待以真实数据替换）"
        first_title = "模拟PM2.5预测误差对比图（待替换）"
        second_title = "模拟PM2.5预测拟合优度图（待替换）"
        first_ylabel = "浓度误差 (μg/m³)"
        second_ylabel = "R²"
        ylim = (0, max(row[2] for row in rows) * 1.25)
        summary_values = (
            "LSTM baseline: MAE 18.6 μg/m³、RMSE 27.4 μg/m³、R² 0.81；"
            "Static ST-GCN: 16.9、25.0、0.84；Dynamic ST-GNN: 15.4、22.8、0.87。"
        )
    elif bci:
        rows = [
            ["Baseline CSP+SVM", 81.8, 77.4, 246],
            ["Fusion classifier", 85.9, 81.2, 226],
            ["Fusion + feedback lock", 88.7, 84.1, 207],
        ]
        headers = ["方案", "离线准确率 (%)", "在线成功率 (%)", "平均时延 (ms)"]
        series_labels = ("离线准确率", "在线成功率")
        line_label = "平均时延 (ms)"
        first_caption = "模拟数据图：离线准确率与在线成功率比较（待以真实实验数据替换）"
        second_caption = "模拟数据图：平均在线响应时延（待以真实实验数据替换）"
        first_title = "模拟性能对比图（待替换）"
        second_title = "模拟在线时延图（待替换）"
        first_ylabel = "百分比 (%)"
        second_ylabel = "平均时延 (ms)"
        ylim = (0, 100)
        summary_values = (
            "Baseline CSP+SVM: 离线准确率81.8%、在线成功率77.4%、平均时延246 ms；"
            "Fusion classifier: 85.9%、81.2%、226 ms；"
            "Fusion + feedback lock: 88.7%、84.1%、207 ms。"
        )
    else:
        rows = [
            ["Baseline", 0.62, 0.58, 0.60],
            ["Enhanced model", 0.68, 0.64, 0.66],
            ["Proposed model", 0.73, 0.69, 0.71],
        ]
        headers = ["方案", "模拟指标 A", "模拟指标 B", "模拟综合得分"]
        series_labels = ("模拟指标 A", "模拟指标 B")
        line_label = "模拟综合得分"
        first_caption = "模拟数据图：指标比较（待以真实数据替换）"
        second_caption = "模拟数据图：综合得分比较（待以真实数据替换）"
        first_title = "模拟指标对比图（待替换）"
        second_title = "模拟综合得分图（待替换）"
        first_ylabel = "模拟指标值"
        second_ylabel = "模拟综合得分"
        ylim = (0, 1)
        summary_values = "Proposed model 为模拟占位最优方案；全部指标须以真实研究数据替换。"
    csv_path = folder / f"{slug}_SIMULATED_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["SIMULATED DATA - replace with real observations before formal use"])
        writer.writerow(headers)
        writer.writerows(rows)

    cjk_font = _chinese_font() if chinese else None
    labels = [row[0] for row in rows]
    first_metric = np.array([row[1] for row in rows])
    second_metric = np.array([row[2] for row in rows])
    line_metric = np.array([row[3] for row in rows])
    watermark = "模拟数据 - 待真实数据替换" if chinese else "SIMULATED DATA - REPLACE WITH REAL DATA"

    accuracy_path = folder / f"{slug}_SIMULATED_accuracy.png"
    fig, ax = plt.subplots(figsize=(9.5, 5.4), dpi=180)
    x = np.arange(len(labels))
    width = 0.34
    ax.bar(x - width / 2, first_metric, width, color="#1F5B78", label=series_labels[0])
    ax.bar(x + width / 2, second_metric, width, color="#C36A34", label=series_labels[1])
    ax.set_xticks(x, labels)
    ax.set_ylim(*ylim)
    ax.set_ylabel(first_ylabel, fontproperties=cjk_font)
    ax.set_title(first_title, fontproperties=cjk_font)
    ax.legend(prop=cjk_font)
    ax.grid(axis="y", alpha=0.24)
    ax.text(
        0.5,
        0.5,
        watermark,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=18,
        color="#A33A2B",
        alpha=0.18,
        rotation=18,
        fontproperties=cjk_font,
    )
    fig.tight_layout()
    fig.savefig(accuracy_path, facecolor="white")
    plt.close(fig)

    latency_path = folder / f"{slug}_SIMULATED_latency.png"
    fig, ax = plt.subplots(figsize=(9.5, 5.4), dpi=180)
    ax.plot(labels, line_metric, marker="o", linewidth=2.4, color="#237B74", label=line_label)
    ax.set_ylabel(second_ylabel, fontproperties=cjk_font)
    ax.set_title(second_title, fontproperties=cjk_font)
    ax.grid(axis="y", alpha=0.24)
    ax.text(
        0.5,
        0.5,
        watermark,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=18,
        color="#A33A2B",
        alpha=0.18,
        rotation=18,
        fontproperties=cjk_font,
    )
    fig.tight_layout()
    fig.savefig(latency_path, facecolor="white")
    plt.close(fig)

    attribution = "系统生成的模拟数据，不代表真实实验观测，正式使用前必须替换"
    figures = [
        {
            "asset_id": f"figure-{slug}-sim-accuracy",
            "approved": True,
            "local_path": str(accuracy_path.resolve()),
            "section_id": section_id,
            "purpose": "result_evidence",
            "source": "generated_simulated_result_data",
            "source_url": str(csv_path.resolve()),
            "license": "generated_simulated_placeholder",
            "attribution": attribution,
            "caption": first_caption,
            "english_caption": "Simulated result chart: performance comparison (replace with real experimental data)",
            "job_id": job_id,
            "simulated": True,
        },
        {
            "asset_id": f"figure-{slug}-sim-latency",
            "approved": True,
            "local_path": str(latency_path.resolve()),
            "section_id": section_id,
            "purpose": "result_evidence",
            "source": "generated_simulated_result_data",
            "source_url": str(csv_path.resolve()),
            "license": "generated_simulated_placeholder",
            "attribution": attribution,
            "caption": second_caption,
            "english_caption": "Simulated result chart: secondary metric comparison (replace with real experimental data)",
            "job_id": job_id,
            "simulated": True,
        },
    ]
    tables = [
        {
            "asset_id": f"table-{slug}-sim-results",
            "section_id": section_id,
            "caption": "模拟数据表：性能指标占位汇总（待以真实实验数据替换）",
            "english_caption": "Simulated metric summary (replace with real experimental data)",
            "job_id": job_id,
            "headers": headers,
            "rows": rows,
            "source": attribution,
            "simulated": True,
        }
    ]
    summary = (
        "【模拟结果数据，非真实实验观测，必须在正式使用前替换】"
        f"{summary_values}"
    )
    return figures, tables, summary
