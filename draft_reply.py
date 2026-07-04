"""Policy-grounded safe reply drafting."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from llm_client import LLMUsage, call_llm_validated
from pii import sanitize_reply
from prompts import DRAFT_REPLY_SYSTEM_PROMPT, RETRY_VALIDATION_PROMPT
from schemas import ClassificationResult, ExtractionResult

POLICY_PATH = Path(__file__).parent / "data" / "support_policy.md"


class DraftReplyResult(BaseModel):
    safe_reply: str = Field(min_length=10)


def load_support_policy(path: Path | None = None) -> str:
    policy_file = path or POLICY_PATH
    if not policy_file.exists():
        raise FileNotFoundError(f"Support policy not found: {policy_file}")
    return policy_file.read_text(encoding="utf-8")


def draft_reply(
    customer_message: str,
    classification: ClassificationResult,
    extraction: ExtractionResult,
    *,
    ticket_id: str = "unknown",
    policy_text: str | None = None,
    temperature: float = 0.4,
) -> tuple[str, LLMUsage]:
    """Draft a policy-compliant reply grounded in support_policy.md."""
    policy = policy_text or load_support_policy()
    context = (
        f"SUPPORT POLICY:\n{policy}\n\n"
        f"CUSTOMER MESSAGE:\n{customer_message}\n\n"
        f"CLASSIFICATION:\n"
        f"- category: {classification.category.value}\n"
        f"- priority: {classification.priority.value}\n"
        f"- sentiment: {classification.sentiment.value}\n"
        f"- sla_risk: {classification.sla_risk}\n\n"
        f"EXTRACTED FACTS:\n"
        f"- product: {extraction.product}\n"
        f"- customer_request: {extraction.customer_request}\n"
        f"- missing_information: {extraction.missing_information}\n"
        f"- refund_request: {extraction.refund_request}\n"
    )

    result, usage = call_llm_validated(
        DRAFT_REPLY_SYSTEM_PROMPT,
        context,
        DraftReplyResult,
        temperature=temperature,
        retry_prompt_template=RETRY_VALIDATION_PROMPT,
        ticket_id=f"{ticket_id}:draft",
    )
    return sanitize_reply(result.safe_reply), usage
