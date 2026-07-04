"""Tests for PII detection and redaction."""

from pii import detect_pii, redact_for_logging, redact_pii, sanitize_reply


def test_detect_email():
    text = "Contact me at alice@example.com for updates."
    assert "email" in detect_pii(text)


def test_detect_phone():
    text = "Call me at (555) 123-4567 tomorrow."
    assert "phone" in detect_pii(text)


def test_detect_address():
    text = "Ship to 123 Main Street, Springfield."
    assert "address" in detect_pii(text)


def test_redact_email():
    text = "Email: bob@test.org"
    redacted = redact_pii(text, ["email"])
    assert "bob@test.org" not in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_redact_for_logging():
    text = "Reach me at carol@demo.com or 555-987-6543."
    redacted, detected = redact_for_logging(text)
    assert "carol@demo.com" not in redacted
    assert "555-987-6543" not in redacted
    assert "email" in detected
    assert "phone" in detected


def test_sanitize_reply():
    reply = "We will email you at user@secret.com shortly."
    clean = sanitize_reply(reply)
    assert "user@secret.com" not in clean


def test_credit_card_redaction():
    text = "Card 4111 1111 1111 1111 was charged."
    assert "credit_card" in detect_pii(text)
    redacted = redact_pii(text)
    assert "4111" not in redacted


def test_ssn_redaction():
    text = "SSN on file: 123-45-6789"
    assert "ssn" in detect_pii(text)
    redacted = redact_pii(text)
    assert "123-45-6789" not in redacted
