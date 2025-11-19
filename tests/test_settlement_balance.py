"""Tests for settlement impact on balance calculations."""

import pytest
from extensions import db
from models import Expense, Settlement, User
from services.expense_service import ExpenseService


def test_settlements_reduce_balance_correctly(app):
    """Test that recording a payment updates the balance correctly."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        # Alice pays $100 for both
        expense = Expense(
            amount=100.0,
            description="Dinner",
            payer="alice@example.com",
            split_details='{"alice@example.com": 50.0, "bob@example.com": 50.0}',
        )
        db.session.add(expense)
        db.session.commit()

        # Calculate initial balance (Bob owes Alice $50)
        expenses = [expense]
        balance_data = ExpenseService.calculate_balances(expenses)
        
        assert balance_data["balances"]["alice@example.com"] == 50.0  # Alice is owed $50
        assert balance_data["balances"]["bob@example.com"] == -50.0  # Bob owes $50
        assert len(balance_data["transactions"]) == 1
        assert balance_data["transactions"][0]["from"] == "bob@example.com"
        assert balance_data["transactions"][0]["to"] == "alice@example.com"
        assert balance_data["transactions"][0]["amount"] == 50.0

        # Bob records a payment of $30 to Alice
        settlement = Settlement(
            amount=30.0,
            payer_id=bob.id,
            recipient_id=alice.id,
            note="Partial payment"
        )
        db.session.add(settlement)
        db.session.commit()

        # Calculate balance after settlement (Bob now owes only $20)
        settlements = [settlement]
        balance_data_after = ExpenseService.calculate_balances(expenses, settlements)
        
        assert balance_data_after["balances"]["alice@example.com"] == 20.0  # Alice is owed $20
        assert balance_data_after["balances"]["bob@example.com"] == -20.0  # Bob owes $20
        assert len(balance_data_after["transactions"]) == 1
        assert balance_data_after["transactions"][0]["amount"] == 20.0


def test_complete_settlement_zeroes_balance(app):
    """Test that a complete payment zeros out the balance."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        # Alice pays $100 for both
        expense = Expense(
            amount=100.0,
            description="Groceries",
            payer="alice@example.com",
            split_details='{"alice@example.com": 50.0, "bob@example.com": 50.0}',
        )
        db.session.add(expense)
        db.session.commit()

        # Bob records a complete payment of $50 to Alice
        settlement = Settlement(
            amount=50.0,
            payer_id=bob.id,
            recipient_id=alice.id,
            note="Full payment"
        )
        db.session.add(settlement)
        db.session.commit()

        # Calculate balance after settlement
        expenses = [expense]
        settlements = [settlement]
        balance_data = ExpenseService.calculate_balances(expenses, settlements)
        
        # Both balances should be zero (or very close due to floating point)
        assert abs(balance_data["balances"]["alice@example.com"]) < 0.01
        assert abs(balance_data["balances"]["bob@example.com"]) < 0.01
        # No transactions should be needed
        assert len(balance_data["transactions"]) == 0


def test_multiple_settlements_accumulate(app):
    """Test that multiple settlements properly accumulate."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        # Alice pays $100 for both
        expense = Expense(
            amount=100.0,
            description="Concert tickets",
            payer="alice@example.com",
            split_details='{"alice@example.com": 50.0, "bob@example.com": 50.0}',
        )
        db.session.add(expense)
        db.session.commit()

        # Bob makes two partial payments
        settlement1 = Settlement(amount=20.0, payer_id=bob.id, recipient_id=alice.id)
        settlement2 = Settlement(amount=15.0, payer_id=bob.id, recipient_id=alice.id)
        db.session.add_all([settlement1, settlement2])
        db.session.commit()

        # Calculate balance after both settlements
        expenses = [expense]
        settlements = [settlement1, settlement2]
        balance_data = ExpenseService.calculate_balances(expenses, settlements)
        
        # Bob paid $35 total, so he owes $15 more
        assert balance_data["balances"]["alice@example.com"] == 15.0
        assert balance_data["balances"]["bob@example.com"] == -15.0
        assert balance_data["transactions"][0]["amount"] == 15.0


def test_settlement_without_expenses_doesnt_crash(app):
    """Test that settlements work even with no expenses."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        # Create a settlement without any expenses (edge case)
        settlement = Settlement(amount=10.0, payer_id=bob.id, recipient_id=alice.id)
        db.session.add(settlement)
        db.session.commit()

        # This should not crash
        expenses = []
        settlements = [settlement]
        balance_data = ExpenseService.calculate_balances(expenses, settlements)
        
        # Should return empty data since no expenses
        assert balance_data["balances"] == {}
        assert balance_data["transactions"] == []
