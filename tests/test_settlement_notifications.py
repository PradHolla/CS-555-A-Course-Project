"""
Tests for settlement notification feature.

This module tests the notification system that alerts users
when someone records a payment to them.
"""

from unittest.mock import patch

from extensions import db
from models import Settlement, User

# === Settlement Notification Tests ===


def test_settlement_creation_sends_notification_to_recipient(client, app):
    """
    Test that creating a settlement sends a notification to the recipient.

    Acceptance Criteria:
    - Given a member settles a payment to me
    - When the transaction is saved
    - Then I receive a notification saying "X has paid $Y to you"
    """
    # Arrange
    with app.app_context():
        payer = User(email="neha@example.com")
        recipient = User(email="john@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

    # Simulate logged-in user
    with client.session_transaction() as sess:
        sess["user_id"] = payer_id
        sess["user_email"] = "neha@example.com"

    # Act
    with patch("services.notification_service._send_or_log_email") as mock_send:
        response = client.post(
            "/settlements",
            data={
                "amount": "500.00",
                "payer_id": payer_id,
                "recipient_id": recipient_id,
                "note": "Rent payment",
            },
            follow_redirects=False,
        )

        # Assert
        assert response.status_code == 302  # Redirect after success

        # Check notification was sent
        assert mock_send.called

        # Verify notification contains correct details
        call_args = mock_send.call_args
        recipient_email = call_args[0][0]
        subject = call_args[0][1]
        body = call_args[0][2]
        
        assert recipient_email == "john@example.com"
        assert "neha@example.com" in subject or "$500.00" in subject
        assert "$500.00" in body
        assert "Rent payment" in body


def test_settlement_notification_contains_detail_link(client, app):
    """
    Test that the notification contains a link to settlement details.

    Acceptance Criteria:
    - Given I tap the alert
    - Then I am taken to the settlement details page
    """
    # Arrange
    with app.app_context():
        payer = User(email="alice@example.com")
        recipient = User(email="bob@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch("services.notification_service._send_or_log_email") as mock_send:
        client.post(
            "/settlements",
            data={
                "amount": "250.50",
                "payer_id": payer_id,
                "recipient_id": recipient_id,
            },
        )

        # Assert
        assert mock_send.called

        # Verify notification contains link to settlement details
        call_args = mock_send.call_args
        body = call_args[0][2]
        assert "/settlements/" in body
        assert "View" in body and "details" in body


def test_settlement_without_note_sends_notification(client, app):
    """Test that settlement without a note still sends notification."""
    # Arrange
    with app.app_context():
        payer = User(email="charlie@example.com")
        recipient = User(email="diana@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch("services.notification_service._send_or_log_email") as mock_send:
        response = client.post(
            "/settlements",
            data={
                "amount": "100.00",
                "payer_id": payer_id,
                "recipient_id": recipient_id,
                # No note provided
            },
        )

        # Assert
        assert response.status_code == 302
        assert mock_send.called
        call_args = mock_send.call_args
        subject = call_args[0][1]
        body = call_args[0][2]
        assert "charlie@example.com" in subject or "$100.00" in subject
        assert "$100.00" in body


def test_settlement_detail_page_accessible(client, app):
    """
    Test that settlement detail page is accessible and displays correct info.

    This verifies the link in the email notification works correctly.
    """
    # Arrange
    with app.app_context():
        payer = User(email="eve@example.com")
        recipient = User(email="frank@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()

        settlement = Settlement(
            amount=750.00,
            payer_id=payer.id,
            recipient_id=recipient.id,
            note="Utilities",
        )
        db.session.add(settlement)
        db.session.commit()
        settlement_id = settlement.id
        recipient_id = recipient.id

    with client.session_transaction() as sess:
        sess["user_id"] = recipient_id

    # Act
    response = client.get(f"/settlements/{settlement_id}")

    # Assert
    assert response.status_code == 200
    assert b"eve@example.com" in response.data  # Payer email
    assert b"frank@example.com" in response.data  # Recipient email
    assert b"750.00" in response.data  # Amount
    assert b"Utilities" in response.data  # Note


def test_multiple_settlements_send_separate_notifications(client, app):
    """Test that multiple settlements send separate notifications."""
    # Arrange
    with app.app_context():
        payer = User(email="grace@example.com")
        recipient1 = User(email="henry@example.com")
        recipient2 = User(email="iris@example.com")
        db.session.add_all([payer, recipient1, recipient2])
        db.session.commit()
        payer_id = payer.id
        recipient1_id = recipient1.id
        recipient2_id = recipient2.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch("services.notification_service._send_or_log_email") as mock_send:
        # Create first settlement
        client.post(
            "/settlements",
            data={
                "amount": "200.00",
                "payer_id": payer_id,
                "recipient_id": recipient1_id,
            },
        )

        # Create second settlement
        client.post(
            "/settlements",
            data={
                "amount": "300.00",
                "payer_id": payer_id,
                "recipient_id": recipient2_id,
            },
        )

        # Assert - notifications were sent
        assert mock_send.called
        assert mock_send.call_count == 2

        # Verify each notification went to correct recipient
        recipients = [call[0][0] for call in mock_send.call_args_list]
        assert "henry@example.com" in recipients
        assert "iris@example.com" in recipients


def test_settlement_notification_is_sent(client, app):
    """Test that notification is sent when settlement is created."""
    # Arrange
    with app.app_context():
        payer = User(email="jack@example.com")
        recipient = User(email="kate@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch("services.notification_service._send_or_log_email") as mock_send:
        client.post(
            "/settlements",
            data={
                "amount": "150.00",
                "payer_id": payer_id,
                "recipient_id": recipient_id,
            },
        )

        # Assert
        assert mock_send.called
        call_args = mock_send.call_args
        recipient_email = call_args[0][0]
        assert recipient_email == "kate@example.com"
