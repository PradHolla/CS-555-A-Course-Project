"""Tests for payment reminder notifications."""

import pytest
from unittest.mock import patch

from extensions import db
from models import User
from services.notification_service import notify_debtor_reminder


def test_send_reminder_notification_email_content(app):
    """Test reminder email contains correct information."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.commit()

        # Mock email sending
        with patch("services.notification_service._send_or_log_email") as mock_send:
            # Send reminder
            notify_debtor_reminder(
                creditor=creditor,
                debtor=debtor,
                amount=50.00,
                breakdown=[
                    {"description": "Dinner", "amount": 30.00, "date": "2025-01-15"},
                    {"description": "Movie", "amount": 20.00, "date": "2025-01-16"},
                ],
            )

            # Verify email was sent
            assert mock_send.called
            assert mock_send.call_count == 1

            # Check email parameters
            call_args = mock_send.call_args
            to_email = call_args[0][0]
            subject = call_args[0][1]
            body = call_args[0][2]
            html_body = call_args[0][3] if len(call_args[0]) > 3 else call_args.kwargs.get("html_body", "")

            # Verify recipient
            assert to_email == "bob@example.com"

            # Verify subject
            assert "Payment Reminder from Alice" in subject

            # Verify plain text body content
            assert "Bob" in body
            assert "Alice" in body
            assert "$50.00" in body
            assert "Dinner" in body
            assert "$30.00" in body
            assert "Movie" in body
            assert "$20.00" in body

            # Verify HTML body content
            assert "Bob" in html_body
            assert "Alice" in html_body
            assert "$50.00" in html_body
            assert "Dinner" in html_body
            assert "Movie" in html_body


def test_send_reminder_notification_without_breakdown(app):
    """Test reminder email works without expense breakdown."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.commit()

        # Mock email sending
        with patch("services.notification_service._send_or_log_email") as mock_send:
            # Send reminder without breakdown
            notify_debtor_reminder(creditor=creditor, debtor=debtor, amount=25.50, breakdown=None)

            # Verify email was sent
            assert mock_send.called

            # Check email content
            call_args = mock_send.call_args
            body = call_args[0][2]

            # Verify basic content
            assert "Bob" in body
            assert "Alice" in body
            assert "$25.50" in body


def test_send_reminder_uses_email_fallback(app):
    """Test reminder uses email when display name not set."""
    with app.app_context():
        # Create users without display names
        creditor = User(email="creditor@example.com")
        debtor = User(email="debtor@example.com")
        db.session.add_all([creditor, debtor])
        db.session.commit()

        # Mock email sending
        with patch("services.notification_service._send_or_log_email") as mock_send:
            # Send reminder
            notify_debtor_reminder(creditor=creditor, debtor=debtor, amount=100.00)

            # Verify email was sent
            assert mock_send.called

            # Check that email addresses are used in subject/body
            call_args = mock_send.call_args
            subject = call_args[0][1]
            body = call_args[0][2]

            assert "creditor@example.com" in subject or "creditor@example.com" in body


def test_send_reminder_includes_balance_link(app):
    """Test reminder email includes link to balance summary."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.commit()

        # Mock email sending
        with patch("services.notification_service._send_or_log_email") as mock_send:
            # Send reminder
            notify_debtor_reminder(creditor=creditor, debtor=debtor, amount=75.00)

            # Verify email was sent
            assert mock_send.called

            # Check for balance URL
            call_args = mock_send.call_args
            body = call_args[0][2]
            html_body = call_args[0][3] if len(call_args[0]) > 3 else call_args.kwargs.get("html_body", "")

            assert "balance-summary" in body or "balance" in body.lower()
            assert "balance-summary" in html_body or "balance" in html_body.lower()


def test_send_reminder_logs_when_email_disabled(app):
    """Test reminder logs to terminal when EMAIL_ENABLED is False."""
    with app.app_context():
        # Ensure EMAIL_ENABLED is False
        app.config["EMAIL_ENABLED"] = False

        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.commit()

        # Send reminder (should log instead of sending email)
        notify_debtor_reminder(creditor=creditor, debtor=debtor, amount=50.00)

        # No exception should be raised - function should complete successfully


def test_send_reminder_with_empty_breakdown(app):
    """Test reminder handles empty breakdown list gracefully."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.commit()

        # Mock email sending
        with patch("services.notification_service._send_or_log_email") as mock_send:
            # Send reminder with empty breakdown
            notify_debtor_reminder(
                creditor=creditor, debtor=debtor, amount=30.00, breakdown=[]
            )

            # Verify email was sent
            assert mock_send.called

            # Check email content doesn't break
            call_args = mock_send.call_args
            body = call_args[0][2]
            assert "Bob" in body
            assert "$30.00" in body
