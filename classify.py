"""Ticket classification: category, priority, sentiment, SLA risk."""

from __future__ import annotations

from llm_client import LLMUsage, call_llm_validated
from prompts import CLASSIFICATION_FEW_SHOT, CLASSIFICATION_SYSTEM_PROMPT, RETRY_VALIDATION_PROMPT
from schemas import ClassificationResult


def classify_ticket(
    customer_message: str,
    *,
    ticket_id: str = "unknown",
    temperature: float = 0.1,
) -> tuple[ClassificationResult, LLMUsage]:
    """Classify a support ticket using few-shot prompting and structured JSON output."""
    return call_llm_validated(
        CLASSIFICATION_SYSTEM_PROMPT,
        f"Customer message:\n{customer_message}",
        ClassificationResult,
        few_shot=CLASSIFICATION_FEW_SHOT,
        temperature=temperature,
        retry_prompt_template=RETRY_VALIDATION_PROMPT,
        ticket_id=f"{ticket_id}:classify",
    )
