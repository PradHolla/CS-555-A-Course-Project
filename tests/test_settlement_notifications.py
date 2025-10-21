"""
Tests for settlement notification feature.

This module tests the notification system that alerts users
when someone records a payment to them.
"""

import pytest
from unittest.mock import patch
from flask import url_for
from models import User, Settlement
from extensions import db


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
        payer = User(name="Neha", email="neha@example.com")
        recipient = User(name="John", email="john@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

    # Simulate logged-in user
    with client.session_transaction() as sess:
        sess["user_id"] = payer_id
        sess["user_email"] = "neha@example.com"

    # Act
    with patch('services.notification_service.print') as mock_print:
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
        
        # Check notification was printed
        assert mock_print.called
        
        # Verify notification contains correct details
        printed_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert "john@example.com" in printed_output
        assert "Neha" in printed_output
        assert "$500.00" in printed_output
        assert "Rent payment" in printed_output


def test_settlement_notification_contains_detail_link(client, app):
    """
    Test that the notification contains a link to settlement details.
    
    Acceptance Criteria:
    - Given I tap the alert
    - Then I am taken to the settlement details page
    """
    # Arrange
    with app.app_context():
        payer = User(name="Alice", email="alice@example.com")
        recipient = User(name="Bob", email="bob@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch('services.notification_service.print') as mock_print:
        response = client.post(
            "/settlements",
            data={
                "amount": "250.50",
                "payer_id": payer_id,
                "recipient_id": recipient_id,
            },
        )

        # Assert
        assert mock_print.called
        
        # Verify notification contains link to settlement details
        printed_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert "/settlements/" in printed_output
        assert "View details:" in printed_output


def test_settlement_without_note_sends_notification(client, app):
    """Test that settlement without a note still sends notification."""
    # Arrange
    with app.app_context():
        payer = User(name="Charlie", email="charlie@example.com")
        recipient = User(name="Diana", email="diana@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch('services.notification_service.print') as mock_print:
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
        assert mock_print.called
        printed_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert "Charlie has paid $100.00 to you" in printed_output


def test_settlement_detail_page_accessible(client, app):
    """
    Test that settlement detail page is accessible and displays correct info.
    
    This verifies the link in the email notification works correctly.
    """
    # Arrange
    with app.app_context():
        payer = User(name="Eve", email="eve@example.com")
        recipient = User(name="Frank", email="frank@example.com")
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
    assert b"Eve" in response.data  # Payer name
    assert b"Frank" in response.data  # Recipient name
    assert b"750.00" in response.data  # Amount
    assert b"Utilities" in response.data  # Note


def test_multiple_settlements_send_separate_notifications(client, app):
    """Test that multiple settlements send separate notifications."""
    # Arrange
    with app.app_context():
        payer = User(name="Grace", email="grace@example.com")
        recipient1 = User(name="Henry", email="henry@example.com")
        recipient2 = User(name="Iris", email="iris@example.com")
        db.session.add_all([payer, recipient1, recipient2])
        db.session.commit()
        payer_id = payer.id
        recipient1_id = recipient1.id
        recipient2_id = recipient2.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch('services.notification_service.print') as mock_print:
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

        # Assert - notifications were printed
        assert mock_print.called
        
        # Verify each notification went to correct recipient
        printed_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert "henry@example.com" in printed_output
        assert "iris@example.com" in printed_output


def test_settlement_notification_is_sent(client, app):
    """Test that notification is sent when settlement is created."""
    # Arrange
    with app.app_context():
        payer = User(name="Jack", email="jack@example.com")
        recipient = User(name="Kate", email="kate@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch('services.notification_service.print') as mock_print:
        client.post(
            "/settlements",
            data={
                "amount": "150.00",
                "payer_id": payer_id,
                "recipient_id": recipient_id,
            },
        )

        # Assert
        assert mock_print.called
        printed_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert "kate@example.com" in printed_output
