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

        # Create expenses where user is payer
        expense1 = Expense(
            description="Lunch",
            amount=50.00,
            payer=user.display_name,
            split_type="equal",
        )
        expense2 = Expense(
            description="Dinner",
            amount=75.50,
            payer=user.display_name,
            split_type="equal",
        )
        db.session.add_all([expense1, expense2])

        # Create settlements where user is payer
        other_user = User(email="other@example.com", display_name="Other User")
        db.session.add(other_user)
        db.session.flush()

        settlement1 = Settlement(amount=30.00, payer_id=user.id, recipient_id=other_user.id)
        settlement2 = Settlement(amount=20.25, payer_id=user.id, recipient_id=other_user.id)
        db.session.add_all([settlement1, settlement2])
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # Verify totals
        assert summary["total_expenses"] == 125.50
        assert summary["total_payments"] == 50.25
        assert summary["outstanding_balance"] == 75.25
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
    """Test get_user_summary with only expenses."""
    with app.app_context():
        # Create test user
        user = User(email="testuser@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create expenses only
        expense = Expense(
            description="Groceries",
            amount=100.00,
            payer=user.display_name,
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # Verify outstanding_balance equals total_expenses
        assert summary["total_expenses"] == 100.00
        assert summary["total_payments"] == 0.0
        assert summary["outstanding_balance"] == 100.00
        assert summary["has_data"] is True


def test_get_user_summary_only_payments(app):
    """Test get_user_summary with only payments."""
    with app.app_context():
        # Create test user
        user = User(email="testuser@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create other user and settlement
        other_user = User(email="recipient@example.com", display_name="Recipient")
        db.session.add(other_user)
        db.session.flush()

        settlement = Settlement(amount=50.00, payer_id=user.id, recipient_id=other_user.id)
        db.session.add(settlement)
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # Verify negative outstanding_balance
        assert summary["total_expenses"] == 0.0
        assert summary["total_payments"] == 50.00
        assert summary["outstanding_balance"] == -50.00
        assert summary["has_data"] is True


def test_get_user_summary_decimal_precision(app):
    """Test get_user_summary rounds to 2 decimal places."""
    with app.app_context():
        # Create test user
        user = User(email="testuser@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create expenses with decimal amounts
        expense1 = Expense(
            description="Coffee",
            amount=3.333,
            payer=user.display_name,
            split_type="equal",
        )
        expense2 = Expense(
            description="Snack",
            amount=2.777,
            payer=user.display_name,
            split_type="equal",
        )
        db.session.add_all([expense1, expense2])

        # Create settlement with decimal amount
        other_user = User(email="other@example.com", display_name="Other")
        db.session.add(other_user)
        db.session.flush()

        settlement = Settlement(amount=1.555, payer_id=user.id, recipient_id=other_user.id)
        db.session.add(settlement)
        db.session.commit()

        # Get summary
        summary = DashboardService.get_user_summary(user.id)

        # Verify 2 decimal place rounding
        assert summary["total_expenses"] == 6.11  # 3.333 + 2.777 = 6.11
        assert summary["total_payments"] == 1.55  # 1.555 rounded to 1.55 (banker's rounding)
        assert summary["outstanding_balance"] == 4.56  # 6.11 - 1.55 = 4.56
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



def test_get_user_summary_with_invalid_split_details(app):
    """Test get_user_summary handles invalid JSON in split_details."""
    with app.app_context():
        user = User(email="user@example.com", display_name="User")
        db.session.add(user)
        db.session.commit()

        # Create expense with invalid JSON in split_details
        expense = Expense(
            description="Bad JSON",
            amount=100.00,
            payer="user@example.com",
            split_type="equal",
            split_details="{invalid json}"
        )
        db.session.add(expense)
        db.session.commit()

        # Should handle gracefully and assume user is owed full amount
        summary = DashboardService.get_user_summary(user.id)

        assert summary["total_expenses"] == 100.00
        assert summary["outstanding_balance"] == 100.00


def test_get_user_summary_as_participant_with_invalid_json(app):
    """Test get_user_summary when user is participant with invalid JSON."""
    with app.app_context():
        user = User(email="user@example.com", display_name="User")
        payer = User(email="payer@example.com", display_name="Payer")
        db.session.add_all([user, payer])
        db.session.commit()

        # Create expense where user is not payer, with invalid JSON
        expense = Expense(
            description="Bad JSON",
            amount=100.00,
            payer="payer@example.com",
            split_type="equal",
            split_details="{invalid}"
        )
        db.session.add(expense)
        db.session.commit()

        # Should handle gracefully
        summary = DashboardService.get_user_summary(user.id)

        # User didn't pay and JSON is invalid, so balance should be 0
        assert summary["outstanding_balance"] == 0.00


def test_get_user_summary_with_no_split_details(app):
    """Test get_user_summary when expense has no split_details."""
    with app.app_context():
        user = User(email="user@example.com", display_name="User")
        db.session.add(user)
        db.session.commit()

        # Create expense without split_details
        expense = Expense(
            description="No split",
            amount=50.00,
            payer="user@example.com",
            split_type="equal",
            split_details=None
        )
        db.session.add(expense)
        db.session.commit()

        summary = DashboardService.get_user_summary(user.id)

        # User paid full amount with no split, so they're owed full amount
        assert summary["total_expenses"] == 50.00
        assert summary["outstanding_balance"] == 50.00


def test_get_user_summary_complex_scenario(app):
    """Test get_user_summary with complex multi-user scenario."""
    with app.app_context():
        user = User(email="user@example.com", display_name="User")
        other1 = User(email="other1@example.com", display_name="Other1")
        other2 = User(email="other2@example.com", display_name="Other2")
        db.session.add_all([user, other1, other2])
        db.session.commit()

        # User paid an expense
        expense1 = Expense(
            description="User paid",
            amount=90.00,
            payer="user@example.com",
            split_type="equal",
            split_details='{"user@example.com": 30.0, "other1@example.com": 30.0, "other2@example.com": 30.0}'
        )
        
        # Other1 paid an expense
        expense2 = Expense(
            description="Other1 paid",
            amount=60.00,
            payer="other1@example.com",
            split_type="equal",
            split_details='{"user@example.com": 20.0, "other1@example.com": 20.0, "other2@example.com": 20.0}'
        )
        
        db.session.add_all([expense1, expense2])
        db.session.commit()

        # User made a settlement
        settlement = Settlement(amount=15.00, payer_id=user.id, recipient_id=other1.id)
        db.session.add(settlement)
        db.session.commit()

        summary = DashboardService.get_user_summary(user.id)

        # User paid 90, owes 30 from their share = +60
        # User owes 20 from other1's expense = -20
        # User paid settlement of 15 = -15
        # Net: 60 - 20 - 15 = 25
        assert summary["total_expenses"] == 90.00
        assert summary["total_payments"] == 15.00
        assert summary["outstanding_balance"] == 25.00
