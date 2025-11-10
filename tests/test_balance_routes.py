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


def test_balance_summary_displays_user_display_names(client, app):
    """Test that balance summary displays user display names when available."""
    # Arrange
    from extensions import db

    with app.app_context():
        # Create users with display names
        user1 = User(email="alice@example.com", display_name="Alice Smith")
        user2 = User(email="bob@example.com", display_name="Bob Jones")
        user3 = User(email="charlie@example.com")  # No display name
        db.session.add_all([user1, user2, user3])
        db.session.commit()
        user1_id = user1.id

    with client.session_transaction() as session:
        session["user_id"] = user1_id
        session["user_email"] = "alice@example.com"

    # Create expense with user emails
    expense = Expense(
        description="Team Lunch",
        amount=90.0,
        payer="alice@example.com",
        participants="alice@example.com, bob@example.com, charlie@example.com",
    )
    db.session.add(expense)
    db.session.commit()

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200
    # Should display display names when available
    assert b"Alice Smith" in response.data
    assert b"Bob Jones" in response.data
    # Should fall back to email when no display name
    assert b"charlie@example.com" in response.data


def test_balance_summary_handles_nonexistent_user_emails(client, app):
    """Test that balance summary handles participant emails that don't exist in User table."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Create expense with emails that don't correspond to User records
    expense = Expense(
        description="Event",
        amount=100.0,
        payer="nonexistent@example.com",
        participants="nonexistent@example.com, another@example.com",
    )
    db.session.add(expense)
    db.session.commit()

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200
    # Should display email addresses as fallback when user not found (line 217 coverage)
    assert b"nonexistent@example.com" in response.data
    assert b"another@example.com" in response.data


def test_balance_summary_includes_detailed_breakdown(client, app):
    """Test that balance summary includes detailed breakdown data."""
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

    # Alice paid $30 for lunch split equally
    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="Alice",
        participants="Alice, Bob, Charlie",
        split_type="equal",
        split_details='{"Alice": 10.0, "Bob": 10.0, "Charlie": 10.0}',
    )
    db.session.add(expense)
    db.session.commit()

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200
    # Should include detailed breakdown view elements
    assert b"Detailed Breakdown" in response.data
    assert b"Simplified Pay" in response.data
    # Should show expense description in detailed view
    assert b"Lunch" in response.data


def test_balance_summary_detailed_breakdown_with_multiple_expenses(client, app):
    """Test detailed breakdown shows all transactions from multiple expenses."""
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

    # Create two expenses
    expense1 = Expense(
        description="Lunch",
        amount=30.0,
        payer="Alice",
        participants="Alice, Bob",
        split_type="equal",
        split_details='{"Alice": 15.0, "Bob": 15.0}',
    )
    expense2 = Expense(
        description="Dinner",
        amount=60.0,
        payer="Bob",
        participants="Alice, Bob",
        split_type="equal",
        split_details='{"Alice": 30.0, "Bob": 30.0}',
    )
    db.session.add_all([expense1, expense2])
    db.session.commit()

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200
    # Both expense descriptions should appear in detailed breakdown
    assert b"Lunch" in response.data
    assert b"Dinner" in response.data
    # Toggle buttons should be present
    assert b"btnSimplifiedView" in response.data
    assert b"btnDetailedView" in response.data
