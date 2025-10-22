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
        db.session.add_all([payer, participant1, participant2])

        # Create a group with members
        group = Group(name="Dinner Group", members="John, Alice, Bob")
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
                "payer": "John",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["John", "Alice", "Bob"],
            },
            follow_redirects=False,
        )

        # Assert
        assert response.status_code == 302  # Redirect after success

        # Check notifications were printed
        assert mock_print.called

        # Verify notification content
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "John" in printed_output or "Alice" in printed_output or "Bob" in printed_output
        assert "New expense added" in printed_output
        assert "Dinner at restaurant" in printed_output
        assert "$150.00" in printed_output


def test_expense_without_participants_no_notification(client, app):
    """Test that expense without participants doesn't send notifications."""
    # Arrange
    from models import Group

    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)

        # Create a group (required for expense creation)
        group = Group(name="Solo Group", members="Alice")
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
        db.session.add_all([payer, participant])

        # Create a group with members
        group = Group(name="Movie Group", members="Bob, Charlie")
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
                "payer": "Bob",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["Bob", "Charlie"],
            },
        )

        # Assert
        assert mock_print.called

        # Verify all details are in notification
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Movie tickets" in printed_output
        assert "$30.00" in printed_output
        assert "Bob" in printed_output or "Charlie" in printed_output


def test_multiple_expenses_send_separate_notifications(client, app):
    """Test that multiple expenses send separate notifications."""
    # Arrange
    from models import Group

    with app.app_context():
        payer = User(email="payer@example.com")
        participant = User(email="participant@example.com")
        db.session.add_all([payer, participant])

        # Create a group with members
        group = Group(name="Lunch Group", members="Charlie, Dave")
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
                "payer": "Charlie",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["Charlie", "Dave"],
            },
        )

        # Create second expense
        client.post(
            "/expense-splitter",
            data={
                "description": "Coffee",
                "amount": "10.00",
                "payer": "Charlie",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["Charlie", "Dave"],
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
        db.session.add_all([payer, participant])

        # Create a group with members
        group = Group(name="Test Group", members="Diana, Eve")
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
                "payer": "Diana",
                "group_id": str(group_id),
                "split_type": "equal",
                "participants": ["Diana", "Eve"],
            },
        )

        # Assert
        assert mock_print.called
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Diana" in printed_output or "Eve" in printed_output
