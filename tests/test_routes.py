from models import Expense, Group, User

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


def test_expense_splitter_post_creates_expense(client, app):
    """Test that POST /expense-splitter creates a new expense in the database."""
    # Arrange
    from extensions import db

    # Create a group first
    group = Group(name="Test Group", members="Alex, Sam, Jo")
    db.session.add(group)
    db.session.commit()

    # Create a logged-in user session
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "36.75",
        "payer": "Alex",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["Alex", "Sam", "Jo"]
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    stored = Expense.query.filter_by(description="Dinner").first()
    assert stored is not None
    assert stored.amount == 36.75
    assert stored.payer == "Alex"
    assert stored.group_id == group.id
    assert stored.split_type == "equal"


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


# === New Group-Based Expense Tests ===


def test_expense_splitter_requires_group_selection(client, app):
    """Test that expense creation requires group selection."""
    # Arrange
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "Alice",
        "group_id": "",  # Empty group
        "split_type": "equal",
        "participants": ["Alice", "Bob"]
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect back to form
    assert Expense.query.count() == 0


def test_expense_splitter_rejects_zero_amount(client, app):
    """Test that expense creation rejects zero amount."""
    # Arrange
    from extensions import db

    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "0.00",  # Zero amount
        "payer": "Alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["Alice", "Bob"]
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect back to form
    assert Expense.query.count() == 0


def test_expense_splitter_rejects_negative_amount(client, app):
    """Test that expense creation rejects negative amount."""
    # Arrange
    from extensions import db

    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "-10.00",  # Negative amount
        "payer": "Alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["Alice", "Bob"]
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect back to form
    assert Expense.query.count() == 0


def test_expense_splitter_validates_payer_in_group(client, app):
    """Test that payer must be a member of the selected group."""
    # Arrange
    from extensions import db

    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "Charlie",  # Not in group
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["Alice", "Bob"]
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect back to form
    assert Expense.query.count() == 0


def test_expense_splitter_validates_participants_in_group(client, app):
    """Test that participants must be members of the selected group."""
    # Arrange
    from extensions import db

    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "Alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["Alice", "Charlie"]  # Charlie not in group
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect back to form
    assert Expense.query.count() == 0


def test_expense_splitter_creates_equal_split_expense(client, app):
    """Test creating expense with equal split."""
    # Arrange
    from extensions import db

    group = Group(name="Test Group", members="Alice, Bob, Charlie")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "60.00",
        "payer": "Alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["Alice", "Bob", "Charlie"]
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect after success
    stored = Expense.query.first()
    assert stored is not None
    assert stored.description == "Dinner"
    assert stored.amount == 60.0
    assert stored.payer == "Alice"
    assert stored.group_id == group.id
    assert stored.split_type == "equal"

    # Check split details
    import json
    split_details = json.loads(stored.split_details)
    assert split_details["Alice"] == 20.0
    assert split_details["Bob"] == 20.0
    assert split_details["Charlie"] == 20.0


def test_expense_splitter_creates_custom_split_expense(client, app):
    """Test creating expense with custom split."""
    # Arrange
    from extensions import db

    group = Group(name="Test Group", members="Alice, Bob, Charlie")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "60.00",
        "payer": "Alice",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_Alice": "30.00",
        "custom_amount_Bob": "20.00",
        "custom_amount_Charlie": "10.00"
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect after success
    stored = Expense.query.first()
    assert stored is not None
    assert stored.split_type == "custom"

    # Check split details
    import json
    split_details = json.loads(stored.split_details)
    assert split_details["Alice"] == 30.0
    assert split_details["Bob"] == 20.0
    assert split_details["Charlie"] == 10.0


def test_expense_splitter_rejects_custom_split_mismatch(client, app):
    """Test that custom split amounts must equal total amount."""
    # Arrange
    from extensions import db

    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "Alice",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_Alice": "30.00",
        "custom_amount_Bob": "20.00"  # Total = 50, should be valid
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Should succeed
    assert Expense.query.count() == 1


def test_expense_splitter_rejects_custom_split_total_mismatch(client, app):
    """Test that custom split with wrong total is rejected."""
    # Arrange
    from extensions import db

    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "Alice",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_Alice": "30.00",
        "custom_amount_Bob": "30.00"  # Total = 60, should be rejected
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect back to form
    assert Expense.query.count() == 0


