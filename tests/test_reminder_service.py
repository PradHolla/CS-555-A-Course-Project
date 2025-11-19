"""Unit tests for ReminderService."""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

# Set test environment variables before importing app
os.environ["MAIL_USERNAME"] = "test@example.com"
os.environ["MAIL_PASSWORD"] = "test_password"
os.environ["EMAIL_ENABLED"] = "false"

from app import create_app
from extensions import db
from models import Expense, User
from services.reminder_service import ReminderService


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def create_test_user(email, display_name):
    """Helper to create test user."""
    # Check if user already exists
    user = User.query.filter_by(email=email).first()
    if user:
        # Update existing user
        user.display_name = display_name
        db.session.commit()
        return user
    
    # Create new user
    user = User(email=email, display_name=display_name)
    db.session.add(user)
    db.session.commit()
    return user


def create_test_expense(payer, split_details, description, amount, days_ago=0):
    """Helper to create test expense."""
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    expense = Expense(
        description=description,
        amount=amount,
        payer=payer,
        split_type="equal",
        split_details=json.dumps(split_details),
        created_at=created_at,
        expense_date=created_at.date(),
    )
    db.session.add(expense)
    db.session.commit()
    return expense


class TestCalculateBalanceAge:
    """Tests for calculate_balance_age method."""

    def test_no_expenses(self, app):
        """Test user with no expenses returns 0 days."""
        with app.app_context():
            user = create_test_user("test@example.com", "Test User")
            
            days, oldest_date = ReminderService.calculate_balance_age(user.id)
            
            assert days == 0
            assert oldest_date is None

    def test_old_expense(self, app):
        """Test user with 10 day old expense."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Old expense",
                amount=100.0,
                days_ago=10
            )
            
            days, oldest_date = ReminderService.calculate_balance_age(debtor.id)
            
            assert days == 10
            assert oldest_date is not None

    def test_recent_expense(self, app):
        """Test user with recent expense."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Recent expense",
                amount=100.0,
                days_ago=3
            )
            
            days, oldest_date = ReminderService.calculate_balance_age(debtor.id)
            
            assert days == 3
            assert oldest_date is not None

    def test_user_not_found(self, app):
        """Test with non-existent user."""
        with app.app_context():
            days, oldest_date = ReminderService.calculate_balance_age(99999)
            
            assert days == 0
            assert oldest_date is None


class TestGetUsersNeedingReminders:
    """Tests for get_users_needing_reminders method."""

    def test_no_users(self, app):
        """Test with no users in database."""
        with app.app_context():
            users = ReminderService.get_users_needing_reminders(7)
            
            assert len(users) == 0

    def test_user_with_old_debt(self, app):
        """Test user with debt older than threshold."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Old expense",
                amount=100.0,
                days_ago=10
            )
            
            users = ReminderService.get_users_needing_reminders(7)
            
            assert len(users) == 1
            assert users[0][0].email == "debtor@example.com"
            assert users[0][1] < 0  # Negative balance

    def test_user_with_recent_debt(self, app):
        """Test user with debt newer than threshold."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Recent expense",
                amount=100.0,
                days_ago=3
            )
            
            users = ReminderService.get_users_needing_reminders(7)
            
            assert len(users) == 0

    def test_user_with_positive_balance(self, app):
        """Test user who is owed money (positive balance)."""
        with app.app_context():
            creditor = create_test_user("creditor@example.com", "Creditor")
            debtor = create_test_user("debtor@example.com", "Debtor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Old expense",
                amount=100.0,
                days_ago=10
            )
            
            users = ReminderService.get_users_needing_reminders(7)
            
            # Creditor should not be in list (positive balance)
            user_emails = [u[0].email for u in users]
            assert "creditor@example.com" not in user_emails


