"""Tests for group management routes."""

from models import Group, User


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
    """Test that POST /groups/create creates invitations for non-existent members."""
    # Arrange
    from extensions import db
    from models import GroupInvitation

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
    assert len(stored.members) == 1  # Only creator (others are invited)
    assert creator in stored.members
    # Check that invitations were created for non-existent users
    assert GroupInvitation.query.filter_by(email="anikait@example.com").first() is not None
    assert GroupInvitation.query.filter_by(email="sairithik@example.com").first() is not None
    assert GroupInvitation.query.filter_by(email="pradhyumna@example.com").first() is not None


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
    response = client.post("/groups/create", data=group_data, follow_redirects=True)

    # Assert - should redirect back to create page with error message
    assert response.status_code == 200
    assert b"Invalid email format: notanemail" in response.data
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

    # Assert - should redirect back to create page with error
    assert response.status_code == 302
    assert response.location.endswith("/groups/create")
    assert Group.query.count() == 0  # No group created


def test_groups_create_group_skips_duplicate_creator(client, app):
    """Test that creator is not added twice if listed in members, and creates invitation for new user."""
    # Arrange
    from extensions import db
    from models import GroupInvitation

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
    # Creator should only be in members once
    creator_count = sum(1 for m in group.members if m.email == "test@example.com")
    assert creator_count == 1
    assert len(group.members) == 1  # Only creator (alice gets an invitation)
    # Check invitation was created for alice
    assert GroupInvitation.query.filter_by(email="alice@example.com").first() is not None


def test_groups_list_requires_login(client):
    """Test that GET /groups/ requires login."""
    # Act - no login session
    response = client.get("/groups/", follow_redirects=False)

    # Assert - should redirect to login
    assert response.status_code == 302


def test_groups_create_handles_database_error(client, app, monkeypatch):
    """Test that POST /groups/create handles database errors gracefully."""
    # Arrange
    from extensions import db

    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Simulate database error during commit
    def mock_commit():
        raise Exception("Database error")

    monkeypatch.setattr(db.session, "commit", mock_commit)

    group_data = {"name": "Test Group", "members": "member@example.com"}

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=True)

    # Assert - should redirect to create page with error message
    assert response.status_code == 200
    assert b"Failed to create group" in response.data


def test_groups_create_get_returns_ok(client, app):
    """Test that GET /groups/create returns 200 for logged-in user."""
    # Arrange
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.get("/groups/create")

    # Assert
    assert response.status_code == 200
    assert b"Create Group" in response.data or b"CREATE GROUP" in response.data


def test_groups_create_get_requires_login(client):
    """Test that GET /groups/create requires login."""
    # Act - no login session
    response = client.get("/groups/create", follow_redirects=False)

    # Assert - should redirect to login
    assert response.status_code == 302


def test_group_expenses_get_returns_ok(client, app):
    """Test that GET /groups/<group_id> returns 200 for logged-in group member."""
    # Arrange
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.get(f"/groups/{group.id}")

    # Assert
    assert response.status_code == 200
    assert b"Test Group" in response.data


def test_group_expenses_get_requires_login(client, app):
    """Test that GET /groups/<group_id> requires login."""
    # Arrange
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    # Act - no login session
    response = client.get(f"/groups/{group.id}", follow_redirects=False)

    # Assert - should redirect to login
    assert response.status_code == 302


def test_group_expenses_requires_membership(client, app):
    """Test that GET /groups/<group_id> requires user to be a group member."""
    # Arrange
    from extensions import db

    member = User(email="member@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([member, non_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=member.id)
    group.members.append(member)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = non_member.id
        sess["user_email"] = non_member.email

    # Act
    response = client.get(f"/groups/{group.id}", follow_redirects=False)

    # Assert - should redirect or return 403
    assert response.status_code in [302, 403]


def test_group_expenses_post_creates_expense(client, app):
    """Test that POST /groups/<group_id> creates expense for that group."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    participant = User(email="participant@example.com")
    db.session.add_all([payer, participant])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, participant])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    # Create MultiDict to handle multiple participants
    expense_data = MultiDict(
        [
            ("description", "Lunch"),
            ("amount", "30.00"),
            ("payer", "payer@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "participant@example.com"),
        ]
    )

    # Act
    response = client.post(f"/groups/{group.id}", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect after creation
    expense = Expense.query.filter_by(description="Lunch", group_id=group.id).first()
    assert expense is not None
    assert expense.amount == 30.0
