"""Pydantic schemas for SupportOps Copilot structured outputs."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    BILLING = "billing"
    TECHNICAL_BUG = "technical_bug"
    ACCOUNT_ACCESS = "account_access"
    REFUND = "refund"
    SHIPPING = "shipping"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Sentiment(str, Enum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class PIIType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"


class TicketAnalysis(BaseModel):
    """Full structured analysis for a support ticket."""

    category: Category
    priority: Priority
    sentiment: Sentiment
    sla_risk: bool
    product: Optional[str] = None
    customer_request: str
    missing_information: list[str] = Field(default_factory=list)
    refund_request: bool
    pii_detected: list[str] = Field(default_factory=list)
    safe_reply: str = ""
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("pii_detected")
    @classmethod
    def normalize_pii_types(cls, values: list[str]) -> list[str]:
        allowed = {p.value for p in PIIType}
        normalized: list[str] = []
        for value in values:
            key = value.strip().lower().replace("-", "_")
            if key in allowed and key not in normalized:
                normalized.append(key)
        return normalized

    @field_validator("missing_information")
    @classmethod
    def strip_missing_info(cls, values: list[str]) -> list[str]:
        return [v.strip() for v in values if v and v.strip()]


class ClassificationResult(BaseModel):
    category: Category
    priority: Priority
    sentiment: Sentiment
    sla_risk: bool
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    product: Optional[str] = None
    customer_request: str
    missing_information: list[str] = Field(default_factory=list)
    refund_request: bool
    pii_detected: list[str] = Field(default_factory=list)

    @field_validator("missing_information")
    @classmethod
    def strip_missing_info(cls, values: list[str]) -> list[str]:
        return [v.strip() for v in values if v and v.strip()]


class LatencyCostRecord(BaseModel):
    ticket_id: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    model: str
