"""Tests for expense functionality."""

from models import Expense, Group, User


def test_expense_splitter_get_returns_ok(client, app):
    """Test that GET /expense-splitter returns a 200 status code."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Create a logged-in user session
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/expense-splitter")

    # Assert
    assert response.status_code == 200


def test_expense_splitter_post_creates_expense(client, app):
    """Test that POST /expense-splitter creates a new expense in the database."""
    # Arrange
    from extensions import db

    # Create users and group
    alex = User(email="alex@example.com")
    sam = User(email="sam@example.com")
    jo = User(email="jo@example.com")
    db.session.add_all([alex, sam, jo])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=alex.id)
    group.members.extend([alex, sam, jo])
    db.session.add(group)
    db.session.commit()

    # Create a logged-in user session
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "36.75",
        "payer": "alex@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alex@example.com", "sam@example.com", "jo@example.com"],
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    stored = Expense.query.filter_by(description="Dinner").first()
    assert stored is not None
    assert stored.amount == 36.75
    assert stored.payer == "alex@example.com"
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


def test_groups_list_returns_ok(client, app):
    """Test that GET /groups/ returns 200 for logged-in user."""
    # Arrange
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.get("/groups/")

    # Assert
    assert response.status_code == 200


def test_groups_create_group_with_members(client, app):
    """Test that POST /groups/create creates a new group with members."""
    # Arrange
    from extensions import db

    # Create the logged-in user (creator)
    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    group_data = {
        "name": "My Agile group",
        "members": "anikait@example.com, sairithik@example.com, pradhyumna@example.com",
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    stored = Group.query.filter_by(name="My Agile group").first()
    assert stored is not None
    assert len(stored.members) == 4  # Creator + 3 members
    assert creator in stored.members
    # Check that member users were created
    assert User.query.filter_by(email="anikait@example.com").first() is not None


def test_groups_create_group_rejects_invalid_member_emails(client, app):
    """Test that POST /groups/create rejects groups with invalid member email formats."""
    # Arrange
    from extensions import db

    # Create the logged-in user (creator)
    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Try creating group with invalid email
    group_data = {
        "name": "Invalid Email Group",
        "members": "valid@example.com, notanemail, another@example.com",
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert - should redirect back to groups page
    assert response.status_code == 302
    assert response.location == "/groups/"
    # Group should not have been created
    assert Group.query.filter_by(name="Invalid Email Group").first() is None


def test_groups_create_group_without_members(client, app):
    """Test that POST /groups/create works without optional members."""
    # Arrange
    from extensions import db

    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    group_data = {
        "name": "Solo Group",
        "members": "",  # No members
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    group = Group.query.filter_by(name="Solo Group").first()
    assert group is not None
    assert len(group.members) == 1  # Just the creator
    assert creator in group.members


def test_groups_create_group_requires_name(client, app):
    """Test that POST /groups/create requires a name."""
    # Arrange
    from extensions import db

    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    group_data = {
        "name": "",  # Empty name
        "members": "alice@example.com",
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert - should redirect back with error
    assert response.status_code == 302
    assert Group.query.count() == 0  # No group created


def test_groups_create_group_skips_duplicate_creator(client, app):
    """Test that creator is not added twice if listed in members."""
    # Arrange
    from extensions import db

    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    group_data = {
        "name": "Test Group",
        "members": "test@example.com, alice@example.com",  # Creator in members list
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    group = Group.query.filter_by(name="Test Group").first()
    assert group is not None
    # Creator should only be in members once, plus alice
    creator_count = sum(1 for m in group.members if m.email == "test@example.com")
    assert creator_count == 1
    assert len(group.members) == 2  # creator + alice


def test_groups_list_requires_login(client):
    """Test that GET /groups/ requires login."""
    # Act - no login session
    response = client.get("/groups/", follow_redirects=False)

    # Assert - should redirect to login
    assert response.status_code == 302


def test_expense_splitter_requires_group_selection(client, app):
    """Test that expense creation requires group selection."""
    # Arrange
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "alice@example.com",
        "group_id": "",  # Empty group
        "split_type": "equal",
        "participants": ["alice@example.com", "bob@example.com"],
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

    alice = User(email="alice@example.com")
    bob = User(email="bob@example.com")
    db.session.add_all([alice, bob])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=alice.id)
    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "0.00",  # Zero amount
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com", "bob@example.com"],
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

    alice = User(email="alice@example.com")
    bob = User(email="bob@example.com")
    db.session.add_all([alice, bob])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=alice.id)
    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "-10.00",  # Negative amount
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com", "bob@example.com"],
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

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Test Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "charlie@example.com",  # Not in group
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com", "bob@example.com"],
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

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Test Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com", "charlie@example.com"],  # Charlie not in group
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

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    charlie = User(email="charlie@example.com")

    db.session.add_all([alice, bob, charlie])

    db.session.commit()

    group = Group(name="Test Group", created_by_id=alice.id)

    group.members.extend([alice, bob, charlie])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "60.00",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com", "bob@example.com", "charlie@example.com"],
    }

    # Act
    response = client.post("/expense-splitter", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect after success
    stored = Expense.query.first()
    assert stored is not None
    assert stored.description == "Dinner"
    assert stored.amount == 60.0
    assert stored.payer == "alice@example.com"
    assert stored.group_id == group.id
    assert stored.split_type == "equal"

    # Check split details
    import json

    split_details = json.loads(stored.split_details)
    assert split_details["alice@example.com"] == 20.0
    assert split_details["bob@example.com"] == 20.0
    assert split_details["charlie@example.com"] == 20.0


def test_expense_splitter_creates_custom_split_expense(client, app):
    """Test creating expense with custom split."""
    # Arrange
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    charlie = User(email="charlie@example.com")

    db.session.add_all([alice, bob, charlie])

    db.session.commit()

    group = Group(name="Test Group", created_by_id=alice.id)

    group.members.extend([alice, bob, charlie])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "60.00",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice@example.com": "30.00",
        "custom_amount_bob@example.com": "20.00",
        "custom_amount_charlie@example.com": "10.00",
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
    assert split_details["alice@example.com"] == 30.0
    assert split_details["bob@example.com"] == 20.0
    assert split_details["charlie@example.com"] == 10.0


def test_expense_splitter_rejects_custom_split_mismatch(client, app):
    """Test that custom split amounts must equal total amount."""
    # Arrange
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Test Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice@example.com": "30.00",
        "custom_amount_bob@example.com": "20.00",  # Total = 50, should be valid
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

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Test Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    expense_data = {
        "description": "Dinner",
        "amount": "50.00",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice@example.com": "30.00",
        "custom_amount_bob@example.com": "30.00",  # Total = 60, should be rejected
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

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    charlie = User(email="charlie@example.com")

    dave = User(email="dave@example.com")

    db.session.add_all([alice, bob, charlie, dave])

    db.session.commit()

    group1 = Group(name="Group 1", created_by_id=alice.id)

    group1.members.extend([alice, bob])

    db.session.add(group1)

    db.session.commit()

    group2 = Group(name="Group 2", created_by_id=charlie.id)

    group2.members.extend([charlie, dave])
    db.session.add_all([group1, group2])
    db.session.commit()

    # Create expenses for both groups
    expense1 = Expense(
        description="Lunch 1",
        amount=20.0,
        payer="Alice",
        group_id=group1.id,
        split_type="equal",
        split_details='{"Alice": 10.0, "Bob": 10.0}',
    )
    expense2 = Expense(
        description="Lunch 2",
        amount=40.0,
        payer="Charlie",
        group_id=group2.id,
        split_type="equal",
        split_details='{"Charlie": 20.0, "Dave": 20.0}',
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

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    charlie = User(email="charlie@example.com")

    dave = User(email="dave@example.com")

    db.session.add_all([alice, bob, charlie, dave])

    db.session.commit()

    group1 = Group(name="Group 1", created_by_id=alice.id)

    group1.members.extend([alice, bob])

    db.session.add(group1)

    db.session.commit()

    group2 = Group(name="Group 2", created_by_id=charlie.id)

    group2.members.extend([charlie, dave])
    db.session.add_all([group1, group2])
    db.session.commit()

    # Create expenses for both groups
    expense1 = Expense(
        description="Lunch 1",
        amount=20.0,
        payer="Alice",
        group_id=group1.id,
        split_type="equal",
        split_details='{"Alice": 10.0, "Bob": 10.0}',
    )
    expense2 = Expense(
        description="Lunch 2",
        amount=40.0,
        payer="Charlie",
        group_id=group2.id,
        split_type="equal",
        split_details='{"Charlie": 20.0, "Dave": 20.0}',
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

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "",  # Missing
        "amount": "100",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com"],
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
        "payer": "alice@example.com",
        "group_id": "",  # Missing
        "split_type": "equal",
        "participants": ["alice@example.com"],
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_missing_payer(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
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
        "participants": ["alice@example.com"],
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_invalid_amount_nonpositive(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "0",  # Or negative
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com"],
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_invalid_amount_type(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "abc",  # Not a number
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com"],
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
        "payer": "alice@example.com",
        "group_id": "99999",  # Nonexistent group
        "split_type": "equal",
        "participants": ["alice@example.com"],
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_payer_not_in_group(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "50",
        "payer": "notamember@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com"],
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_no_participants_selected(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": [],  # Empty list
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_participant_not_in_group(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "equal",
        "participants": ["alice@example.com", "notamember@example.com"],
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_invalid_custom_amount(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    # Assume group members: alice, bob
    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice@example.com": "abc",  # Invalid
        "custom_amount_bob@example.com": "60",
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_no_custom_split_details(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    # No amounts for any member
    data = {
        "description": "Trip",
        "amount": "100",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice@example.com": "",
        "custom_amount_bob@example.com": "",
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0


def test_invalid_custom_split_sum(client, app):
    from extensions import db

    alice = User(email="alice@example.com")

    bob = User(email="bob@example.com")

    db.session.add_all([alice, bob])

    db.session.commit()

    group = Group(name="Fixture Group", created_by_id=alice.id)

    group.members.extend([alice, bob])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "test@example.com"

    data = {
        "description": "Trip",
        "amount": "90",
        "payer": "alice@example.com",
        "group_id": str(group.id),
        "split_type": "custom",
        "custom_amount_alice@example.com": "30",
        "custom_amount_bob@example.com": "40",
        # Adds up to 70, not 90
    }
    resp = client.post("/expense-splitter", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert Expense.query.count() == 0