class TestGetBalanceBreakdown:
    """Tests for get_balance_breakdown method."""

    def test_single_creditor(self, app):
        """Test breakdown with single creditor."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Expense",
                amount=100.0,
                days_ago=10
            )
            
            breakdown = ReminderService.get_balance_breakdown(debtor.id)
            
            assert len(breakdown) == 1
            assert breakdown[0]["creditor"] == "creditor@example.com"
            assert breakdown[0]["amount"] == 50.0

    def test_multiple_creditors(self, app):
        """Test breakdown with multiple creditors."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor1 = create_test_user("creditor1@example.com", "Creditor1")
            creditor2 = create_test_user("creditor2@example.com", "Creditor2")
            
            create_test_expense(
                payer="creditor1@example.com",
                split_details={"creditor1@example.com": 50.0, "debtor@example.com": 50.0},
                description="Expense 1",
                amount=100.0,
                days_ago=10
            )
            
            create_test_expense(
                payer="creditor2@example.com",
                split_details={"creditor2@example.com": 75.0, "debtor@example.com": 75.0},
                description="Expense 2",
                amount=150.0,
                days_ago=10
            )
            
            breakdown = ReminderService.get_balance_breakdown(debtor.id)
            
            assert len(breakdown) == 2
            # Should be sorted by amount descending
            assert breakdown[0]["amount"] == 75.0
            assert breakdown[1]["amount"] == 50.0

    def test_no_debts(self, app):
        """Test user with no debts."""
        with app.app_context():
            user = create_test_user("user@example.com", "User")
            
            breakdown = ReminderService.get_balance_breakdown(user.id)
            
            assert len(breakdown) == 0


class TestSendReminders:
    """Tests for send_reminders method."""

    def test_reminder_disabled(self, app):
        """Test when reminder system is disabled."""
        with app.app_context():
            app.config["REMINDER_ENABLED"] = False
            
            result = ReminderService.send_reminders(7)
            
            assert result["reminders_sent"] == 0
            assert len(result["errors"]) == 1
            assert "disabled" in result["errors"][0]["error"].lower()

    def test_no_eligible_users(self, app):
        """Test when no users need reminders."""
        with app.app_context():
            result = ReminderService.send_reminders(7)
            
            assert result["reminders_sent"] == 0
            assert len(result["users_notified"]) == 0
            assert len(result["errors"]) == 0


class TestSendRemindersIntegration:
    """Integration tests for send_reminders method."""

    def test_send_reminders_success(self, app):
        """Test successful reminder sending."""
        with app.app_context():
            app.config["REMINDER_ENABLED"] = True
            
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Old expense",
                amount=100.0,
                days_ago=10
            )
            
            result = ReminderService.send_reminders(7)
            
            assert result["reminders_sent"] == 1
            assert "debtor@example.com" in result["users_notified"]
            assert len(result["errors"]) == 0

    def test_send_reminders_multiple_users(self, app):
        """Test sending reminders to multiple users."""
        with app.app_context():
            app.config["REMINDER_ENABLED"] = True
            
            debtor1 = create_test_user("debtor1@example.com", "Debtor1")
            debtor2 = create_test_user("debtor2@example.com", "Debtor2")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor1@example.com": 50.0},
                description="Expense 1",
                amount=100.0,
                days_ago=10
            )
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor2@example.com": 50.0},
                description="Expense 2",
                amount=100.0,
                days_ago=15
            )
            
            result = ReminderService.send_reminders(7)
            
            assert result["reminders_sent"] == 2
            assert "debtor1@example.com" in result["users_notified"]
            assert "debtor2@example.com" in result["users_notified"]

    def test_send_reminders_with_threshold(self, app):
        """Test reminder threshold filtering."""
        with app.app_context():
            app.config["REMINDER_ENABLED"] = True
            
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Recent expense",
                amount=100.0,
                days_ago=5
            )
            
            # Should not send with 7 day threshold
            result = ReminderService.send_reminders(7)
            assert result["reminders_sent"] == 0
            
            # Should send with 3 day threshold
            result = ReminderService.send_reminders(3)
            assert result["reminders_sent"] == 1


