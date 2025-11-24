"""Tests for settlement validation and recording feature."""

from extensions import db
from models import Expense, Settlement, User
from services.settlement_service import SettlementService


def test_get_debt_between_users_simple_case(app):
    """Test calculating debt between two users with one expense."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Alice paid $30 for both Alice and Bob (Bob owes Alice $15)
        expense = Expense(
            description="Lunch",
            amount=30.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Bob owes Alice $15
        debt = SettlementService.get_debt_between_users("bob@example.com", "alice@example.com")
        assert debt == 15.0

        # Alice doesn't owe Bob anything
        reverse_debt = SettlementService.get_debt_between_users(
            "alice@example.com", "bob@example.com"
        )
        assert reverse_debt == 0.0


def test_get_debt_between_users_no_debt(app):
    """Test calculating debt when no expenses exist."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        debt = SettlementService.get_debt_between_users("bob@example.com", "alice@example.com")
        assert debt == 0.0


def test_validate_settlement_valid_full_payment(app):
    """Test validation passes for exact debt amount."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Create expense where Bob owes Alice $20
        expense = Expense(
            description="Dinner",
            amount=40.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Validate settling the exact amount
        validation = SettlementService.validate_settlement(bob.id, alice.id, 20.0)
        assert validation["valid"] is True
        assert validation["error"] is None
        assert validation["current_debt"] == 20.0


def test_validate_settlement_valid_partial_payment(app):
    """Test validation passes for partial payment."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $50
        expense = Expense(
            description="Hotel",
            amount=100.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Validate partial payment of $30
        validation = SettlementService.validate_settlement(bob.id, alice.id, 30.0)
        assert validation["valid"] is True
        assert validation["error"] is None
        assert validation["current_debt"] == 50.0


def test_validate_settlement_exceeds_debt(app):
    """Test validation fails when amount exceeds debt."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $20
        expense = Expense(
            description="Lunch",
            amount=40.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Try to settle $30 when only owe $20
        validation = SettlementService.validate_settlement(bob.id, alice.id, 30.0)
        assert validation["valid"] is False
        assert "exceeds the owed amount" in validation["error"]
        assert validation["current_debt"] == 20.0


def test_validate_settlement_no_debt_exists(app):
    """Test validation fails when no debt exists."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        # Try to settle when no debt exists
        validation = SettlementService.validate_settlement(bob.id, alice.id, 10.0)
        assert validation["valid"] is False
        assert "No debt exists" in validation["error"]


def test_validate_settlement_negative_amount(app):
    """Test validation fails for negative amount."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        validation = SettlementService.validate_settlement(bob.id, alice.id, -10.0)
        assert validation["valid"] is False
        assert "must be greater than" in validation["error"]


def test_validate_settlement_zero_amount(app):
    """Test validation fails for zero amount."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        validation = SettlementService.validate_settlement(bob.id, alice.id, 0.0)
        assert validation["valid"] is False
        assert "must be greater than" in validation["error"]


def test_validate_settlement_same_user(app):
    """Test validation fails when payer and recipient are the same."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        db.session.add(alice)
        db.session.commit()

        validation = SettlementService.validate_settlement(alice.id, alice.id, 10.0)
        assert validation["valid"] is False
        assert "Cannot settle a payment with yourself" in validation["error"]


def test_validate_settlement_invalid_users(app):
    """Test validation fails for non-existent users."""
    with app.app_context():
        validation = SettlementService.validate_settlement(9999, 9998, 10.0)
        assert validation["valid"] is False
        assert "Invalid payer or recipient" in validation["error"]


def test_create_settlement_success(app):
    """Test creating a valid settlement."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $30
        expense = Expense(
            description="Groceries",
            amount=60.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Create settlement
        success, settlement, error = SettlementService.create_settlement(
            bob.id, alice.id, 30.0, "Payment for groceries"
        )

        assert success is True
        assert settlement is not None
        assert error is None
        assert settlement.amount == 30.0
        assert settlement.payer_id == bob.id
        assert settlement.recipient_id == alice.id
        assert settlement.note == "Payment for groceries"

        # Verify settlement was saved
        saved = db.session.get(Settlement, settlement.id)
        assert saved is not None


def test_create_settlement_failure_exceeds_debt(app):
    """Test creating settlement fails when exceeding debt."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $15
        expense = Expense(
            description="Coffee",
            amount=30.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Try to settle more than owed
        success, settlement, error = SettlementService.create_settlement(bob.id, alice.id, 20.0)

        assert success is False
        assert settlement is None
        assert "exceeds the owed amount" in error

        # Verify no settlement was created
        assert Settlement.query.count() == 0


def test_balance_updates_after_settlement(app):
    """Test that balances update correctly after settlement."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $50
        expense = Expense(
            description="Taxi",
            amount=100.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Check initial debt
        initial_debt = SettlementService.get_debt_between_users(
            "bob@example.com", "alice@example.com"
        )
        assert initial_debt == 50.0

        # Bob pays Alice $30
        success, settlement, error = SettlementService.create_settlement(bob.id, alice.id, 30.0)
        assert success is True

        # Check remaining debt
        remaining_debt = SettlementService.get_debt_between_users(
            "bob@example.com", "alice@example.com"
        )
        assert remaining_debt == 20.0  # 50 - 30 = 20


def test_balance_zero_after_full_settlement(app):
    """Test that balance becomes zero after full settlement."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $25
        expense = Expense(
            description="Movie",
            amount=50.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # Bob pays Alice the full $25
        success, settlement, error = SettlementService.create_settlement(bob.id, alice.id, 25.0)
        assert success is True

        # Check debt is now zero
        remaining_debt = SettlementService.get_debt_between_users(
            "bob@example.com", "alice@example.com"
        )
        assert remaining_debt == 0.0


def test_multiple_partial_settlements(app):
    """Test multiple partial payments reduce debt correctly."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $100
        expense = Expense(
            description="Vacation",
            amount=200.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        # First payment: $40
        success1, _, _ = SettlementService.create_settlement(
            bob.id, alice.id, 40.0, "First payment"
        )
        assert success1 is True
        debt_after_first = SettlementService.get_debt_between_users(
            "bob@example.com", "alice@example.com"
        )
        assert debt_after_first == 60.0

        # Second payment: $30
        success2, _, _ = SettlementService.create_settlement(
            bob.id, alice.id, 30.0, "Second payment"
        )
        assert success2 is True
        debt_after_second = SettlementService.get_debt_between_users(
            "bob@example.com", "alice@example.com"
        )
        assert debt_after_second == 30.0

        # Final payment: $30
        success3, _, _ = SettlementService.create_settlement(
            bob.id, alice.id, 30.0, "Final payment"
        )
        assert success3 is True
        debt_after_third = SettlementService.get_debt_between_users(
            "bob@example.com", "alice@example.com"
        )
        assert debt_after_third == 0.0

        # Verify all settlements were created
        assert Settlement.query.count() == 3


def test_settlement_with_custom_split(app):
    """Test settlement validation works with custom split expenses."""
    import json

    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        charlie = User(email="charlie@example.com", display_name="Charlie")
        db.session.add_all([alice, bob, charlie])
        db.session.flush()

        # Alice paid $120, Bob owes $50, Charlie owes $70
        expense = Expense(
            description="Hotel Room",
            amount=120.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com, charlie@example.com",
            split_type="custom",
            split_details=json.dumps(
                {
                    "alice@example.com": 0.0,  # Alice paid, owes nothing
                    "bob@example.com": 50.0,
                    "charlie@example.com": 70.0,
                }
            ),
        )
        db.session.add(expense)
        db.session.commit()

        # Bob should owe Alice $50
        bob_debt = SettlementService.get_debt_between_users("bob@example.com", "alice@example.com")
        assert bob_debt == 50.0

        # Charlie should owe Alice $70
        charlie_debt = SettlementService.get_debt_between_users(
            "charlie@example.com", "alice@example.com"
        )
        assert charlie_debt == 70.0

        # Bob pays his share
        success, _, _ = SettlementService.create_settlement(bob.id, alice.id, 50.0)
        assert success is True

        # Verify Bob's debt is cleared
        bob_remaining = SettlementService.get_debt_between_users(
            "bob@example.com", "alice@example.com"
        )
        assert bob_remaining == 0.0

        # Verify Charlie's debt unchanged
        charlie_remaining = SettlementService.get_debt_between_users(
            "charlie@example.com", "alice@example.com"
        )
        assert charlie_remaining == 70.0
