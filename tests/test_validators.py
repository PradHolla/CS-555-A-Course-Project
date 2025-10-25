"""Tests for validation utilities."""

from utils.validators import is_valid_email


def test_valid_email_formats():
    """Test that valid email formats are accepted."""
    valid_emails = [
        "user@example.com",
        "john.doe@company.co.uk",
        "test+tag@domain.org",
        "user_name@sub.domain.com",
        "a@b.co",
        "test123@example.com",
        "user-name@example.com",
    ]

    for email in valid_emails:
        assert is_valid_email(email), f"Should accept valid email: {email}"


def test_invalid_email_formats():
    """Test that invalid email formats are rejected."""
    invalid_emails = [
        "notanemail",
        "@example.com",
        "test@",
        "test@@example.com",
        "test@example",
        "",
        None,
        ".test@example.com",
        "test.@example.com",
        "test@.example.com",
        "test@example..com",
    ]

    for email in invalid_emails:
        assert not is_valid_email(email), f"Should reject invalid email: {email}"


def test_email_with_special_characters():
    """Test emails with special but valid characters."""
    special_emails = [
        "user+filter@example.com",
        "user_name@example.com",
        "user-name@example.com",
        "user.name@example.com",
        "user%test@example.com",
    ]

    for email in special_emails:
        assert is_valid_email(email), f"Should accept email with special chars: {email}"


def test_email_with_subdomains():
    """Test emails with multiple subdomain levels."""
    subdomain_emails = [
        "user@mail.example.com",
        "user@mail.company.example.com",
        "user@sub1.sub2.example.org",
    ]

    for email in subdomain_emails:
        assert is_valid_email(email), f"Should accept email with subdomains: {email}"


def test_empty_string_returns_false():
    """Test that empty string returns False."""
    assert not is_valid_email("")


def test_none_returns_false():
    """Test that None returns False."""
    assert not is_valid_email(None)
