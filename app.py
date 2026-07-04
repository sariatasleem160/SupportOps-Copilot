"""Streamlit web app for SupportOps Copilot."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard import plot_category_distribution, summarize_tickets
from draft_reply import load_support_policy
from llm_client import SESSION_METRICS
from pipeline import process_ticket
from pii import redact_for_logging

RESULTS_DIR = Path(__file__).parent / "results"
DATA_DIR = Path(__file__).parent / "data"


st.set_page_config(
    page_title="SupportOps Copilot",
    page_icon="🎫",
    layout="wide",
)

st.title("SupportOps Copilot")
st.caption("Messy ticket → structured analysis → safe draft → dashboard → metrics")

if "processed" not in st.session_state:
    st.session_state.processed = []
if "logs" not in st.session_state:
    st.session_state.logs = []


tab_analyze, tab_batch, tab_dashboard, tab_policy = st.tabs(
    ["Analyze Ticket", "Batch Upload", "Dashboard", "Support Policy"]
)

with tab_analyze:
    st.subheader("Analyze a support ticket")
    ticket_id = st.text_input("Ticket ID", value="T-1001")
    message = st.text_area(
        "Customer message",
        height=180,
        placeholder="Paste the customer support message here...",
    )

    if st.button("Analyze", type="primary", disabled=not message.strip()):
        with st.spinner("Running classify → extract → draft..."):
            analysis, log_payload = process_ticket(message.strip(), ticket_id=ticket_id)
            st.session_state.processed.append(analysis.model_dump(mode="json"))
            st.session_state.logs.append(log_payload)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Classification**")
            st.json(
                {
                    "category": analysis.category.value,
                    "priority": analysis.priority.value,
                    "sentiment": analysis.sentiment.value,
                    "sla_risk": analysis.sla_risk,
                    "confidence": analysis.confidence,
                }
            )
        with col2:
            st.markdown("**Extraction**")
            st.json(
                {
                    "product": analysis.product,
                    "customer_request": analysis.customer_request,
                    "missing_information": analysis.missing_information,
                    "refund_request": analysis.refund_request,
                    "pii_detected": analysis.pii_detected,
                }
            )

        st.markdown("**Safe draft reply**")
        st.info(analysis.safe_reply)

        redacted, detected = redact_for_logging(message)
        st.markdown("**PII-safe log preview**")
        st.code(
            json.dumps(
                {"redacted_message": redacted, "pii_detected": detected},
                indent=2,
            ),
            language="json",
        )

        if analysis.priority.value == "urgent" or analysis.sla_risk:
            st.error("Escalation queue: urgent / SLA-risk ticket flagged for immediate review.")

with tab_batch:
    st.subheader("Batch CSV upload")
    st.write("CSV must include `ticket_id` and `customer_message` columns.")
    uploaded = st.file_uploader("Upload tickets CSV", type=["csv"])

    if uploaded and st.button("Process batch"):
        df = pd.read_csv(uploaded)
        if "customer_message" not in df.columns:
            st.error("CSV must contain a customer_message column.")
        else:
            progress = st.progress(0)
            batch_results = []
            for i, row in df.iterrows():
                tid = str(row.get("ticket_id", f"batch-{i}"))
                msg = str(row["customer_message"])
                analysis, log_payload = process_ticket(msg, ticket_id=tid)
                batch_results.append(analysis.model_dump(mode="json"))
                st.session_state.logs.append(log_payload)
                progress.progress((i + 1) / len(df))
            st.session_state.processed.extend(batch_results)
            st.success(f"Processed {len(batch_results)} tickets.")
            st.dataframe(pd.DataFrame(batch_results))

with tab_dashboard:
    st.subheader("Ticket pattern dashboard")
    analyses = st.session_state.processed
    if not analyses:
        st.info("Analyze tickets first to populate the dashboard.")
    else:
        summary = summarize_tickets(analyses)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total tickets", summary["total_tickets"])
        m2.metric("SLA risk", summary["sla_risk_count"])
        m3.metric("Refund requests", summary["refund_request_count"])
        m4.metric("Avg confidence", summary["avg_confidence"])

        st.json(summary)

        chart_path = plot_category_distribution(analyses)
        st.image(str(chart_path), caption="Category distribution")

        metrics = SESSION_METRICS.summary()
        st.markdown("**Latency & cost (this session)**")
        st.json(metrics)

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_DIR / "latency_cost_summary.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

with tab_policy:
    st.subheader("Support policy")
    try:
        st.markdown(load_support_policy())
    except FileNotFoundError as exc:
        st.warning(str(exc))
