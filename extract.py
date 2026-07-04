"""Structured fact extraction from support tickets."""

from __future__ import annotations

from llm_client import LLMUsage, call_llm_validated
from pii import detect_pii
from prompts import EXTRACTION_SYSTEM_PROMPT, RETRY_VALIDATION_PROMPT
from schemas import ExtractionResult


def extract_ticket_facts(
    customer_message: str,
    *,
    ticket_id: str = "unknown",
    temperature: float = 0.1,
) -> tuple[ExtractionResult, LLMUsage]:
    """Extract product, request summary, missing info, refund flag, and PII types."""
    result, usage = call_llm_validated(
        EXTRACTION_SYSTEM_PROMPT,
        f"Customer message:\n{customer_message}",
        ExtractionResult,
        temperature=temperature,
        retry_prompt_template=RETRY_VALIDATION_PROMPT,
        ticket_id=f"{ticket_id}:extract",
    )

    # Merge regex-based PII detection with model output for reliability.
    regex_pii = detect_pii(customer_message)
    merged = list(dict.fromkeys([*result.pii_detected, *regex_pii]))
    result = result.model_copy(update={"pii_detected": merged})
    return result, usage
