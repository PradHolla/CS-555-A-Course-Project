"""Integration tests for settlement routes with validation."""

from extensions import db
from models import Expense, Settlement, User


def test_settlement_create_valid_full_payment(client, app):
    """Test creating a settlement for the full debt amount."""
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

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    # Record payment
    response = client.post(
        "/settlements",
        data={"payer_id": bob_id, "recipient_id": alice_id, "amount": "20.00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "Payment recorded!" in response_text or "recorded" in response_text.lower()

    # Verify settlement was created
    with app.app_context():
        settlement = Settlement.query.first()
        assert settlement is not None
        assert settlement.amount == 20.0
        assert settlement.payer_id == bob_id
        assert settlement.recipient_id == alice_id


def test_settlement_create_valid_partial_payment(client, app):
    """Test creating a partial settlement."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $50
        expense = Expense(
            description="Dinner",
            amount=100.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    # Record partial payment of $30
    response = client.post(
        "/settlements",
        data={
            "payer_id": bob_id,
            "recipient_id": alice_id,
            "amount": "30.00",
            "note": "Partial payment",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "Partial payment recorded!" in response_text or "recorded" in response_text.lower()

    with app.app_context():
        settlement = Settlement.query.first()
        assert settlement is not None
        assert settlement.amount == 30.0
        assert settlement.note == "Partial payment"


def test_settlement_create_exceeds_debt_rejected(client, app):
    """Test that settlement exceeding debt is rejected."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $20
        expense = Expense(
            description="Coffee",
            amount=40.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    # Try to pay $30 when only owe $20
    response = client.post(
        "/settlements",
        data={"payer_id": bob_id, "recipient_id": alice_id, "amount": "30.00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "exceeds the owed amount" in response_text or "exceeds" in response_text.lower()

    # Verify no settlement was created
    with app.app_context():
        assert Settlement.query.count() == 0


def test_settlement_create_no_debt_rejected(client, app):
    """Test that settlement with no existing debt is rejected."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    # Try to settle when no debt exists
    response = client.post(
        "/settlements",
        data={"payer_id": bob_id, "recipient_id": alice_id, "amount": "10.00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "No debt exists" in response_text or "no debt" in response_text.lower()

    with app.app_context():
        assert Settlement.query.count() == 0


def test_settlement_create_zero_amount_rejected(client, app):
    """Test that zero amount settlement is rejected."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        expense = Expense(
            description="Test",
            amount=40.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    response = client.post(
        "/settlements",
        data={"payer_id": bob_id, "recipient_id": alice_id, "amount": "0.00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "must be greater than" in response_text or "greater than 0" in response_text.lower()

    with app.app_context():
        assert Settlement.query.count() == 0


def test_settlement_create_negative_amount_rejected(client, app):
    """Test that negative amount settlement is rejected."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        expense = Expense(
            description="Test",
            amount=40.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    response = client.post(
        "/settlements",
        data={"payer_id": bob_id, "recipient_id": alice_id, "amount": "-10.00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "must be greater than" in response_text or "greater than 0" in response_text.lower()

    with app.app_context():
        assert Settlement.query.count() == 0


def test_settlement_create_invalid_data(client, app):
    """Test that invalid form data is handled gracefully."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    # Send invalid data
    response = client.post(
        "/settlements",
        data={"payer_id": "invalid", "recipient_id": "invalid", "amount": "not_a_number"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "Invalid settlement data" in response_text or "invalid" in response_text.lower()

    with app.app_context():
        assert Settlement.query.count() == 0


def test_settlement_shows_remaining_debt_message(client, app):
    """Test that partial payment shows remaining debt in message."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $100
        expense = Expense(
            description="Hotel",
            amount=200.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    # Pay $60 out of $100
    response = client.post(
        "/settlements",
        data={"payer_id": bob_id, "recipient_id": alice_id, "amount": "60.00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    # Should show remaining debt message
    response_text = response.data.decode("utf-8")
    assert "Remaining debt" in response_text and "$40.00" in response_text


def test_settlement_shows_settled_message(client, app):
    """Test that full payment shows 'all settled up' message."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $25
        expense = Expense(
            description="Uber",
            amount=50.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    # Pay full amount
    response = client.post(
        "/settlements",
        data={"payer_id": bob_id, "recipient_id": alice_id, "amount": "25.00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "All settled up!" in response_text


def test_settlement_requires_login(client, app):
    """Test that settlement creation requires authentication."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    # Try to create settlement without login
    response = client.post(
        "/settlements",
        data={"payer_id": bob_id, "recipient_id": alice_id, "amount": "10.00"},
    )

    # Should redirect to login
    assert response.status_code == 302
    assert b"/login" in response.data or response.location.endswith("/login")


def test_settlement_with_note(client, app):
    """Test creating settlement with an optional note."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        expense = Expense(
            description="Groceries",
            amount=60.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    response = client.post(
        "/settlements",
        data={
            "payer_id": bob_id,
            "recipient_id": alice_id,
            "amount": "30.00",
            "note": "Thanks for covering groceries!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        settlement = Settlement.query.first()
        assert settlement is not None
        assert settlement.note == "Thanks for covering groceries!"
