"""Tests for payment reminder routes."""

import pytest
from unittest.mock import patch

from extensions import db
from models import Expense, User


def test_send_reminder_requires_authentication(client, app):
    """Test reminder endpoint requires login."""
    # Try to send reminder without authentication
    response = client.post("/send-reminder/1")

    # Should redirect to login
    assert response.status_code == 302
    assert "/auth/login" in response.location or "login" in response.location.lower()


def test_send_reminder_validates_debtor_exists(client, app):
    """Test handles non-existent debtor."""
    with app.app_context():
        # Create creditor user
        creditor = User(email="creditor@example.com", display_name="Creditor")
        db.session.add(creditor)
        db.session.commit()
        creditor_id = creditor.id

    # Log in as creditor
    with client.session_transaction() as session:
        session["user_id"] = creditor_id
        session["user_email"] = "creditor@example.com"

    # Try to send reminder to non-existent debtor
    response = client.post("/send-reminder/99999", follow_redirects=True)

    # Should show error message
    assert response.status_code == 200
    # Check that error message appears in the response
    assert b"Error" in response.data or b"not found" in response.data


def test_send_reminder_validates_creditor_is_owed_money(client, app):
    """Test can't send reminder if not owed money."""
    with app.app_context():
        # Create users
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        db.session.add_all([user1, user2])
        db.session.commit()
        user1_id = user1.id
        user2_id = user2.id

    # Log in as user1
    with client.session_transaction() as session:
        session["user_id"] = user1_id
        session["user_email"] = "user1@example.com"

    # Try to send reminder to user2 (but user1 doesn't owe user2)
    response = client.post(f"/send-reminder/{user2_id}", follow_redirects=True)

    # Should show warning/error
    assert response.status_code == 200
    # Check that warning message appears in the response
    assert b"not owed" in response.data or b"You are not owed" in response.data


