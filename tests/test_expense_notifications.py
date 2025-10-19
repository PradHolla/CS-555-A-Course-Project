"""
Tests for expense notification feature.

This module tests the email notification system that alerts participants
when a new expense is added.
"""

import pytest
from flask import url_for
from models import User, Expense
from extensions import db, mail


def test_expense_creation_sends_email_to_participants(client, app):
    """
    Test that creating an expense sends email notifications to participants.
    
    Acceptance Criteria:
    - Given a user adds an expense with participants
    - When the expense is saved
    - Then all participants receive an email notification
    """
    # Arrange
    with app.app_context():
        payer = User(email="payer@example.com")
        participant1 = User(email="participant1@example.com")
        participant2 = User(email="participant2@example.com")
        db.session.add_all([payer, participant1, participant2])
        db.session.commit()
        payer_id = payer.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id
        sess["user_email"] = "payer@example.com"

    # Act
    with mail.record_messages() as outbox:
        response = client.post(
            "/expense-splitter",
            data={
                "description": "Dinner at restaurant",
                "amount": "150.00",
                "payer": "John",
                "participants": "participant1@example.com, participant2@example.com",
            },
            follow_redirects=False,
        )

        # Assert
        assert response.status_code == 302  # Redirect after success
        
        # Check emails were sent to both participants
        assert len(outbox) == 2
        
        # Verify email recipients
        recipients = [email.recipients[0] for email in outbox]
        assert "participant1@example.com" in recipients
        assert "participant2@example.com" in recipients
        
        # Verify email content
        for email in outbox:
            assert "New expense added" in email.subject
            assert "Dinner at restaurant" in email.body
            assert "$150.00" in email.body
            assert "John" in email.body


def test_expense_without_participants_no_email(client, app):
    """Test that expense without participants doesn't send emails."""
    # Arrange
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = user_id

    # Act
    with mail.record_messages() as outbox:
        response = client.post(
            "/expense-splitter",
            data={
                "description": "Solo expense",
                "amount": "50.00",
                "payer": "Alice",
                "participants": "",  # No participants
            },
        )

        # Assert
        assert response.status_code == 302
        assert len(outbox) == 0  # No emails sent


def test_expense_email_contains_all_details(client, app):
    """Test that notification email contains all expense details."""
    # Arrange
    with app.app_context():
        payer = User(email="payer@example.com")
        participant = User(email="participant@example.com")
        db.session.add_all([payer, participant])
        db.session.commit()
        payer_id = payer.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with mail.record_messages() as outbox:
        response = client.post(
            "/expense-splitter",
            data={
                "description": "Movie tickets",
                "amount": "30.00",
                "payer": "Bob",
                "participants": "participant@example.com",
            },
        )

        # Assert
        assert len(outbox) == 1
        email = outbox[0]
        
        # Verify all details are in email
        assert "Movie tickets" in email.body
        assert "$30.00" in email.body
        assert "Bob" in email.body
        assert "participant@example.com" in email.body


def test_multiple_expenses_send_separate_emails(client, app):
    """Test that multiple expenses send separate email notifications."""
    # Arrange
    with app.app_context():
        payer = User(email="payer@example.com")
        participant = User(email="participant@example.com")
        db.session.add_all([payer, participant])
        db.session.commit()
        payer_id = payer.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with mail.record_messages() as outbox:
        # Create first expense
        client.post(
            "/expense-splitter",
            data={
                "description": "Lunch",
                "amount": "25.00",
                "payer": "Charlie",
                "participants": "participant@example.com",
            },
        )
        
        # Create second expense
        client.post(
            "/expense-splitter",
            data={
                "description": "Coffee",
                "amount": "10.00",
                "payer": "Charlie",
                "participants": "participant@example.com",
            },
        )

        # Assert
        assert len(outbox) == 2
        
        # Verify different expense details in each email
        assert "Lunch" in outbox[0].body
        assert "Coffee" in outbox[1].body


def test_expense_notification_sender_configured(client, app):
    """Test that email sender is properly configured."""
    # Arrange
    with app.app_context():
        payer = User(email="payer@example.com")
        participant = User(email="participant@example.com")
        db.session.add_all([payer, participant])
        db.session.commit()
        payer_id = payer.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with mail.record_messages() as outbox:
        client.post(
            "/expense-splitter",
            data={
                "description": "Test expense",
                "amount": "100.00",
                "payer": "Diana",
                "participants": "participant@example.com",
            },
        )

        # Assert
        assert len(outbox) == 1
        email = outbox[0]
        assert email.sender is not None
