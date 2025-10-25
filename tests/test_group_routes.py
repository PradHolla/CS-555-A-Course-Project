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
    response = client.post("/groups/create", data=group_data, follow_redirects=True)

    # Assert - should redirect back to groups page with error message
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
