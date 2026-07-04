"""Command-line interface for SupportOps Copilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from dashboard import summarize_tickets
from evaluate import evaluate_dataset, load_labeled_csv
from llm_client import SESSION_METRICS
from pipeline import process_ticket

RESULTS_DIR = Path(__file__).parent / "results"
DATA_DIR = Path(__file__).parent / "data"


def cmd_analyze(args: argparse.Namespace) -> None:
    message = args.message
    if args.file:
        message = Path(args.file).read_text(encoding="utf-8")
    if not message:
        raise SystemExit("Provide --message or --file")

    analysis, log_payload = process_ticket(message, ticket_id=args.ticket_id)
    print(json.dumps(analysis.model_dump(mode="json"), indent=2))
    if args.log:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_DIR / "sample_outputs.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_payload) + "\n")


def cmd_batch(args: argparse.Namespace) -> None:
    df = pd.read_csv(args.csv)
    if "customer_message" not in df.columns:
        raise SystemExit("CSV must contain customer_message column")

    analyses = []
    for i, row in df.iterrows():
        tid = str(row.get("ticket_id", f"batch-{i}"))
        analysis, _ = process_ticket(str(row["customer_message"]), ticket_id=tid)
        analyses.append(analysis.model_dump(mode="json"))
        print(f"Processed {tid}: {analysis.category.value} / {analysis.priority.value}")

    summary = summarize_tickets(analyses)
    print("\nDashboard summary:")
    print(json.dumps(summary, indent=2))


def cmd_evaluate(args: argparse.Namespace) -> None:
    path = args.data or DATA_DIR / "tickets_test_labeled.csv"
    df = load_labeled_csv(path)
    summary = evaluate_dataset(df, max_rows=args.max_rows)
    print(json.dumps(summary, indent=2))


def cmd_metrics(args: argparse.Namespace) -> None:
    print(json.dumps(SESSION_METRICS.summary(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SupportOps Copilot — classify, extract, draft, evaluate."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Analyze a single ticket")
    p_analyze.add_argument("--message", "-m", default="", help="Customer message text")
    p_analyze.add_argument("--file", "-f", type=Path, help="Read message from file")
    p_analyze.add_argument("--ticket-id", default="cli-001")
    p_analyze.add_argument("--log", action="store_true", help="Append to sample_outputs.jsonl")
    p_analyze.set_defaults(func=cmd_analyze)

    p_batch = sub.add_parser("batch", help="Process a CSV of tickets")
    p_batch.add_argument("csv", type=Path, help="Path to tickets CSV")
    p_batch.set_defaults(func=cmd_batch)

    p_eval = sub.add_parser("evaluate", help="Run labeled evaluation")
    p_eval.add_argument("--data", type=Path, default=None)
    p_eval.add_argument("--max-rows", type=int, default=None)
    p_eval.set_defaults(func=cmd_evaluate)

    p_metrics = sub.add_parser("metrics", help="Show session latency/cost summary")
    p_metrics.set_defaults(func=cmd_metrics)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
