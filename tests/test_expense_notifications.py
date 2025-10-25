"""
Tests for expense notification feature.

This module tests the notification system that alerts participants
when a new expense is added.
"""

from unittest.mock import patch

from extensions import db
from models import User


def test_expense_creation_sends_notification_to_participants(client, app):
    """
    Test that creating an expense sends notifications to participants.

    Acceptance Criteria:
    - Given a user adds an expense with participants
    - When the expense is saved
    - Then all participants receive a notification
    """
    # Arrange
    from models import Group

    with app.app_context():
        payer = User(email="payer@example.com")
        participant1 = User(email="participant1@example.com")
        participant2 = User(email="participant2@example.com")
        john = User(email="john@example.com")
        alice = User(email="alice@example.com")
        bob_user = User(email="bob@example.com")
        db.session.add_all([payer, participant1, participant2, john, alice, bob_user])
        db.session.flush()

        # Create a group with members
        group = Group(name="Dinner Group", created_by_id=john.id)
        group.members.extend([john, alice, bob_user])
        db.session.add(group)
        db.session.commit()

        payer_id = payer.id
        group_id = group.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id
        sess["user_email"] = "payer@example.com"

    # Act
    with patch("services.notification_service.print") as mock_print:
        response = client.post(
            "/expense-splitter",
            data={
                "description": "Dinner at restaurant",
                "amount": "150.00",
                "payer": "john@example.com",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["john@example.com", "alice@example.com", "bob@example.com"],
            },
            follow_redirects=False,
        )

        # Assert
        assert response.status_code == 302  # Redirect after success

        # Check notifications were printed
        assert mock_print.called

        # Verify notification content
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "john@example.com" in printed_output or "alice@example.com" in printed_output
        assert "New expense added" in printed_output
        assert "Dinner at restaurant" in printed_output
        assert "$150.00" in printed_output


def test_expense_without_participants_no_notification(client, app):
    """Test that expense without participants doesn't send notifications."""
    # Arrange
    from models import Group

    with app.app_context():
        user = User(email="user@example.com")
        alice = User(email="alice@example.com")
        db.session.add_all([user, alice])
        db.session.flush()

        # Create a group (required for expense creation)
        group = Group(name="Solo Group", created_by_id=alice.id)
        group.members.append(alice)
        db.session.add(group)
        db.session.commit()

        user_id = user.id
        group_id = group.id

    with client.session_transaction() as sess:
        sess["user_id"] = user_id

    # Act
    with patch("services.notification_service.notify_expense_participants") as mock_notify:
        response = client.post(
            "/expense-splitter",
            data={
                "description": "Solo expense",
                "amount": "50.00",
                "payer": "Alice",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": [],  # No participants selected
            },
        )

        # Assert - Should fail validation (no participants selected)
        assert response.status_code == 302
        assert not mock_notify.called  # No notifications sent because validation failed


def test_expense_notification_contains_all_details(client, app):
    """Test that notification contains all expense details."""
    # Arrange
    from models import Group

    with app.app_context():
        payer = User(email="payer@example.com")
        participant = User(email="participant@example.com")
        bob_user = User(email="bob@example.com")
        charlie = User(email="charlie@example.com")
        db.session.add_all([payer, participant, bob_user, charlie])
        db.session.flush()

        # Create a group with members
        group = Group(name="Movie Group", created_by_id=bob_user.id)
        group.members.extend([bob_user, charlie])
        db.session.add(group)
        db.session.commit()

        payer_id = payer.id
        group_id = group.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch("services.notification_service.print") as mock_print:
        client.post(
            "/expense-splitter",
            data={
                "description": "Movie tickets",
                "amount": "30.00",
                "payer": "bob@example.com",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["bob@example.com", "charlie@example.com"],
            },
        )

        # Assert
        assert mock_print.called

        # Verify all details are in notification
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Movie tickets" in printed_output
        assert "$30.00" in printed_output
        assert "bob@example.com" in printed_output or "charlie@example.com" in printed_output


