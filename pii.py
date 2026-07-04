"""PII detection and redaction for support ticket logging."""

from __future__ import annotations

import re
from typing import Callable

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
)
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9\s.,#-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b",
    re.IGNORECASE,
)

REDACTION_MAP: dict[str, tuple[re.Pattern[str], str]] = {
    "email": (EMAIL_PATTERN, "[REDACTED_EMAIL]"),
    "phone": (PHONE_PATTERN, "[REDACTED_PHONE]"),
    "address": (ADDRESS_PATTERN, "[REDACTED_ADDRESS]"),
    "credit_card": (CREDIT_CARD_PATTERN, "[REDACTED_CARD]"),
    "ssn": (SSN_PATTERN, "[REDACTED_SSN]"),
}


def detect_pii(text: str) -> list[str]:
    """Return sorted list of PII type names found in text."""
    found: list[str] = []
    for name, (pattern, _) in REDACTION_MAP.items():
        if pattern.search(text):
            found.append(name)
    return found


def redact_pii(text: str, types: list[str] | None = None) -> str:
    """Redact PII from text. If types is None, redact all detected types."""
    redacted = text
    target_types = types if types is not None else list(REDACTION_MAP.keys())
    for pii_type in target_types:
        if pii_type in REDACTION_MAP:
            pattern, replacement = REDACTION_MAP[pii_type]
            redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_for_logging(text: str) -> tuple[str, list[str]]:
    """Detect and redact PII before writing to logs."""
    detected = detect_pii(text)
    return redact_pii(text, detected), detected


def sanitize_reply(reply: str) -> str:
    """Ensure drafted replies do not leak PII."""
    return redact_pii(reply)
