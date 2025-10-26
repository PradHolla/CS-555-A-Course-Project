"""Tests for profile routes."""

from models import User


def test_profile_view_returns_ok(client, app):
    """Test that GET /profile returns 200 and displays user info."""
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

    # Act
    response = client.get("/profile/")

    # Assert
    assert response.status_code == 200
    assert b"Test User" in response.data
    assert b"test@example.com" in response.data
    assert b"USER.PROFILE" in response.data


def test_profile_view_requires_login(client):
    """Test that /profile redirects to login when not authenticated."""
    # Act
    response = client.get("/profile/", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_profile_update_display_name(client, app):
    """Test that POST /profile updates display name successfully."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name="Old Name")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.post("/profile/", data={"display_name": "New Name"}, follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Profile updated successfully!" in response.data
    assert b"New Name" in response.data

    # Verify database was updated
    with app.app_context():
        updated_user = db.session.get(User, user_id)
        assert updated_user.display_name == "New Name"


def test_profile_update_requires_login(client):
    """Test that POST /profile redirects to login when not authenticated."""
    # Act
    response = client.post("/profile/", data={"display_name": "New Name"}, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_profile_update_rejects_empty_display_name(client, app):
    """Test that empty display name is rejected."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name="Original Name")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.post("/profile/", data={"display_name": "   "}, follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Display name cannot be empty" in response.data

    # Verify database was NOT updated
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.display_name == "Original Name"


def test_profile_update_rejects_too_long_display_name(client, app):
    """Test that display name longer than 100 chars is rejected."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name="Original Name")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act - 101 character name
    long_name = "A" * 101
    response = client.post("/profile/", data={"display_name": long_name}, follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Display name must be 100 characters or less" in response.data

    # Verify database was NOT updated
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.display_name == "Original Name"


def test_profile_update_allows_max_length_display_name(client, app):
    """Test that display name of exactly 100 chars is accepted."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name="Original Name")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act - Exactly 100 characters
    max_name = "A" * 100
    response = client.post("/profile/", data={"display_name": max_name}, follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Profile updated successfully!" in response.data

    # Verify database was updated
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.display_name == max_name
        assert len(user.display_name) == 100


def test_profile_displays_groups_count(client, app):
    """Test that profile displays correct number of groups user belongs to."""
    # Arrange
    from extensions import db
    from models import Group

    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        # Create groups with user as member
        group1 = Group(name="Group 1", created_by_id=user.id)
        group2 = Group(name="Group 2", created_by_id=user.id)
        group1.members.append(user)
        group2.members.append(user)
        db.session.add_all([group1, group2])
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/profile/")

    # Assert
    assert response.status_code == 200
    assert b"Groups:" in response.data
    # Should show 2 groups
    assert b">2<" in response.data or b"2</span>" in response.data


def test_profile_update_handles_database_error(client, app, monkeypatch):
    """Test that POST /profile handles database commit errors gracefully."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name="Original Name")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Mock db.session.commit to raise an exception
    def mock_commit():
        raise Exception("Database error")

    monkeypatch.setattr("extensions.db.session.commit", mock_commit)

    # Act
    response = client.post("/profile/", data={"display_name": "New Name"}, follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Failed to update profile" in response.data
    assert b"Database error" in response.data


def test_profile_view_with_no_display_name(client, app):
    """Test that profile page works for users without display name set."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name=None)
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.get("/profile/")

    # Assert
    assert response.status_code == 200
    assert b"test@example.com" in response.data
    # Input field should be empty
    assert b'value=""' in response.data


def test_profile_update_trims_whitespace(client, app):
    """Test that display name whitespace is trimmed."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name="Old Name")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act - Submit with leading/trailing whitespace
    response = client.post(
        "/profile/", data={"display_name": "  Trimmed Name  "}, follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Profile updated successfully!" in response.data

    # Verify whitespace was trimmed
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.display_name == "Trimmed Name"
