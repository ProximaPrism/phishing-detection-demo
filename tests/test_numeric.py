from types import SimpleNamespace
from app.components.numeric import extract_numeric_features

def test_extract_numeric_features():
    email = SimpleNamespace(
        sender_email="john123@example-security.com",
        sender_display_name="John",
        body="required_field",
        sent_datetime="2026-08-01 12:00:00"
    )
    feats = extract_numeric_features(email)
    assert feats.get("is_date_invalid") == 0
    assert feats.get("sender_email_digit_count") == 3
    assert feats.get("sender_email_has_hyphens") == 1
    assert feats.get("sender_username_length") == 7
    assert feats.get("does_body_contains_urls") == 0

def test_invalid_dt():
    email = SimpleNamespace(
        sender_email="test@example.com",
        sender_display_name="test",
        body="required_field",
        sent_datetime="invalid"
    )

    feats = extract_numeric_features(email)
    assert feats.get("is_date_invalid") == 1