def test_send_reminder_success_sends_notification(client, app):
    """Test successful reminder sends notification."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.flush()

        # Create expense where Alice paid, Bob owes
        expense = Expense(
            description="Dinner",
            amount=100.00,
            payer=creditor.display_name,
            participants=f"{creditor.email}, {debtor.email}",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        creditor_id = creditor.id
        debtor_id = debtor.id

    # Log in as Alice (creditor)
    with client.session_transaction() as session:
        session["user_id"] = creditor_id
        session["user_email"] = "alice@example.com"

    # Mock notification service
    with patch("routes.expenses.notify_debtor_reminder") as mock_notify:
        # Send reminder to Bob
        response = client.post(f"/send-reminder/{debtor_id}", follow_redirects=True)

        # Should succeed
        assert response.status_code == 200

        # Verify notification was sent
        assert mock_notify.called
        assert mock_notify.call_count == 1

        # Check notification parameters
        call_args = mock_notify.call_args
        assert call_args[1]["creditor"].email == "alice@example.com"
        assert call_args[1]["debtor"].email == "bob@example.com"
        assert call_args[1]["amount"] == 50.00  # Bob's share of $100 split equally


def test_send_reminder_success_flash_message(client, app):
    """Test successful reminder shows flash message."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.flush()

        # Create expense where Alice paid, Bob owes
        expense = Expense(
            description="Lunch",
            amount=50.00,
            payer=creditor.display_name,
            participants=f"{creditor.email}, {debtor.email}",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        creditor_id = creditor.id
        debtor_id = debtor.id

    # Log in as Alice
    with client.session_transaction() as session:
        session["user_id"] = creditor_id
        session["user_email"] = "alice@example.com"

    # Mock notification service
    with patch("routes.expenses.notify_debtor_reminder"):
        # Send reminder
        response = client.post(f"/send-reminder/{debtor_id}", follow_redirects=True)

        # Should show success message
        assert response.status_code == 200
        # Check that success message appears in the response
        assert b"reminder sent" in response.data or b"Payment reminder sent" in response.data


def test_send_reminder_redirects_to_balance_summary(client, app):
    """Test send reminder redirects back to balance summary."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.flush()

        # Create expense
        expense = Expense(
            description="Coffee",
            amount=20.00,
            payer=creditor.display_name,
            participants=f"{creditor.email}, {debtor.email}",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        creditor_id = creditor.id
        debtor_id = debtor.id

    # Log in
    with client.session_transaction() as session:
        session["user_id"] = creditor_id
        session["user_email"] = "alice@example.com"

    # Mock notification
    with patch("routes.expenses.notify_debtor_reminder"):
        # Send reminder without following redirects
        response = client.post(f"/send-reminder/{debtor_id}")

        # Should redirect to balance summary
        assert response.status_code == 302
        assert "balance-summary" in response.location


def test_send_reminder_handles_multiple_expenses(client, app):
    """Test reminder includes total from multiple expenses."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.flush()

        # Create multiple expenses
        expense1 = Expense(
            description="Dinner",
            amount=60.00,
            payer=creditor.display_name,
            participants=f"{creditor.email}, {debtor.email}",
            split_type="equal",
        )
        expense2 = Expense(
            description="Movie",
            amount=40.00,
            payer=creditor.display_name,
            participants=f"{creditor.email}, {debtor.email}",
            split_type="equal",
        )
        db.session.add_all([expense1, expense2])
        db.session.commit()

        creditor_id = creditor.id
        debtor_id = debtor.id

    # Log in
    with client.session_transaction() as session:
        session["user_id"] = creditor_id
        session["user_email"] = "alice@example.com"

    # Mock notification
    with patch("routes.expenses.notify_debtor_reminder") as mock_notify:
        # Send reminder
        response = client.post(f"/send-reminder/{debtor_id}", follow_redirects=True)

        # Should succeed
        assert response.status_code == 200

        # Verify total amount is sum of both expenses
        assert mock_notify.called
        call_args = mock_notify.call_args
        total_amount = call_args[1]["amount"]
        assert total_amount == 50.00  # Bob owes $30 + $20 = $50

        # Verify breakdown includes both expenses
        breakdown = call_args[1]["breakdown"]
        assert len(breakdown) == 2


def test_send_reminder_handles_notification_exception(client, app):
    """Test send reminder handles notification service exceptions."""
    with app.app_context():
        # Create users
        creditor = User(email="alice@example.com", display_name="Alice")
        debtor = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([creditor, debtor])
        db.session.commit()

        # Create expense where Bob owes Alice
        expense = Expense(
            description="Lunch",
            amount=50.00,
            payer=creditor.display_name,
            participants=f"{creditor.email}, {debtor.email}",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        creditor_id = creditor.id
        debtor_id = debtor.id

    # Log in as Alice
    with client.session_transaction() as session:
        session["user_id"] = creditor_id
        session["user_email"] = "alice@example.com"

    # Mock notification service to raise exception
    with patch("routes.expenses.notify_debtor_reminder") as mock_notify:
        mock_notify.side_effect = Exception("Email service unavailable")
        
        # Send reminder
        response = client.post(f"/send-reminder/{debtor_id}", follow_redirects=True)

        # Should show error message
        assert response.status_code == 200
        # Check that error message appears in the response
        assert b"Error" in response.data or b"Email service unavailable" in response.data


def test_balance_summary_with_group_filter(client, app):
    """Test balance summary can filter by group_id."""
    with app.app_context():
        # Create users
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        db.session.add_all([user1, user2])
        db.session.commit()
        user1_id = user1.id

        # Create group with required created_by_id
        from models import Group
        group = Group(name="Test Group", created_by_id=user1_id)
        db.session.add(group)
        db.session.commit()
        group_id = group.id

    # Log in
    with client.session_transaction() as session:
        session["user_id"] = user1_id
        session["user_email"] = "user1@example.com"

    # Access balance summary with group filter
    response = client.get(f"/balance-summary?group_id={group_id}")

    # Should succeed
    assert response.status_code == 200
    assert b"Balance Summary" in response.data
