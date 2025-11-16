"""Unit tests for ReminderService."""

import json
from datetime import datetime, timedelta, timezone

import pytest

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
