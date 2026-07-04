"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from schemas import Category, ClassificationResult, ExtractionResult, TicketAnalysis


def test_ticket_analysis_valid():
    analysis = TicketAnalysis(
        category=Category.BILLING,
        priority="high",
        sentiment="negative",
        sla_risk=True,
        product="Pro",
        customer_request="Fix duplicate charge",
        missing_information=["order ID"],
        refund_request=False,
        pii_detected=["email"],
        safe_reply="Thank you for reaching out. We will review your billing.",
        confidence=0.9,
    )
    assert analysis.category == Category.BILLING
    assert analysis.pii_detected == ["email"]


def test_pii_detected_deduplication():
    analysis = TicketAnalysis(
        category=Category.OTHER,
        priority="low",
        sentiment="neutral",
        sla_risk=False,
        customer_request="Help",
        refund_request=False,
        pii_detected=["email", "email", "phone"],
        safe_reply="We are here to help with your request today.",
        confidence=0.5,
    )
    assert analysis.pii_detected == ["email", "phone"]


def test_confidence_bounds():
    with pytest.raises(ValidationError):
        TicketAnalysis(
            category=Category.OTHER,
            priority="low",
            sentiment="neutral",
            sla_risk=False,
            customer_request="Help",
            refund_request=False,
            confidence=1.5,
            safe_reply="Valid reply text here for testing.",
        )


def test_classification_result():
    result = ClassificationResult(
        category="technical_bug",
        priority="medium",
        sentiment="negative",
        sla_risk=False,
        confidence=0.88,
    )
    assert result.category.value == "technical_bug"


def test_extraction_strips_empty_missing_info():
    result = ExtractionResult(
        customer_request="Reset password",
        missing_information=["", "  ", "account email"],
        refund_request=False,
    )
    assert result.missing_information == ["account email"]
