from types import SimpleNamespace
from app.components.explain import explain_email

def test_detects_phishing_keywords():
    email = SimpleNamespace(
        subject="URGENT: Verify your account!",
        body="Click on the link below to verify your account!",
        sender_email="sec123@example.com",
        sender_display_name=None,
    )

    result = explain_email(email)
    assert "Contains common phishing language." in result["reasons"]
    assert "Contains external links / URLs" not in result["reasons"]

    assert "verify" in result["trigger_words"]
    assert "account" in result["trigger_words"]
    assert "urgent" in result["trigger_words"]

def test_detects_sender_patterns():
    email = SimpleNamespace(
        subject="Hi there",
        body="Hi",
        sender_email="very-long-user-name-123@example-long-domain.com",
        sender_display_name=None,
    )
    result = explain_email(email)

    assert "Sender does not have a display name." in result["reasons"]
    assert "Sender address contains hyphens." in result["reasons"]