class TestBalanceBreakdownEdgeCases:
    """Edge case tests for balance breakdown."""

    def test_breakdown_with_same_creditor_multiple_expenses(self, app):
        """Test breakdown aggregates multiple expenses from same creditor."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 30.0, "debtor@example.com": 30.0},
                description="Expense 1",
                amount=60.0,
                days_ago=10
            )
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 20.0, "debtor@example.com": 20.0},
                description="Expense 2",
                amount=40.0,
                days_ago=10
            )
            
            breakdown = ReminderService.get_balance_breakdown(debtor.id)
            
            assert len(breakdown) == 1
            assert breakdown[0]["creditor"] == "creditor@example.com"
            assert breakdown[0]["amount"] == 50.0  # 30 + 20

    def test_breakdown_sorted_by_amount(self, app):
        """Test breakdown is sorted by amount descending."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor1 = create_test_user("creditor1@example.com", "Creditor1")
            creditor2 = create_test_user("creditor2@example.com", "Creditor2")
            creditor3 = create_test_user("creditor3@example.com", "Creditor3")
            
            create_test_expense(
                payer="creditor1@example.com",
                split_details={"creditor1@example.com": 25.0, "debtor@example.com": 25.0},
                description="Expense 1",
                amount=50.0,
                days_ago=10
            )
            
            create_test_expense(
                payer="creditor2@example.com",
                split_details={"creditor2@example.com": 75.0, "debtor@example.com": 75.0},
                description="Expense 2",
                amount=150.0,
                days_ago=10
            )
            
            create_test_expense(
                payer="creditor3@example.com",
                split_details={"creditor3@example.com": 50.0, "debtor@example.com": 50.0},
                description="Expense 3",
                amount=100.0,
                days_ago=10
            )
            
            breakdown = ReminderService.get_balance_breakdown(debtor.id)
            
            assert len(breakdown) == 3
            assert breakdown[0]["amount"] == 75.0
            assert breakdown[1]["amount"] == 50.0
            assert breakdown[2]["amount"] == 25.0

    def test_breakdown_user_not_found(self, app):
        """Test breakdown with non-existent user."""
        with app.app_context():
            breakdown = ReminderService.get_balance_breakdown(99999)
            
            assert len(breakdown) == 0



