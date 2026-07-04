"""End-to-end ticket processing pipeline."""

from __future__ import annotations

from classify import classify_ticket
from draft_reply import draft_reply
from extract import extract_ticket_facts
from llm_client import LLMUsage
from pii import redact_for_logging
from schemas import TicketAnalysis


def process_ticket(
    customer_message: str,
    *,
    ticket_id: str = "unknown",
) -> tuple[TicketAnalysis, dict[str, str]]:
    """Run classify → extract → draft → validate into TicketAnalysis."""
    classification, classify_usage = classify_ticket(
        customer_message, ticket_id=ticket_id
    )
    extraction, extract_usage = extract_ticket_facts(
        customer_message, ticket_id=ticket_id
    )
    safe_reply, draft_usage = draft_reply(
        customer_message,
        classification,
        extraction,
        ticket_id=ticket_id,
    )

    analysis = TicketAnalysis(
        category=classification.category,
        priority=classification.priority,
        sentiment=classification.sentiment,
        sla_risk=classification.sla_risk,
        product=extraction.product,
        customer_request=extraction.customer_request,
        missing_information=extraction.missing_information,
        refund_request=extraction.refund_request,
        pii_detected=extraction.pii_detected,
        safe_reply=safe_reply,
        confidence=classification.confidence,
    )

    redacted_message, _ = redact_for_logging(customer_message)
    log_payload = {
        "ticket_id": ticket_id,
        "redacted_message": redacted_message,
        "analysis": analysis.model_dump(mode="json"),
    }
    total_usage = LLMUsage(
        input_tokens=classify_usage.input_tokens
        + extract_usage.input_tokens
        + draft_usage.input_tokens,
        output_tokens=classify_usage.output_tokens
        + extract_usage.output_tokens
        + draft_usage.output_tokens,
        latency_ms=classify_usage.latency_ms
        + extract_usage.latency_ms
        + draft_usage.latency_ms,
        model=classify_usage.model,
    )
    log_payload["usage"] = {
        "latency_ms": round(total_usage.latency_ms, 2),
        "estimated_cost_usd": round(total_usage.estimated_cost_usd, 6),
    }
    return analysis, log_payload
