"""Evaluation metrics on labeled support tickets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

from classify import classify_ticket
from dashboard import plot_confusion_matrix
from extract import extract_ticket_facts
from llm_client import SESSION_METRICS
from schemas import Category

DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
CATEGORY_LABELS = [c.value for c in Category]


def load_labeled_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "ticket_id",
        "customer_message",
        "true_category",
        "true_priority",
        "true_product",
        "true_refund_request",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")
    return df


def evaluate_dataset(
    df: pd.DataFrame,
    *,
    max_rows: int | None = None,
    save_outputs: bool = True,
) -> dict:
    """Run classification and extraction evaluation; return metric summary."""
    subset = df.head(max_rows) if max_rows else df
    pred_categories: list[str] = []
    true_categories: list[str] = []
    pred_priorities: list[str] = []
    true_priorities: list[str] = []
    product_matches = 0
    refund_matches = 0
    sample_outputs: list[dict] = []

    for _, row in subset.iterrows():
        ticket_id = str(row["ticket_id"])
        message = str(row["customer_message"])

        classification, _ = classify_ticket(message, ticket_id=ticket_id)
        extraction, _ = extract_ticket_facts(message, ticket_id=ticket_id)

        pred_cat = classification.category.value
        pred_pri = classification.priority.value
        true_cat = str(row["true_category"]).strip()
        true_pri = str(row["true_priority"]).strip()

        pred_categories.append(pred_cat)
        true_categories.append(true_cat)
        pred_priorities.append(pred_pri)
        true_priorities.append(true_pri)

        true_product = row["true_product"]
        if pd.isna(true_product) or str(true_product).strip() == "":
            product_ok = extraction.product is None or str(extraction.product).strip() == ""
        else:
            product_ok = (
                extraction.product is not None
                and str(true_product).lower() in str(extraction.product).lower()
            ) or str(extraction.product or "").lower() in str(true_product).lower()
        if product_ok:
            product_matches += 1

        true_refund = bool(row["true_refund_request"])
        if extraction.refund_request == true_refund:
            refund_matches += 1

        sample_outputs.append(
            {
                "ticket_id": ticket_id,
                "true_category": true_cat,
                "pred_category": pred_cat,
                "true_priority": true_pri,
                "pred_priority": pred_pri,
                "confidence": classification.confidence,
                "refund_request": extraction.refund_request,
                "pii_detected": extraction.pii_detected,
            }
        )

    n = len(subset)
    category_macro_f1 = f1_score(
        true_categories, pred_categories, labels=CATEGORY_LABELS, average="macro", zero_division=0
    )
    priority_accuracy = accuracy_score(true_priorities, pred_priorities)
    key_field_accuracy = (product_matches + refund_matches) / (2 * n) if n else 0.0

    report = classification_report(
        true_categories,
        pred_categories,
        labels=CATEGORY_LABELS,
        output_dict=True,
        zero_division=0,
    )

    summary = {
        "tickets_evaluated": n,
        "category_macro_f1": round(category_macro_f1, 4),
        "priority_accuracy": round(priority_accuracy, 4),
        "key_field_accuracy": round(key_field_accuracy, 4),
        "targets_met": {
            "category_macro_f1_gte_0_75": category_macro_f1 >= 0.75,
            "priority_accuracy_gte_0_75": priority_accuracy >= 0.75,
            "key_field_accuracy_gte_0_80": key_field_accuracy >= 0.80,
        },
        "classification_report": report,
    }

    if save_outputs:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_DIR / "eval_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        with open(RESULTS_DIR / "sample_outputs.jsonl", "w", encoding="utf-8") as f:
            for item in sample_outputs:
                f.write(json.dumps(item) + "\n")

        plot_confusion_matrix(true_categories, pred_categories, CATEGORY_LABELS)

        with open(RESULTS_DIR / "latency_cost_summary.json", "w", encoding="utf-8") as f:
            json.dump(SESSION_METRICS.summary(), f, indent=2)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate SupportOps Copilot on labeled tickets.")
    parser.add_argument(
        "--data",
        type=Path,
        default=DATA_DIR / "tickets_test_labeled.csv",
        help="Path to labeled CSV",
    )
    parser.add_argument("--max-rows", type=int, default=None, help="Limit rows for quick runs")
    args = parser.parse_args()

    df = load_labeled_csv(args.data)
    summary = evaluate_dataset(df, max_rows=args.max_rows)

    print("\n=== SupportOps Copilot Evaluation ===")
    print(f"Tickets evaluated: {summary['tickets_evaluated']}")
    print(f"Category macro-F1:  {summary['category_macro_f1']:.4f}")
    print(f"Priority accuracy:  {summary['priority_accuracy']:.4f}")
    print(f"Key-field accuracy: {summary['key_field_accuracy']:.4f}")
    print("\nTargets:")
    for name, met in summary["targets_met"].items():
        status = "PASS" if met else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\nResults saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