def test_expense_splitter_filters_by_group(client, app):
    """Test that expenses can be filtered by group."""
    # Arrange
    from extensions import db

    group1 = Group(name="Group 1", members="Alice, Bob")
    group2 = Group(name="Group 2", members="Charlie, Dave")
    db.session.add_all([group1, group2])
    db.session.commit()

    # Create expenses for both groups
    expense1 = Expense(
        description="Lunch 1", amount=20.0, payer="Alice",
        group_id=group1.id, split_type="equal", split_details='{"Alice": 10.0, "Bob": 10.0}'
    )
    expense2 = Expense(
        description="Lunch 2", amount=40.0, payer="Charlie",
        group_id=group2.id, split_type="equal", split_details='{"Charlie": 20.0, "Dave": 20.0}'
    )
    db.session.add_all([expense1, expense2])
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    # Act
    response = client.get(f"/expense-splitter?group_id={group1.id}")

    # Assert
    assert response.status_code == 200
    assert b"Lunch 1" in response.data
    assert b"Lunch 2" not in response.data


def test_balance_summary_filters_by_group(client, app):
    """Test that balance summary can be filtered by group."""
    # Arrange
    from extensions import db

    group1 = Group(name="Group 1", members="Alice, Bob")
    group2 = Group(name="Group 2", members="Charlie, Dave")
    db.session.add_all([group1, group2])
    db.session.commit()

    # Create expenses for both groups
    expense1 = Expense(
        description="Lunch 1", amount=20.0, payer="Alice",
        group_id=group1.id, split_type="equal", split_details='{"Alice": 10.0, "Bob": 10.0}'
    )
    expense2 = Expense(
        description="Lunch 2", amount=40.0, payer="Charlie",
        group_id=group2.id, split_type="equal", split_details='{"Charlie": 20.0, "Dave": 20.0}'
    )
    db.session.add_all([expense1, expense2])
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    # Act
    response = client.get(f"/balance-summary?group_id={group1.id}")

    # Assert
    assert response.status_code == 200
    # Should only show balances for Group 1 members
    assert b"Alice" in response.data
    assert b"Bob" in response.data
    assert b"Charlie" not in response.data
    assert b"Dave" not in response.data

def test_missing_description(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "",  # Missing
        "amount": "100",
        "payer": "alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice"]
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_missing_group(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice",
        "group_id": "",  # Missing
        "split_type": "equal",
        "participants": ["alice"]
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_missing_payer(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "",  # Missing
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice"]
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_invalid_amount_nonpositive(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "0",  # Or negative
        "payer": "alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice"]
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_invalid_amount_type(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "abc",  # Not a number
        "payer": "alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice"]
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_group_not_found(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "50",
        "payer": "alice",
        "group_id": "99999",  # Nonexistent group
        "split_type": "equal",
        "participants": ["alice"]
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_payer_not_in_group(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "50",
        "payer": "notamember",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice"]
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_no_participants_selected(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": []  # Empty list
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_participant_not_in_group(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice", "notamember"]
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_invalid_custom_amount(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    # Assume group members: alice, bob
    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice": "abc",  # Invalid
        "custom_amount_bob": "60"
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_no_custom_split_details(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    # No amounts for any member
    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice": "",
        "custom_amount_bob": ""
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0

def test_invalid_custom_split_sum(client, app):
    from extensions import db

    group = Group(name="Fixture Group", members="alice, bob")
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "90",
        "payer": "alice",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice": "30",
        "custom_amount_bob": "40"
        # Adds up to 70, not 90
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


# === Service Layer Coverage Tests (targeted lines) ===


def test_expense_service_parse_split_details_json_error(app):
    """Covers json.loads exception path (lines 133-134)."""
    from extensions import db
    from services.expense_service import ExpenseService

    expense = Expense(
        description="Test",
        amount=10.0,
        payer="Alice",
        split_details="invalid json {",  # triggers JSONDecodeError
    )
    db.session.add(expense)
    db.session.commit()

    result = ExpenseService._parse_split_details(expense)
    assert result == {}


def test_expense_service_validate_custom_split_empty_details(app):
    """Covers empty split_details early return (line 158)."""
    from services.expense_service import ExpenseService

    is_valid, error_msg = ExpenseService.validate_custom_split({}, 50.0)
    assert not is_valid
    assert error_msg == "No participants specified"


def test_expense_service_calculate_equal_split_empty_participants(app):
    """Covers empty participants early return (line 181)."""
    from services.expense_service import ExpenseService

    result = ExpenseService.calculate_equal_split([], 50.0)
    assert result == {}
