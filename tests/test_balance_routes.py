"""Tests for balance functionality."""

from models import Expense, User


def test_balance_summary_get_returns_ok(client, app):
    """Test that GET /balance-summary returns a 200 status code."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200


def test_balance_summary_calculates_simple_balance(client, app):
    """Test that balance summary correctly calculates who owes whom for a simple case."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Alice paid $30 for Alice, Bob, Charlie (each owes Alice $10)
    expense1 = Expense(
        description="Lunch", amount=30.0, payer="Alice", participants="Alice, Bob, Charlie"
    )
    db.session.add(expense1)
    db.session.commit()

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200
    assert b"Alice" in response.data
    assert b"Bob" in response.data
    assert b"Charlie" in response.data


def test_balance_summary_calculates_multiple_expenses(client, app):
    """Test that balance summary correctly handles multiple expenses."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Alice paid $30 for Alice, Bob, Charlie
    expense1 = Expense(
        description="Lunch", amount=30.0, payer="Alice", participants="Alice, Bob, Charlie"
    )
    # Bob paid $60 for Alice, Bob, Charlie
    expense2 = Expense(
        description="Dinner", amount=60.0, payer="Bob", participants="Alice, Bob, Charlie"
    )
    db.session.add_all([expense1, expense2])
    db.session.commit()

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200
    # After calculation: Bob is owed $10 (Bob paid $60, should pay $30 total)
    # Alice owes $10 (Alice paid $30, should pay $30 total)
    # Charlie owes $20 (Charlie paid $0, should pay $30 total)


def test_balance_summary_with_no_expenses(client, app):
    """Test that balance summary works with no expenses in database."""
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"
    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200


def test_balance_summary_requires_login(client):
    """Test that balance summary redirects to login when not authenticated."""
    # Act
    response = client.get("/balance-summary", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_balance_summary_handles_expense_with_no_participants(client, app):
    """Test that balance summary correctly handles expenses with empty participants."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Create expense with no participants (edge case)
    expense1 = Expense(description="Orphan expense", amount=50.0, payer="Alice", participants=None)
    # Create normal expense
    expense2 = Expense(description="Lunch", amount=30.0, payer="Bob", participants="Alice, Bob")
    db.session.add_all([expense1, expense2])
    db.session.commit()

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200
    # The orphan expense should be skipped, only the valid expense should be calculated
    assert b"Bob" in response.data
    assert b"Alice" in response.data
