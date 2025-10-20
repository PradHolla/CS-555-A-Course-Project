from models import Expense, User, Group

# === Authentication Route Tests ===


def test_request_otp_creates_user_and_sends_email(client, app):
    """Test that POST /auth/request-otp creates user and generates OTP."""
    # Arrange
    email_data = {"email": "test@example.com"}

    # Act
    response = client.post("/auth/request-otp", data=email_data, follow_redirects=False)

    # Assert
    assert response.status_code == 200
    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None
    assert user.otp is not None
    assert len(user.otp) == 6
    assert user.otp.isdigit()
    assert user.otp_expiry is not None


def test_request_otp_for_existing_user_updates_otp(client, app):
    """Test that requesting OTP for existing user updates their OTP."""
    # Arrange
    from extensions import db

    user = User(email="existing@example.com", otp="111111")
    db.session.add(user)
    db.session.commit()
    old_otp = user.otp

    email_data = {"email": "existing@example.com"}

    # Act
    response = client.post("/auth/request-otp", data=email_data)

    # Assert
    assert response.status_code == 200
    user = User.query.filter_by(email="existing@example.com").first()
    assert user.otp != old_otp  # OTP should be regenerated
    assert len(user.otp) == 6


def test_request_otp_requires_email(client):
    """Test that POST /auth/request-otp requires email field."""
    # Act
    response = client.post("/auth/request-otp", data={})

    # Assert
    assert response.status_code == 400


def test_verify_otp_with_valid_code_logs_in_user(client, app):
    """Test that POST /auth/verify-otp with valid OTP logs in user."""
    # Arrange
    from datetime import datetime, timedelta, timezone

    from extensions import db

    user = User(email="test@example.com")
    user.otp = "123456"
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.add(user)
    db.session.commit()

    verify_data = {"email": "test@example.com", "otp": "123456"}

    # Act
    response = client.post("/auth/verify-otp", data=verify_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect to dashboard
    assert response.location == "/groups/"
    # Check session
    with client.session_transaction() as sess:
        assert sess.get("user_id") == user.id
        assert sess.get("user_email") == "test@example.com"


def test_verify_otp_with_invalid_code_rejects(client, app):
    """Test that POST /auth/verify-otp with invalid OTP rejects."""
    # Arrange
    from datetime import datetime, timedelta, timezone

    from extensions import db

    user = User(email="test@example.com")
    user.otp = "123456"
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.add(user)
    db.session.commit()

    verify_data = {"email": "test@example.com", "otp": "999999"}  # Wrong OTP

    # Act
    response = client.post("/auth/verify-otp", data=verify_data)

    # Assert
    assert response.status_code == 400


def test_verify_otp_with_expired_code_rejects(client, app):
    """Test that POST /auth/verify-otp with expired OTP rejects."""
    # Arrange
    from datetime import datetime, timedelta, timezone

    from extensions import db

    user = User(email="test@example.com")
    user.otp = "123456"
    user.otp_expiry = datetime.now(timezone.utc) - timedelta(minutes=1)  # Expired
    db.session.add(user)
    db.session.commit()

    verify_data = {"email": "test@example.com", "otp": "123456"}

    # Act
    response = client.post("/auth/verify-otp", data=verify_data)

    # Assert
    assert response.status_code == 400


def test_logout_clears_session(client, app):
    """Test that GET /auth/logout clears the session."""
    # Arrange - simulate logged in user
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_email"] = "test@example.com"

    # Act
    response = client.get("/auth/logout", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert response.location == "/"
    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "user_email" not in sess


# === Protected Route Tests ===


def test_expense_splitter_redirects_if_not_logged_in(client):
    """Test that /expense-splitter redirects to login if user not authenticated."""
    # Act
    response = client.get("/expense-splitter", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_expense_splitter_accessible_when_logged_in(client):
    """Test that /expense-splitter is accessible when user is logged in."""
    # Arrange - simulate logged in user
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_email"] = "test@example.com"

    # Act
    response = client.get("/expense-splitter")

    # Assert
    assert response.status_code == 200


# === Expense Route Tests ===


def test_expense_splitter_get_returns_ok(client):
    """Test that GET /expense-splitter returns a 200 status code."""
    # Arrange
    # Create a logged-in user session
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/expense-splitter")

    # Assert
    assert response.status_code == 200


def test_expense_splitter_post_creates_expense(client):
    """Test that POST /expense-splitter creates a new expense in the database."""
    # Arrange
    # Create a logged-in user session
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "36.75",
        "payer": "Alex",
        "participants": "Alex, Sam, Jo",
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    stored = Expense.query.filter_by(description="Dinner").first()
    assert stored is not None
    assert stored.amount == 36.75
    assert stored.payer == "Alex"
    assert stored.participants == "Alex, Sam, Jo"


def test_expense_splitter_rejects_invalid_amount(client):
    """Test that POST /expense-splitter rejects non-numeric amount values."""
    # Arrange
    invalid_data = {
        "description": "Snacks",
        "amount": "abc",
        "payer": "Riley",
        "participants": "Riley, Pat",
    }

    # Act
    response = client.post("/expense-splitter", data=invalid_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert Expense.query.count() == 0

def test_groups_list_returns_ok(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    response = client.get('/groups/')
    assert response.status_code == 200

def test_groups_create_group_with_members(client):
    """Test that POST /groups creates a new group in the database."""
    # Arrange
    # Create a logged-in user session
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    group_data = {
        "name": "My Agile group",
        "members": "Anikait, Sairithik, Pradhyumna",
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    stored = Group.query.filter_by(name="My Agile group").first()
    assert stored is not None
    assert stored.members == "Anikait, Sairithik, Pradhyumna"

# === Balance Summary Tests ===


def test_balance_summary_get_returns_ok(client):
    """Test that GET /balance-summary returns a 200 status code."""
    # Arrange
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/balance-summary")

    # Assert
    assert response.status_code == 200


def test_balance_summary_calculates_simple_balance(client, app):
    """Test that balance summary correctly calculates who owes whom for a simple case."""
    # Arrange
    from extensions import db

    with client.session_transaction() as session:
        session["user_id"] = 1
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

    with client.session_transaction() as session:
        session["user_id"] = 1
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


def test_balance_summary_with_no_expenses(client):
    """Test that balance summary works with no expenses in database."""
    with client.session_transaction() as session:
        session["user_id"] = 1
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

    with client.session_transaction() as session:
        session["user_id"] = 1
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