class TestErrorHandling:
    """Tests for error handling in reminder service."""

    def test_calculate_balance_age_with_exception(self, app):
        """Test calculate_balance_age handles exceptions gracefully."""
        with app.app_context():
            # Test with invalid user_id type should not crash
            days, oldest_date = ReminderService.calculate_balance_age(None)
            
            # Should return default values
            assert days == 0
            assert oldest_date is None

    def test_get_balance_breakdown_with_invalid_json(self, app):
        """Test balance breakdown handles invalid JSON in split_details."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            # Create expense with invalid JSON
            expense = Expense(
                description="Bad JSON",
                amount=100.0,
                payer="creditor@example.com",
                split_type="equal",
                split_details="{invalid json}",
                created_at=datetime.now(timezone.utc),
                expense_date=datetime.now(timezone.utc).date(),
            )
            db.session.add(expense)
            db.session.commit()
            
            # Should not crash, just skip the invalid expense
            breakdown = ReminderService.get_balance_breakdown(debtor.id)
            
            # Should return empty since JSON is invalid
            assert isinstance(breakdown, list)

    def test_send_reminders_with_no_breakdown(self, app):
        """Test send_reminders skips users with no balance breakdown."""
        with app.app_context():
            app.config["REMINDER_ENABLED"] = True
            
            # Create user with no expenses (no breakdown)
            user = create_test_user("user@example.com", "User")
            
            result = ReminderService.send_reminders(7)
            
            # Should not send any reminders
            assert result["reminders_sent"] == 0
            assert isinstance(result["errors"], list)



class TestNotificationPreferences:
    """Tests for notification preference functionality."""

    def test_user_with_disabled_notifications_not_reminded(self, app):
        """Test that users with disabled notifications are skipped."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            # Disable notifications for debtor
            debtor.daily_reminder_enabled = False
            db.session.commit()
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Old expense",
                amount=100.0,
                days_ago=10
            )
            
            users = ReminderService.get_users_needing_reminders(7)
            
            # Debtor should not be in list
            assert len(users) == 0

    def test_user_with_enabled_notifications_is_reminded(self, app):
        """Test that users with enabled notifications are included."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            # Explicitly enable notifications (default is True)
            debtor.daily_reminder_enabled = True
            db.session.commit()
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Old expense",
                amount=100.0,
                days_ago=10
            )
            
            users = ReminderService.get_users_needing_reminders(7)
            
            # Debtor should be in list
            assert len(users) == 1
            assert users[0][0].email == "debtor@example.com"

    def test_new_user_has_notifications_enabled_by_default(self, app):
        """Test that new users have notifications enabled by default."""
        with app.app_context():
            user = create_test_user("newuser@example.com", "New User")
            
            # Should be enabled by default
            assert user.daily_reminder_enabled is True

    def test_toggle_preference_affects_reminders(self, app):
        """Test that toggling preference immediately affects reminder eligibility."""
        with app.app_context():
            debtor = create_test_user("debtor@example.com", "Debtor")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor@example.com": 50.0},
                description="Old expense",
                amount=100.0,
                days_ago=10
            )
            
            # Initially enabled - should be included
            users = ReminderService.get_users_needing_reminders(7)
            assert len(users) == 1
            
            # Disable notifications
            debtor.daily_reminder_enabled = False
            db.session.commit()
            
            # Should not be included
            users = ReminderService.get_users_needing_reminders(7)
            assert len(users) == 0
            
            # Re-enable notifications
            debtor.daily_reminder_enabled = True
            db.session.commit()
            
            # Should be included again
            users = ReminderService.get_users_needing_reminders(7)
            assert len(users) == 1

    def test_multiple_users_independent_preferences(self, app):
        """Test that multiple users can have independent preferences."""
        with app.app_context():
            debtor1 = create_test_user("debtor1@example.com", "Debtor1")
            debtor2 = create_test_user("debtor2@example.com", "Debtor2")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            # Set different preferences
            debtor1.daily_reminder_enabled = True
            debtor2.daily_reminder_enabled = False
            db.session.commit()
            
            # Create expenses for both
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor1@example.com": 50.0},
                description="Expense 1",
                amount=100.0,
                days_ago=10
            )
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor2@example.com": 50.0},
                description="Expense 2",
                amount=100.0,
                days_ago=10
            )
            
            users = ReminderService.get_users_needing_reminders(7)
            
            # Only debtor1 should be included
            assert len(users) == 1
            assert users[0][0].email == "debtor1@example.com"

    def test_send_reminders_respects_preferences(self, app, monkeypatch):
        """Test that send_reminders respects notification preferences."""
        with app.app_context():
            app.config["REMINDER_ENABLED"] = True
            
            debtor1 = create_test_user("debtor1@example.com", "Debtor1")
            debtor2 = create_test_user("debtor2@example.com", "Debtor2")
            creditor = create_test_user("creditor@example.com", "Creditor")
            
            # Enable for debtor1, disable for debtor2
            debtor1.daily_reminder_enabled = True
            debtor2.daily_reminder_enabled = False
            db.session.commit()
            
            # Create expenses for both
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor1@example.com": 50.0},
                description="Expense 1",
                amount=100.0,
                days_ago=10
            )
            
            create_test_expense(
                payer="creditor@example.com",
                split_details={"creditor@example.com": 50.0, "debtor2@example.com": 50.0},
                description="Expense 2",
                amount=100.0,
                days_ago=10
            )
            
            # Track calls
            calls = []
            def mock_send(user, balance_amount, days_outstanding, balance_breakdown):
                calls.append(user.email)
            
            import services.notification_service
            monkeypatch.setattr(services.notification_service, "send_payment_reminder", mock_send)
            
            result = ReminderService.send_reminders(7)
            
            # Only debtor1 should receive reminder
            assert result["reminders_sent"] == 1
            assert "debtor1@example.com" in result["users_notified"]
            assert "debtor2@example.com" not in result["users_notified"]
            assert len(calls) == 1
