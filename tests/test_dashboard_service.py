"""Unit tests for dashboard service."""

from extensions import db
from models import Expense, Settlement, User
from services.dashboard_service import DashboardService


def test_get_user_summary_with_data(app):
    """Test get_user_summary with expenses and settlements."""
    with app.app_context():
        # Create test user
        user = User(email="testuser@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create other user
        other_user = User(email="other@example.com", display_name="Other User")
        db.session.add(other_user)
        db.session.flush()

        # User paid $50 for lunch, split equally - other owes user $25
        expense1 = Expense(
            description="Lunch",
            amount=50.00,
            payer=user.display_name,
            participants=f"{user.email}, {other_user.email}",
            split_type="equal",
        )
        # User paid $75.50 for dinner, split equally - other owes user $37.75
        expense2 = Expense(
            description="Dinner",
            amount=75.50,
            payer=user.display_name,
            participants=f"{user.email}, {other_user.email}",
            split_type="equal",
        )
        db.session.add_all([expense1, expense2])
        db.session.flush()

        # Other user pays user back $50.25 total
        settlement1 = Settlement(amount=30.00, payer_id=other_user.id, recipient_id=user.id)
        settlement2 = Settlement(amount=20.25, payer_id=other_user.id, recipient_id=user.id)
        db.session.add_all([settlement1, settlement2])
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # User's outstanding balance:
        # - Was owed: $25 + $37.75 = $62.75
        # - Received payments: $50.25
        # - Still owed: $62.75 - $50.25 = $12.50
        assert summary["total_expenses"] == 125.50
        assert summary["total_payments"] == 0.0  # User didn't make any payments
        assert summary["outstanding_balance"] == 12.50
        assert summary["has_data"] is True


def test_get_user_summary_no_data(app):
    """Test get_user_summary with no financial data."""
    with app.app_context():
        # Create test user
        user = User(email="testuser@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Get summary with no data
        summary = DashboardService.get_user_summary(user.id)

        # Verify empty summary
        assert summary["total_expenses"] == 0.0
        assert summary["total_payments"] == 0.0
        assert summary["outstanding_balance"] == 0.0
        assert summary["has_data"] is False


def test_get_user_summary_only_expenses(app):
    """Test get_user_summary with only expenses (user paid, hasn't been paid back yet)."""
    with app.app_context():
        # Create test user
        user = User(email="testuser@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create another user to participate
        other_user = User(email="other@example.com", display_name="Other")
        db.session.add(other_user)
        db.session.flush()

        # User paid $100 for groceries, split with other_user
        # So other_user owes user $50
        expense = Expense(
            description="Groceries",
            amount=100.00,
            payer=user.display_name,
            participants=f"{user.email}, {other_user.email}",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # User is owed $50 (paid $100, their share is $50, so they're owed $50)
        assert summary["total_expenses"] == 100.00
        assert summary["total_payments"] == 0.0
        assert summary["outstanding_balance"] == 50.00  # User is owed $50
        assert summary["has_data"] is True


def test_get_user_summary_only_payments(app):
    """Test get_user_summary when user only makes payments (settling debts from someone else's expense)."""
    with app.app_context():
        # Create test user (Bob)
        user = User(email="testuser@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create other user (Alice) who paid for an expense
        other_user = User(email="recipient@example.com", display_name="Recipient")
        db.session.add(other_user)
        db.session.flush()

        # Alice paid $100, split with Bob - so Bob owes $50
        expense = Expense(
            description="Shared expense",
            amount=100.00,
            payer=other_user.email,
            participants=f"{other_user.email}, {user.email}",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.flush()

        # Bob pays Alice $50 to settle
        settlement = Settlement(amount=50.00, payer_id=user.id, recipient_id=other_user.id)
        db.session.add(settlement)
        db.session.commit()

        # Get summary for Bob
        summary = DashboardService.get_user_summary(user.id)

        # Bob's outstanding balance should be 0 (he owed $50, paid $50)
        assert summary["total_expenses"] == 0.0  # Bob didn't pay for the expense
        assert summary["total_payments"] == 50.00  # Bob paid $50
        assert summary["outstanding_balance"] == 0.0  # Debt is settled
        assert summary["has_data"] is True


def test_get_user_summary_decimal_precision(app):
    """Test get_user_summary rounds to 2 decimal places."""
    with app.app_context():
        # Create test user
        user = User(email="testuser@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create other user
        other_user = User(email="other@example.com", display_name="Other")
        db.session.add(other_user)
        db.session.flush()

        # User paid expenses, split equally
        expense1 = Expense(
            description="Coffee",
            amount=3.333,
            payer=user.display_name,
            participants=f"{user.email}, {other_user.email}",
            split_type="equal",
        )
        expense2 = Expense(
            description="Snack",
            amount=2.777,
            payer=user.display_name,
            participants=f"{user.email}, {other_user.email}",
            split_type="equal",
        )
        db.session.add_all([expense1, expense2])
        db.session.flush()

        # Other user pays back partial amount
        settlement = Settlement(amount=1.555, payer_id=other_user.id, recipient_id=user.id)
        db.session.add(settlement)
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # User's outstanding balance:
        # - Was owed: (3.333 + 2.777) / 2 = 3.055
        # - Received payment: 1.555
        # - Still owed: 3.055 - 1.555 = 1.50
        assert summary["total_expenses"] == 6.11  # 3.333 + 2.777 = 6.11
        assert summary["total_payments"] == 0.0  # User didn't make payments
        assert summary["outstanding_balance"] == 1.50  # User is still owed $1.50
        assert summary["has_data"] is True


def test_get_user_summary_missing_user(app):
    """Test get_user_summary with non-existent user."""
    with app.app_context():
        # Get summary for non-existent user
        summary = DashboardService.get_user_summary(99999)

        # Verify empty summary
        assert summary["total_expenses"] == 0.0
        assert summary["total_payments"] == 0.0
        assert summary["outstanding_balance"] == 0.0
        assert summary["has_data"] is False


def test_get_user_summary_uses_display_name(app):
    """Test that service uses display_name as payer identifier."""
    with app.app_context():
        user = User(email="user@example.com", display_name="Display Name")
        db.session.add(user)
        db.session.commit()

        # Create expense with display_name as payer
        expense = Expense(
            description="Test",
            amount=50.00,
            payer="Display Name",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # Verify expense is included
        assert summary["total_expenses"] == 50.00
        assert summary["has_data"] is True


def test_get_user_summary_uses_email_fallback(app):
    """Test that service uses email when display_name is not set."""
    with app.app_context():
        user = User(email="user@example.com", display_name=None)
        db.session.add(user)
        db.session.commit()

        # Create expense with email as payer
        expense = Expense(
            description="Test",
            amount=50.00,
            payer="user@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # Verify expense is included
        assert summary["total_expenses"] == 50.00
        assert summary["has_data"] is True
