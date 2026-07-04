"""Dashboard summaries and visualizations for processed tickets."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

RESULTS_DIR = Path(__file__).parent / "results"


def analyses_to_dataframe(analyses: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in analyses:
        row = {**item}
        if "category" in row and hasattr(row["category"], "value"):
            row["category"] = row["category"].value
        if "priority" in row and hasattr(row["priority"], "value"):
            row["priority"] = row["priority"].value
        if "sentiment" in row and hasattr(row["sentiment"], "value"):
            row["sentiment"] = row["sentiment"].value
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_tickets(analyses: list[dict[str, Any]]) -> dict[str, Any]:
    """Build dashboard summary stats from ticket analyses."""
    if not analyses:
        return {
            "total_tickets": 0,
            "by_category": {},
            "by_priority": {},
            "by_sentiment": {},
            "sla_risk_count": 0,
            "refund_request_count": 0,
            "avg_confidence": 0.0,
            "pii_detection_rate": 0.0,
        }

    df = analyses_to_dataframe(analyses)
    pii_count = sum(1 for a in analyses if a.get("pii_detected"))

    return {
        "total_tickets": len(analyses),
        "by_category": dict(Counter(df["category"].tolist())),
        "by_priority": dict(Counter(df["priority"].tolist())),
        "by_sentiment": dict(Counter(df["sentiment"].tolist())),
        "sla_risk_count": int(df["sla_risk"].sum()) if "sla_risk" in df else 0,
        "refund_request_count": int(df["refund_request"].sum())
        if "refund_request" in df
        else 0,
        "avg_confidence": round(float(df["confidence"].mean()), 3)
        if "confidence" in df
        else 0.0,
        "pii_detection_rate": round(pii_count / len(analyses), 3),
    }


def plot_category_distribution(
    analyses: list[dict[str, Any]],
    output_path: Path | None = None,
) -> Path:
    """Save bar chart of ticket categories."""
    output_path = output_path or RESULTS_DIR / "category_distribution.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary = summarize_tickets(analyses)
    categories = summary["by_category"]
    if not categories:
        categories = {"none": 0}

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(categories.keys(), categories.values(), color="#4C72B0")
    ax.set_title("Ticket Category Distribution")
    ax.set_xlabel("Category")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path


def plot_confusion_matrix(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
    output_path: Path | None = None,
    title: str = "Category Confusion Matrix",
) -> Path:
    """Save confusion matrix heatmap for evaluation."""
    output_path = output_path or RESULTS_DIR / "confusion_matrix.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    index_map = {label: i for i, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for truth, pred in zip(y_true, y_pred):
        if truth in index_map and pred in index_map:
            matrix[index_map[truth]][index_map[pred]] += 1

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)

    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, str(matrix[i][j]), ha="center", va="center", color="black")

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