def test_multiple_expenses_send_separate_notifications(client, app):
    """Test that multiple expenses send separate notifications."""
    # Arrange
    from models import Group

    with app.app_context():
        payer = User(email="payer@example.com")
        participant = User(email="participant@example.com")
        charlie = User(email="charlie@example.com")
        dave = User(email="dave@example.com")
        db.session.add_all([payer, participant, charlie, dave])
        db.session.flush()

        # Create a group with members
        group = Group(name="Lunch Group", created_by_id=charlie.id)
        group.members.extend([charlie, dave])
        db.session.add(group)
        db.session.commit()

        payer_id = payer.id
        group_id = group.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch("services.notification_service.print") as mock_print:
        # Create first expense
        client.post(
            "/expense-splitter",
            data={
                "description": "Lunch",
                "amount": "25.00",
                "payer": "charlie@example.com",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["charlie@example.com", "dave@example.com"],
            },
        )

        # Create second expense
        client.post(
            "/expense-splitter",
            data={
                "description": "Coffee",
                "amount": "10.00",
                "payer": "charlie@example.com",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["charlie@example.com", "dave@example.com"],
            },
        )

        # Assert
        assert mock_print.called

        # Verify different expense details in notifications
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Lunch" in printed_output
        assert "Coffee" in printed_output


def test_expense_notification_is_sent(client, app):
    """Test that notification is sent when expense is created."""
    # Arrange
    from models import Group

    with app.app_context():
        payer = User(email="payer@example.com")
        participant = User(email="participant@example.com")
        diana = User(email="diana@example.com")
        eve = User(email="eve@example.com")
        db.session.add_all([payer, participant, diana, eve])
        db.session.flush()

        # Create a group with members
        group = Group(name="Test Group", created_by_id=diana.id)
        group.members.extend([diana, eve])
        db.session.add(group)
        db.session.commit()

        payer_id = payer.id
        group_id = group.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    # Act
    with patch("services.notification_service.print") as mock_print:
        client.post(
            "/expense-splitter",
            data={
                "description": "Test expense",
                "amount": "100.00",
                "payer": "diana@example.com",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["diana@example.com", "eve@example.com"],
            },
        )

        # Assert
        assert mock_print.called
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "diana@example.com" in printed_output or "eve@example.com" in printed_output


def test_payer_does_not_receive_notification(client, app):
    """Test that the payer does not receive a notification when they create an expense."""
    # Arrange
    from models import Group

    with app.app_context():
        payer = User(email="payer@example.com")
        participant1 = User(email="participant1@example.com")
        participant2 = User(email="participant2@example.com")
        db.session.add_all([payer, participant1, participant2])
        db.session.flush()

        # Create a group with all members including payer
        group = Group(name="Test Group", created_by_id=payer.id)
        group.members.extend([payer, participant1, participant2])
        db.session.add(group)
        db.session.commit()

        payer_id = payer.id
        group_id = group.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id
        sess["user_email"] = "payer@example.com"

    # Act
    with patch("routes.expenses.notify_expense_participants") as mock_notify:
        response = client.post(
            "/expense-splitter",
            data={
                "description": "Team lunch",
                "amount": "90.00",
                "payer": "payer@example.com",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": [
                    "payer@example.com",
                    "participant1@example.com",
                    "participant2@example.com",
                ],
            },
            follow_redirects=False,
        )

        # Assert
        assert response.status_code == 302  # Redirect after success
        assert mock_notify.called

        # Get the actual list of emails that were sent notifications
        call_args = mock_notify.call_args
        notified_emails = call_args[0][1]  # Second argument to notify_expense_participants

        # Verify payer is NOT in the notification list
        assert "payer@example.com" not in notified_emails
        # Verify other participants ARE in the notification list
        assert "participant1@example.com" in notified_emails
        assert "participant2@example.com" in notified_emails
        # Verify exactly 2 participants were notified (not 3)
        assert len(notified_emails) == 2
