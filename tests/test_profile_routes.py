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


def test_delete_account_success(client, app):
    """Test that POST /profile/delete-account deletes user and logs out."""
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
    response = client.post("/profile/delete-account", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Account deleted successfully" in response.data
    assert b"login" in response.data  # Redirected to login page

    # Verify user is logged out
    with client.session_transaction() as session:
        assert "user_id" not in session
        assert "user_email" not in session

    # Verify user is deleted from database
    with app.app_context():
        deleted_user = db.session.get(User, user_id)
        assert deleted_user is None


def test_delete_account_requires_login(client):
    """Test that delete account requires authentication."""
    # Act
    response = client.post("/profile/delete-account", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_delete_account_removes_user_from_groups(client, app):
    """Test that deleting account removes user from all groups."""
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
        group1_id = group1.id
        group2_id = group2.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.post("/profile/delete-account", follow_redirects=True)

    # Assert
    assert response.status_code == 200

    # Verify user is removed from groups
    with app.app_context():
        group1 = db.session.get(Group, group1_id)
        group2 = db.session.get(Group, group2_id)
        assert user_id not in [m.id for m in group1.members]
        assert user_id not in [m.id for m in group2.members]


def test_delete_account_deletes_profile_picture(client, app, tmp_path):
    """Test that deleting account also deletes profile picture file."""
    # Arrange
    from extensions import db
    import os
    from flask import current_app

    with app.app_context():
        # Create user with profile picture
        user = User(email="test@example.com", display_name="Test User")
        user.profile_picture = "test_picture.jpg"
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        # Create mock profile picture file
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        picture_path = os.path.join(upload_folder, "test_picture.jpg")
        with open(picture_path, "w") as f:
            f.write("fake image data")

        # Verify file exists
        assert os.path.exists(picture_path)

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.post("/profile/delete-account", follow_redirects=True)

    # Assert
    assert response.status_code == 200

    # Verify profile picture file is deleted
    with app.app_context():
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        picture_path = os.path.join(upload_folder, "test_picture.jpg")
        assert not os.path.exists(picture_path)


def test_delete_account_handles_missing_profile_picture(client, app):
    """Test that delete account works even if profile picture file doesn't exist."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        user.profile_picture = "nonexistent.jpg"  # File doesn't actually exist
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_email"] = "test@example.com"

    # Act
    response = client.post("/profile/delete-account", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Account deleted successfully" in response.data

    # Verify user is still deleted despite missing file
    with app.app_context():
        deleted_user = db.session.get(User, user_id)
        assert deleted_user is None


def test_delete_account_handles_database_error(client, app, monkeypatch):
    """Test that delete account handles database errors gracefully."""
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

    # Mock db.session.commit to raise an exception
    original_commit = db.session.commit

    def mock_commit():
        raise Exception("Database error")

    monkeypatch.setattr("extensions.db.session.commit", mock_commit)

    # Act
    response = client.post("/profile/delete-account", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Failed to delete account" in response.data
    assert b"Database error" in response.data

    # Restore original commit
    monkeypatch.setattr("extensions.db.session.commit", original_commit)

    # Verify user still exists in database
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None


def test_delete_account_blocked_when_user_owes_money(client, app):
    """Test that user cannot delete account when they owe money."""
    # Arrange
    from extensions import db
    from models import Expense, Group

    with app.app_context():
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        db.session.add_all([user1, user2])
        db.session.flush()

        # Create a group
        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.flush()

        # Create expense where user1 owes money
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="user2@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 50.0, "user2@example.com": 50.0}',
        )
        db.session.add(expense)
        db.session.commit()
        user1_id = user1.id

    with client.session_transaction() as session:
        session["user_id"] = user1_id
        session["user_email"] = "user1@example.com"

    # Act
    response = client.post("/profile/delete-account", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"You cannot delete your account because you owe $50.00" in response.data
    assert b"Please settle all your debts before deleting your account" in response.data

    # Verify user still exists
    with app.app_context():
        user = db.session.get(User, user1_id)
        assert user is not None


def test_delete_account_blocked_when_user_is_owed_money(client, app):
    """Test that user cannot delete account when they are owed money."""
    # Arrange
    from extensions import db
    from models import Expense, Group

    with app.app_context():
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        db.session.add_all([user1, user2])
        db.session.flush()

        # Create a group
        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.flush()

        # Create expense where user1 is owed money (user1 paid)
        expense = Expense(
            description="Dinner",
            amount=80.0,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 40.0, "user2@example.com": 40.0}',
        )
        db.session.add(expense)
        db.session.commit()
        user1_id = user1.id

    with client.session_transaction() as session:
        session["user_id"] = user1_id
        session["user_email"] = "user1@example.com"

    # Act
    response = client.post("/profile/delete-account", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"You cannot delete your account because you are owed $40.00" in response.data
    assert b"Please collect all payments before deleting your account" in response.data

    # Verify user still exists
    with app.app_context():
        user = db.session.get(User, user1_id)
        assert user is not None


def test_delete_account_allowed_after_settling_all_balances(client, app):
    """Test that user can delete account after settling all balances."""
    # Arrange
    from extensions import db
    from models import Expense, Group, Settlement

    with app.app_context():
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        db.session.add_all([user1, user2])
        db.session.flush()

        # Create a group
        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.flush()

        # Create expense where user1 owes money
        expense = Expense(
            description="Coffee",
            amount=20.0,
            payer="user2@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 10.0, "user2@example.com": 10.0}',
        )
        db.session.add(expense)
        db.session.flush()

        # Create settlement to fully pay the debt
        settlement = Settlement(amount=10.0, payer_id=user1.id, recipient_id=user2.id)
        db.session.add(settlement)
        db.session.commit()
        user1_id = user1.id

    with client.session_transaction() as session:
        session["user_id"] = user1_id
        session["user_email"] = "user1@example.com"

    # Act
    response = client.post("/profile/delete-account", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Account deleted successfully" in response.data

    # Verify user is deleted
    with app.app_context():
        user = db.session.get(User, user1_id)
        assert user is None

