"""Tests for support policy compliance in draft replies."""

from draft_reply import load_support_policy


def test_policy_file_exists():
    policy = load_support_policy()
    assert "Refund" in policy or "refund" in policy
    assert len(policy) > 200


def test_policy_covers_escalation():
    policy = load_support_policy().lower()
    assert "escalat" in policy
    assert "pii" in policy or "privacy" in policy


def test_policy_refund_rules():
    policy = load_support_policy().lower()
    assert "do not promise" in policy or "will review" in policy
