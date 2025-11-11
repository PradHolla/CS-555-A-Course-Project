"""Integration tests for dashboard routes."""

from extensions import db
from models import Expense, Settlement, User


def test_dashboard_requires_authentication(client):
    """Test that /dashboard redirects to login when not authenticated."""
    # Act
    response = client.get("/dashboard", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_dashboard_displays_with_data(client, app):
    """Test that dashboard displays correct amounts with financial data."""
    # Arrange
    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create expenses
        expense1 = Expense(
            description="Lunch",
            amount=50.00,
            payer=user.display_name,
            split_type="equal",
        )
        expense2 = Expense(
            description="Dinner",
            amount=30.00,
            payer=user.display_name,
            split_type="equal",
        )
        db.session.add_all([expense1, expense2])

        # Create other user and settlements
        other_user = User(email="other@example.com", display_name="Other User")
        db.session.add(other_user)
        db.session.flush()

        settlement = Settlement(amount=20.00, payer_id=user.id, recipient_id=other_user.id)
        db.session.add(settlement)
        db.session.commit()

        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/dashboard")

    # Assert
    assert response.status_code == 200
    assert b"Financial Summary" in response.data
    assert b"Test User" in response.data
    # Check for total expenses: $80.00
    assert b"$80.00" in response.data
    # Check for total payments: $20.00
    assert b"$20.00" in response.data
    # Check for outstanding balance: $60.00
    assert b"$60.00" in response.data
    # Should not show "no data to display"
    assert b"no data to display" not in response.data


def test_dashboard_displays_empty_state(client, app):
    """Test that dashboard displays 'no data to display' for new user."""
    # Arrange
    with app.app_context():
        user = User(email="newuser@example.com", display_name="New User")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "newuser@example.com"

    # Act
    response = client.get("/dashboard")

    # Assert
    assert response.status_code == 200
    assert b"Financial Summary" in response.data
    assert b"New User" in response.data
    # Should show "no data to display" three times (one for each card)
    assert response.data.count(b"no data to display") == 3


def test_dashboard_json_response(client, app):
    """Test that dashboard returns JSON when Accept header is application/json."""
    # Arrange
    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create some data
        expense = Expense(
            description="Test",
            amount=100.00,
            payer=user.display_name,
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/dashboard", headers={"Accept": "application/json"})

    # Assert
    assert response.status_code == 200
    assert response.content_type == "application/json"

    json_data = response.get_json()
    assert "total_expenses" in json_data
    assert "total_payments" in json_data
    assert "outstanding_balance" in json_data
    assert "has_data" in json_data
    assert json_data["total_expenses"] == 100.00
    assert json_data["total_payments"] == 0.0
    assert json_data["outstanding_balance"] == 100.00
    assert json_data["has_data"] is True


def test_dashboard_displays_user_email_when_no_display_name(client, app):
    """Test that dashboard shows email when display_name is not set."""
    # Arrange
    with app.app_context():
        user = User(email="user@example.com", display_name=None)
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "user@example.com"

    # Act
    response = client.get("/dashboard")

    # Assert
    assert response.status_code == 200
    assert b"user@example.com" in response.data


def test_dashboard_has_navigation_links(client, app):
    """Test that dashboard includes navigation links."""
    # Arrange
    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/dashboard")

    # Assert
    assert response.status_code == 200
    assert b"View Groups" in response.data
    assert b"Detailed Balances" in response.data
    assert b"/groups" in response.data
    assert b"/balance-summary" in response.data


def test_dashboard_handles_missing_user_session(client, app):
    """Test that dashboard handles case where user_id in session but user not in database."""
    # Arrange - Set session with non-existent user_id
    with client.session_transaction() as session:
        session["user_id"] = 99999
        session["user_email"] = "nonexistent@example.com"

    # Act
    response = client.get("/dashboard", follow_redirects=True)

    # Assert - Should redirect to login and clear session
    assert response.status_code == 200
    assert b"Session expired" in response.data or b"login" in response.data.lower()


def test_dashboard_decimal_formatting(client, app):
    """Test that dashboard formats amounts with 2 decimal places."""
    # Arrange
    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create expense with decimal amount
        expense = Expense(
            description="Test",
            amount=123.456,
            payer=user.display_name,
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/dashboard")

    # Assert
    assert response.status_code == 200
    # Should display as $123.46 (rounded to 2 decimal places)
    assert b"$123.46" in response.data


def test_dashboard_only_shows_user_expenses(client, app):
    """Test that dashboard only includes expenses where user is payer."""
    # Arrange
    with app.app_context():
        user1 = User(email="user1@example.com", display_name="User One")
        user2 = User(email="user2@example.com", display_name="User Two")
        db.session.add_all([user1, user2])
        db.session.flush()

        # Create expense for user1
        expense1 = Expense(
            description="User1 Expense",
            amount=50.00,
            payer=user1.display_name,
            split_type="equal",
        )
        # Create expense for user2
        expense2 = Expense(
            description="User2 Expense",
            amount=100.00,
            payer=user2.display_name,
            split_type="equal",
        )
        db.session.add_all([expense1, expense2])
        db.session.commit()
        user1_id = user1.id

    with client.session_transaction() as session:
        session["user_id"] = user1_id
        session["user_email"] = "user1@example.com"

    # Act
    response = client.get("/dashboard")

    # Assert
    assert response.status_code == 200
    # Should only show user1's expense total
    assert b"$50.00" in response.data
    # Should not show user2's expense amount
    assert b"$100.00" not in response.data


def test_dashboard_only_shows_user_payments(client, app):
    """Test that dashboard only includes settlements where user is payer."""
    # Arrange
    with app.app_context():
        user1 = User(email="user1@example.com", display_name="User One")
        user2 = User(email="user2@example.com", display_name="User Two")
        user3 = User(email="user3@example.com", display_name="User Three")
        db.session.add_all([user1, user2, user3])
        db.session.flush()

        # User1 pays user2
        settlement1 = Settlement(amount=30.00, payer_id=user1.id, recipient_id=user2.id)
        # User2 pays user3 (should not appear in user1's dashboard)
        settlement2 = Settlement(amount=50.00, payer_id=user2.id, recipient_id=user3.id)
        db.session.add_all([settlement1, settlement2])
        db.session.commit()
        user1_id = user1.id

    with client.session_transaction() as session:
        session["user_id"] = user1_id
        session["user_email"] = "user1@example.com"

    # Act
    response = client.get("/dashboard")

    # Assert
    assert response.status_code == 200
    # Should show user1's payment total
    assert b"$30.00" in response.data
    # Should not show user2's payment amount
    assert b"$50.00" not in response.data


def test_dashboard_handles_database_error(client, app, monkeypatch):
    """Test that dashboard handles database errors gracefully."""
    # Arrange
    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Mock DashboardService to raise an exception
    def mock_get_user_summary(user_id):
        raise Exception("Database connection error")

    monkeypatch.setattr("routes.dashboard.DashboardService.get_user_summary", mock_get_user_summary)

    # Act
    response = client.get("/dashboard")

    # Assert
    assert response.status_code == 200
    # Should still render the page with empty data
    assert b"no data to display" in response.data
    assert b"Financial Summary" in response.data


def test_dashboard_json_error_response(client, app, monkeypatch):
    """Test that dashboard returns JSON error when database fails and JSON is requested."""
    # Arrange
    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Mock DashboardService to raise an exception
    def mock_get_user_summary(user_id):
        raise Exception("Database connection error")

    monkeypatch.setattr("routes.dashboard.DashboardService.get_user_summary", mock_get_user_summary)

    # Act
    response = client.get("/dashboard", headers={"Accept": "application/json"})

    # Assert
    assert response.status_code == 500
    assert response.content_type == "application/json"
    json_data = response.get_json()
    assert "error" in json_data
    assert json_data["error"] == "Failed to load dashboard data"
    assert "summary" in json_data
    assert json_data["summary"]["has_data"] is False
