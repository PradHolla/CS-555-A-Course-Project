"""Test dashboard service with settlements - user perspective."""

from extensions import db
from models import Expense, Settlement, User
from services.dashboard_service import DashboardService


def test_dashboard_user_owes_money_and_pays(app):
    """
    Test dashboard when user owes money from someone else's expense and makes payments.
    This matches the scenario shown in the screenshot.
    """
    with app.app_context():
        # Create Alice who paid for an expense
        alice = User(email="alice@example.com", display_name="Alice")
        # Create Bob who owes money
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Alice paid $44 for lunch, split equally between Alice and Bob
        # So Bob owes Alice $22
        expense = Expense(
            description="Lunch",
            amount=44.00,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.flush()

        # Bob makes a payment of $22 to Alice to settle his debt
        settlement = Settlement(amount=22.00, payer_id=bob.id, recipient_id=alice.id)
        db.session.add(settlement)
        db.session.commit()

        # Get Bob's summary
        bob_summary = DashboardService.get_user_summary(bob.id)

        # Bob's perspective:
        # - Total Expenses Added: $0 (Bob didn't pay for any expenses)
        # - Total Payments Made: $22 (Bob paid Alice)
        # - Outstanding Balance: $0 (Bob paid off his $22 debt, so now owes nothing)
        assert bob_summary["total_expenses"] == 0.0
        assert bob_summary["total_payments"] == 22.00
        assert bob_summary["outstanding_balance"] == 0.0  # Should be zero, not -$22!
        assert bob_summary["has_data"] is True


def test_dashboard_user_owes_money_partial_payment(app):
    """Test dashboard when user makes partial payment on debt."""
    with app.app_context():
        # Create Alice who paid for an expense
        alice = User(email="alice@example.com", display_name="Alice")
        # Create Bob who owes money
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Alice paid $100 for dinner, split equally
        # Bob owes Alice $50
        expense = Expense(
            description="Dinner",
            amount=100.00,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.flush()

        # Bob makes a partial payment of $30
        settlement = Settlement(amount=30.00, payer_id=bob.id, recipient_id=alice.id)
        db.session.add(settlement)
        db.session.commit()

        # Get Bob's summary
        bob_summary = DashboardService.get_user_summary(bob.id)

        # Bob's perspective:
        # - Total Expenses Added: $0 
        # - Total Payments Made: $30
        # - Outstanding Balance: -$20 (Bob still owes $20 to Alice)
        assert bob_summary["total_expenses"] == 0.0
        assert bob_summary["total_payments"] == 30.00
        assert bob_summary["outstanding_balance"] == -20.0
        assert bob_summary["has_data"] is True


def test_dashboard_user_is_owed_and_receives_payment(app):
    """Test dashboard when user is owed money and receives a payment."""
    with app.app_context():
        # Create Alice who paid for an expense
        alice = User(email="alice@example.com", display_name="Alice")
        # Create Bob who owes money
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Alice paid $100 for dinner, split equally
        # Bob owes Alice $50
        expense = Expense(
            description="Dinner",
            amount=100.00,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.flush()

        # Bob pays Alice $30
        settlement = Settlement(amount=30.00, payer_id=bob.id, recipient_id=alice.id)
        db.session.add(settlement)
        db.session.commit()

        # Get Alice's summary
        alice_summary = DashboardService.get_user_summary(alice.id)

        # Alice's perspective:
        # - Total Expenses Added: $100 (Alice paid for dinner)
        # - Total Payments Made: $0 (Alice hasn't paid anyone)
        # - Outstanding Balance: +$20 (Alice is still owed $20 by Bob)
        assert alice_summary["total_expenses"] == 100.00
        assert alice_summary["total_payments"] == 0.0
        assert alice_summary["outstanding_balance"] == 20.0
        assert alice_summary["has_data"] is True
