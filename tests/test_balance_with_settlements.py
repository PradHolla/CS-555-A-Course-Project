"""Tests for balance summary page with settlements."""


from extensions import db
from models import Expense, Settlement, User


def test_balance_summary_reflects_partial_settlement(client, app):
    """Test that balance summary shows reduced debt after partial settlement."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $100
        expense = Expense(
            description="Dinner",
            amount=200.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    # Check balance before settlement
    with client.session_transaction() as session:
        session["user_id"] = bob_id
        session["user_email"] = "bob@example.com"

    response = client.get("/balance-summary")
    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "$100.00" in response_text  # Should show $100 debt

    # Make a partial payment of $60
    with app.app_context():
        settlement = Settlement(
            payer_id=bob_id, recipient_id=alice_id, amount=60.0, note="Partial payment"
        )
        db.session.add(settlement)
        db.session.commit()

    # Check balance after settlement - should show $40 remaining
    response = client.get("/balance-summary")
    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "$40.00" in response_text  # Should show remaining $40 debt


def test_balance_summary_hides_fully_settled_debt(client, app):
    """Test that balance summary hides transactions that are fully settled."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $50
        expense = Expense(
            description="Groceries",
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

    # Check balance before settlement
    response = client.get("/balance-summary")
    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    assert "$50.00" in response_text
    # Should have settlement buttons
    assert "Settle Full Amount" in response_text or "settle" in response_text.lower()

    # Make full payment
    with app.app_context():
        settlement = Settlement(
            payer_id=bob_id, recipient_id=alice_id, amount=50.0, note="Full payment"
        )
        db.session.add(settlement)
        db.session.commit()

    # Check balance after full settlement - debt should be gone
    response = client.get("/balance-summary")
    assert response.status_code == 200
    response_text = response.data.decode("utf-8")

    # After full settlement, the "All Settled! 🎉" message should appear
    assert "All Settled" in response_text and "🎉" in response_text
    # And no transactions should be listed (no settlement buttons/forms)
    assert "Settle Full Amount" not in response_text


def test_balance_cards_reflect_settlements(client, app):
    """Test that balance cards at the top show correct amounts after settlements."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $100
        expense = Expense(
            description="Dinner",
            amount=200.0,
            payer="alice@example.com",
            participants="alice@example.com, bob@example.com",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

        alice_id = alice.id
        bob_id = bob.id

    # Login as Bob
    with client.session_transaction() as session:
        session["user_id"] = bob_id

    # Check initial balance cards
    response = client.get("/balance-summary")
    assert response.status_code == 200
    response_text = response.data.decode("utf-8")

    # Alice should be owed $100
    assert "Alice" in response_text
    assert "$100.00" in response_text
    assert "Is owed" in response_text

    # Bob should owe $100
    assert "Bob" in response_text
    assert "Owes" in response_text

    # Bob pays $60
    with app.app_context():
        response = client.post(
            "/settlements",
            data={
                "payer_id": bob_id,
                "recipient_id": alice_id,
                "amount": "60.00",
                "note": "Partial payment",
            },
            follow_redirects=True,
        )

    # Check balance cards after partial payment
    response = client.get("/balance-summary")
    assert response.status_code == 200
    response_text = response.data.decode("utf-8")

    # Alice should now be owed $40 (not $100)
    assert "$40.00" in response_text

    # Bob should now owe $40 (not $100)
    # The original $100 should not appear anymore
    assert response_text.count("$100.00") == 0

    # Bob pays remaining $40
    with app.app_context():
        response = client.post(
            "/settlements",
            data={
                "payer_id": bob_id,
                "recipient_id": alice_id,
                "amount": "40.00",
                "note": "Final payment",
            },
            follow_redirects=True,
        )

    # Check balance cards after full settlement
    response = client.get("/balance-summary")
    assert response.status_code == 200
    response_text = response.data.decode("utf-8")

    # Both balances should be zero or very close to zero
    # Should show "All Settled" message
    assert "All Settled" in response_text


def test_balance_summary_with_multiple_partial_settlements(client, app):
    """Test balance summary correctly shows debt after multiple partial payments."""
    with app.app_context():
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()

        # Bob owes Alice $150
        expense = Expense(
            description="Trip",
            amount=300.0,
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

    # Initial balance check
    response = client.get("/balance-summary")
    assert response.status_code == 200
    assert b"$150.00" in response.data

    # First partial payment of $50
    with app.app_context():
        settlement1 = Settlement(payer_id=bob_id, recipient_id=alice_id, amount=50.0)
        db.session.add(settlement1)
        db.session.commit()

    response = client.get("/balance-summary")
    assert response.status_code == 200
    assert b"$100.00" in response.data  # $150 - $50 = $100

    # Second partial payment of $30
    with app.app_context():
        settlement2 = Settlement(payer_id=bob_id, recipient_id=alice_id, amount=30.0)
        db.session.add(settlement2)
        db.session.commit()

    response = client.get("/balance-summary")
    assert response.status_code == 200
    assert b"$70.00" in response.data  # $100 - $30 = $70

    # Third partial payment of $70 (full settlement)
    with app.app_context():
        settlement3 = Settlement(payer_id=bob_id, recipient_id=alice_id, amount=70.0)
        db.session.add(settlement3)
        db.session.commit()

    response = client.get("/balance-summary")
    assert response.status_code == 200
    response_text = response.data.decode("utf-8")
    # After full settlement, no transaction should be shown
    assert "$70.00" not in response_text or "Settle" not in response_text
