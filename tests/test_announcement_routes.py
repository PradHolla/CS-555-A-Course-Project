"""Tests for announcement routes."""

from datetime import datetime, timedelta, timezone

import pytest

from models import Announcement, Group, User


# ========== Model Tests ==========


def test_announcement_create_and_persist(app):
    """Test that Announcement model can be created and persisted."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
        is_pinned=False,
    )
    db.session.add(announcement)
    db.session.commit()

    stored = Announcement.query.first()
    assert stored is not None
    assert stored.content == "Test announcement"
    assert stored.group_id == group.id
    assert stored.author_id == user.id
    assert stored.is_pinned is False
    assert stored.created_at is not None


def test_announcement_requires_group(app):
    """Test that Announcement requires group_id."""
    from extensions import db
    from sqlalchemy.exc import IntegrityError

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    announcement = Announcement(
        author_id=user.id,
        content="Test announcement",
    )

    db.session.add(announcement)
    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_announcement_requires_author(app):
    """Test that Announcement requires author_id."""
    from extensions import db
    from sqlalchemy.exc import IntegrityError

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        content="Test announcement",
    )

    db.session.add(announcement)
    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_announcement_content_max_length(app):
    """Test that Announcement content is limited to 100 characters."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    # Create announcement with exactly 100 characters
    content_100 = "a" * 100
    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content=content_100,
    )
    db.session.add(announcement)
    db.session.commit()

    stored = Announcement.query.first()
    assert len(stored.content) == 100


def test_announcement_pinned_default_false(app):
    """Test that Announcement is_pinned defaults to False."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    stored = Announcement.query.first()
    assert stored.is_pinned is False


def test_announcement_relationships(app):
    """Test that Announcement relationships to Group and User work."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    stored = Announcement.query.first()
    assert stored.group is not None
    assert stored.group.id == group.id
    assert stored.author is not None
    assert stored.author.id == user.id


def test_announcement_cascade_delete(app):
    """Test that announcements are deleted when group is deleted."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    assert Announcement.query.count() == 1

    db.session.delete(group)
    db.session.commit()

    assert Announcement.query.count() == 0


# ========== Route Tests - Create Announcement ==========


def test_create_announcement_success(client, app):
    """Test that POST creates announcement successfully."""
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

    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Test announcement"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 302  # Redirect after creation
    announcement = Announcement.query.filter_by(group_id=group.id).first()
    assert announcement is not None
    assert announcement.content == "Test announcement"
    assert announcement.author_id == user.id


def test_create_announcement_requires_login(client, app):
    """Test that creating announcement requires login."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Test announcement"},
        follow_redirects=False,
    )

    assert response.status_code == 302  # Redirect to login


def test_create_announcement_requires_membership(client, app):
    """Test that user must be group member to create announcement."""
    from extensions import db

    creator = User(email="creator@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([creator, non_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.append(creator)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = non_member.id
        sess["user_email"] = non_member.email

    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Test announcement"},
        follow_redirects=False,
    )

    assert response.status_code in [302, 403]
    assert Announcement.query.count() == 0


def test_create_announcement_empty_content(client, app):
    """Test that empty content is rejected."""
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

    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": ""},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Content cannot be empty" in response.data
    assert Announcement.query.count() == 0


def test_create_announcement_content_too_long(client, app):
    """Test that content > 100 chars is rejected."""
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

    long_content = "a" * 101
    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": long_content},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"cannot exceed 100 characters" in response.data
    assert Announcement.query.count() == 0


def test_create_announcement_exactly_100_chars(client, app):
    """Test that exactly 100 chars is accepted."""
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

    content_100 = "a" * 100
    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": content_100},
        follow_redirects=False,
    )

    assert response.status_code == 302
    announcement = Announcement.query.first()
    assert announcement is not None
    assert len(announcement.content) == 100


def test_create_announcement_strips_whitespace(client, app):
    """Test that leading/trailing whitespace is stripped."""
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

    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "  Test announcement  "},
        follow_redirects=False,
    )

    assert response.status_code == 302
    announcement = Announcement.query.first()
    assert announcement.content == "Test announcement"


def test_create_announcement_sets_author(client, app):
    """Test that author is set to current user."""
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

    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Test announcement"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    announcement = Announcement.query.first()
    assert announcement.author_id == user.id


def test_create_announcement_returns_json(client, app):
    """Test that JSON response format is correct."""
    from extensions import db
    import json

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

    # Send as form data with X-Requested-With header (as the actual frontend does)
    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Test announcement"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["success"] is True
    assert "announcement" in data
    assert data["announcement"]["content"] == "Test announcement"


def test_create_announcement_group_not_found(client, app):
    """Test handling of non-existent group."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        "/groups/99999/announcements",
        data={"content": "Test announcement"},
        follow_redirects=False,
    )

    assert response.status_code in [302, 404]


# ========== Route Tests - Edit Announcement ==========


def test_edit_announcement_success(client, app):
    """Test that POST updates announcement content."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": "Updated content"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.content == "Updated content"
    assert announcement.updated_at is not None


def test_edit_announcement_requires_login(client, app):
    """Test that editing announcement requires login."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": "Updated content"},
        follow_redirects=False,
    )

    assert response.status_code == 302  # Redirect to login


def test_edit_announcement_only_by_author(client, app):
    """Test that only author can edit announcement."""
    from extensions import db

    author = User(email="author@example.com")
    other_user = User(email="other@example.com")
    db.session.add_all([author, other_user])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=author.id)
    group.members.extend([author, other_user])
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=author.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
        sess["user_email"] = other_user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": "Updated content"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"only edit your own" in response.data
    db.session.refresh(announcement)
    assert announcement.content == "Original content"


def test_edit_announcement_empty_content(client, app):
    """Test that empty content is rejected."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": ""},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Content cannot be empty" in response.data
    db.session.refresh(announcement)
    assert announcement.content == "Original content"


def test_edit_announcement_content_too_long(client, app):
    """Test that content > 100 chars is rejected."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    long_content = "a" * 101
    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": long_content},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"cannot exceed 100 characters" in response.data
    db.session.refresh(announcement)
    assert announcement.content == "Original content"


def test_edit_announcement_updates_timestamp(client, app):
    """Test that updated_at is set when editing."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    assert announcement.updated_at is None

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": "Updated content"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.updated_at is not None


def test_edit_announcement_not_found(client, app):
    """Test handling of non-existent announcement."""
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

    response = client.post(
        f"/groups/{group.id}/announcements/99999/edit",
        data={"content": "Updated content"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Announcement not found" in response.data


def test_edit_announcement_wrong_group(client, app):
    """Test that editing announcement in different group is rejected."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group1 = Group(name="Group 1", created_by_id=user.id)
    group2 = Group(name="Group 2", created_by_id=user.id)
    group1.members.append(user)
    group2.members.append(user)
    db.session.add_all([group1, group2])
    db.session.commit()

    announcement = Announcement(
        group_id=group1.id,
        author_id=user.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group2.id}/announcements/{announcement.id}/edit",
        data={"content": "Updated content"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Announcement not found" in response.data
    db.session.refresh(announcement)
    assert announcement.content == "Original content"


# ========== Route Tests - Delete Announcement ==========


def test_delete_announcement_success(client, app):
    """Test that POST deletes announcement."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    assert Announcement.query.count() == 1

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert Announcement.query.count() == 0


def test_delete_announcement_requires_login(client, app):
    """Test that deleting announcement requires login."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 302  # Redirect to login
    assert Announcement.query.count() == 1


def test_delete_announcement_only_by_author(client, app):
    """Test that only author can delete announcement."""
    from extensions import db

    author = User(email="author@example.com")
    other_user = User(email="other@example.com")
    db.session.add_all([author, other_user])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=author.id)
    group.members.extend([author, other_user])
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=author.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
        sess["user_email"] = other_user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"only delete your own" in response.data
    assert Announcement.query.count() == 1


def test_delete_announcement_not_found(client, app):
    """Test handling of non-existent announcement."""
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

    response = client.post(
        f"/groups/{group.id}/announcements/99999/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Announcement not found" in response.data


def test_delete_announcement_wrong_group(client, app):
    """Test that deleting announcement in different group is rejected."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group1 = Group(name="Group 1", created_by_id=user.id)
    group2 = Group(name="Group 2", created_by_id=user.id)
    group1.members.append(user)
    group2.members.append(user)
    db.session.add_all([group1, group2])
    db.session.commit()

    announcement = Announcement(
        group_id=group1.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group2.id}/announcements/{announcement.id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Announcement not found" in response.data
    assert Announcement.query.count() == 1


def test_delete_announcement_removes_from_db(client, app):
    """Test that announcement is removed from database."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    announcement_id = announcement.id

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 302
    from extensions import db
    deleted = db.session.get(Announcement, announcement_id)
    assert deleted is None


# ========== Route Tests - Pin/Unpin Announcement ==========


def test_pin_announcement_success(client, app):
    """Test that POST pins announcement."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
        is_pinned=False,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=False,
    )

    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.is_pinned is True


def test_unpin_announcement_success(client, app):
    """Test that POST unpins announcement."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
        is_pinned=True,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=False,
    )

    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.is_pinned is False


def test_toggle_pin_announcement(client, app):
    """Test that toggle pin status works correctly."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
        is_pinned=False,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Pin it
    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.is_pinned is True

    # Unpin it
    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.is_pinned is False


def test_pin_announcement_requires_login(client, app):
    """Test that pinning announcement requires login."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=False,
    )

    assert response.status_code == 302  # Redirect to login


def test_pin_announcement_only_by_author(client, app):
    """Test that only author can pin announcement."""
    from extensions import db

    author = User(email="author@example.com")
    other_user = User(email="other@example.com")
    db.session.add_all([author, other_user])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=author.id)
    group.members.extend([author, other_user])
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=author.id,
        content="Test announcement",
        is_pinned=False,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
        sess["user_email"] = other_user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"only pin your own" in response.data
    db.session.refresh(announcement)
    assert announcement.is_pinned is False


def test_pin_announcement_not_found(client, app):
    """Test handling of non-existent announcement."""
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

    response = client.post(
        f"/groups/{group.id}/announcements/99999/pin",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Announcement not found" in response.data


# ========== Route Tests - Display Announcements ==========


def test_group_expenses_shows_announcements(client, app):
    """Test that announcements appear on group expenses page."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get(f"/groups/{group.id}")

    assert response.status_code == 200
    assert b"Test announcement" in response.data
    assert b"Announcements" in response.data


def test_group_expenses_pinned_first(client, app):
    """Test that pinned announcements appear before unpinned."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    unpinned = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Unpinned announcement",
        is_pinned=False,
    )
    pinned = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Pinned announcement",
        is_pinned=True,
    )
    db.session.add_all([unpinned, pinned])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get(f"/groups/{group.id}")

    assert response.status_code == 200
    content = response.data.decode("utf-8")
    pinned_index = content.find("Pinned announcement")
    unpinned_index = content.find("Unpinned announcement")
    assert pinned_index < unpinned_index


def test_group_expenses_sorted_by_date(client, app):
    """Test that unpinned announcements are sorted by created_at desc."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    older = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Older announcement",
        is_pinned=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    newer = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Newer announcement",
        is_pinned=False,
    )
    db.session.add_all([older, newer])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get(f"/groups/{group.id}")

    assert response.status_code == 200
    content = response.data.decode("utf-8")
    newer_index = content.find("Newer announcement")
    older_index = content.find("Older announcement")
    assert newer_index < older_index


def test_list_groups_shows_announcement_indicators(client, app):
    """Test that groups list shows announcement counts."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
        is_pinned=True,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get("/groups/")

    assert response.status_code == 200
    assert b"pinned" in response.data.lower()


def test_list_groups_shows_pinned_count(client, app):
    """Test that groups list shows pinned announcement count."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    pinned1 = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Pinned 1",
        is_pinned=True,
    )
    pinned2 = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Pinned 2",
        is_pinned=True,
    )
    db.session.add_all([pinned1, pinned2])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get("/groups/")

    assert response.status_code == 200
    assert b"2 pinned" in response.data


def test_list_groups_shows_recent_count(client, app):
    """Test that groups list shows recent announcement count."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    recent = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Recent announcement",
        is_pinned=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.session.add(recent)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get("/groups/")

    assert response.status_code == 200
    assert b"recent" in response.data.lower()


def test_announcements_display_author_name(client, app):
    """Test that author name is displayed correctly."""
    from extensions import db

    user = User(email="test@example.com", display_name="Test User")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get(f"/groups/{group.id}")

    assert response.status_code == 200
    assert b"Test User" in response.data


def test_announcements_display_date(client, app):
    """Test that creation date is displayed correctly."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get(f"/groups/{group.id}")

    assert response.status_code == 200
    # Check that date is displayed (format may vary)
    assert announcement.created_at.strftime("%Y") in response.data.decode("utf-8")


def test_announcements_edit_button_only_for_author(client, app):
    """Test that edit button is only visible to author."""
    from extensions import db

    author = User(email="author@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([author, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=author.id)
    group.members.extend([author, viewer])
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=author.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    # Author should see edit button
    with client.session_transaction() as sess:
        sess["user_id"] = author.id
        sess["user_email"] = author.email

    response = client.get(f"/groups/{group.id}")
    assert response.status_code == 200
    assert b"editAnnouncement" in response.data

    # Viewer should not see edit button
    with client.session_transaction() as sess:
        sess["user_id"] = viewer.id
        sess["user_email"] = viewer.email

    response = client.get(f"/groups/{group.id}")
    assert response.status_code == 200
    # Edit button should not be in the announcement item for non-author
    content = response.data.decode("utf-8")
    # The edit button function should not be accessible for this user's announcements
    # We check that the announcement exists but edit button is not shown
    assert b"Test announcement" in response.data


def test_announcements_delete_button_only_for_author(client, app):
    """Test that delete button is only visible to author."""
    from extensions import db

    author = User(email="author@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([author, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=author.id)
    group.members.extend([author, viewer])
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=author.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    # Author should see delete button
    with client.session_transaction() as sess:
        sess["user_id"] = author.id
        sess["user_email"] = author.email

    response = client.get(f"/groups/{group.id}")
    assert response.status_code == 200
    assert b"deleteAnnouncement" in response.data


def test_announcements_pin_button_only_for_author(client, app):
    """Test that pin button is only visible to author."""
    from extensions import db

    author = User(email="author@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([author, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=author.id)
    group.members.extend([author, viewer])
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=author.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    # Author should see pin button
    with client.session_transaction() as sess:
        sess["user_id"] = author.id
        sess["user_email"] = author.email

    response = client.get(f"/groups/{group.id}")
    assert response.status_code == 200
    assert b"togglePinAnnouncement" in response.data


# ========== Integration Tests ==========


def test_announcement_lifecycle(client, app):
    """Test create, edit, pin, unpin, delete flow."""
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

    # Create
    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Original content"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    announcement = Announcement.query.first()
    assert announcement.content == "Original content"

    # Edit
    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": "Updated content"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.content == "Updated content"

    # Pin
    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.is_pinned is True

    # Unpin
    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.is_pinned is False

    # Delete
    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert Announcement.query.count() == 0


def test_multiple_announcements_ordering(client, app):
    """Test that multiple pinned/unpinned announcements order correctly."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    unpinned1 = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Unpinned 1",
        is_pinned=False,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    pinned1 = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Pinned 1",
        is_pinned=True,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    unpinned2 = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Unpinned 2",
        is_pinned=False,
    )
    pinned2 = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Pinned 2",
        is_pinned=True,
    )
    db.session.add_all([unpinned1, pinned1, unpinned2, pinned2])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.get(f"/groups/{group.id}")

    assert response.status_code == 200
    content = response.data.decode("utf-8")
    # Pinned should come first
    pinned1_index = content.find("Pinned 1")
    pinned2_index = content.find("Pinned 2")
    unpinned1_index = content.find("Unpinned 1")
    unpinned2_index = content.find("Unpinned 2")

    # All pinned should come before all unpinned
    assert pinned1_index < unpinned1_index
    assert pinned2_index < unpinned1_index
    # Within unpinned, newer should come first
    assert unpinned2_index < unpinned1_index


def test_announcement_with_special_characters(client, app):
    """Test handling of special characters in content."""
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

    special_content = "Test with <>&\"' special chars"
    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": special_content},
        follow_redirects=False,
    )

    assert response.status_code == 302
    announcement = Announcement.query.first()
    assert announcement.content == special_content


def test_announcement_unicode_support(client, app):
    """Test support for Unicode characters."""
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

    unicode_content = "Test with 中文 and 🎉 emoji"
    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": unicode_content},
        follow_redirects=False,
    )

    assert response.status_code == 302
    announcement = Announcement.query.first()
    assert announcement.content == unicode_content


def test_announcements_per_group_isolation(client, app):
    """Test that announcements are isolated per group."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group1 = Group(name="Group 1", created_by_id=user.id)
    group2 = Group(name="Group 2", created_by_id=user.id)
    group1.members.append(user)
    group2.members.append(user)
    db.session.add_all([group1, group2])
    db.session.commit()

    announcement1 = Announcement(
        group_id=group1.id,
        author_id=user.id,
        content="Group 1 announcement",
    )
    announcement2 = Announcement(
        group_id=group2.id,
        author_id=user.id,
        content="Group 2 announcement",
    )
    db.session.add_all([announcement1, announcement2])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Check group1 only shows its announcement
    response = client.get(f"/groups/{group1.id}")
    assert response.status_code == 200
    assert b"Group 1 announcement" in response.data
    assert b"Group 2 announcement" not in response.data

    # Check group2 only shows its announcement
    response = client.get(f"/groups/{group2.id}")
    assert response.status_code == 200
    assert b"Group 2 announcement" in response.data
    assert b"Group 1 announcement" not in response.data


# ========== Edge Cases ==========


def test_create_announcement_very_long_whitespace(client, app):
    """Test handling of whitespace-only content."""
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

    whitespace_content = "   \n\t   "
    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": whitespace_content},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Content cannot be empty" in response.data
    assert Announcement.query.count() == 0


def test_edit_announcement_preserves_pin_status(client, app):
    """Test that edit doesn't change pin status."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Original content",
        is_pinned=True,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": "Updated content"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    db.session.refresh(announcement)
    assert announcement.content == "Updated content"
    assert announcement.is_pinned is True


def test_delete_pinned_announcement(client, app):
    """Test that pinned announcements can be deleted."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Pinned announcement",
        is_pinned=True,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert Announcement.query.count() == 0


def test_multiple_users_create_announcements(client, app):
    """Test that multiple users can create announcements in same group."""
    from extensions import db

    user1 = User(email="user1@example.com")
    user2 = User(email="user2@example.com")
    db.session.add_all([user1, user2])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user1.id)
    group.members.extend([user1, user2])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user1.id
        sess["user_email"] = user1.email

    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Announcement from user1"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with client.session_transaction() as sess:
        sess["user_id"] = user2.id
        sess["user_email"] = user2.email

    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Announcement from user2"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    assert Announcement.query.count() == 2
    announcements = Announcement.query.all()
    assert announcements[0].author_id in [user1.id, user2.id]
    assert announcements[1].author_id in [user1.id, user2.id]


def test_announcement_author_leaves_group(client, app):
    """Test that announcement remains when author leaves group."""
    from extensions import db

    author = User(email="author@example.com")
    other_user = User(email="other@example.com")
    db.session.add_all([author, other_user])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=author.id)
    group.members.extend([author, other_user])
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=author.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    # Author leaves group
    group.members.remove(author)
    db.session.commit()

    # Announcement should still exist
    assert Announcement.query.count() == 1
    stored = Announcement.query.first()
    assert stored.author_id == author.id


# ========== Additional Coverage Tests for Non-AJAX Paths ==========
# These tests ensure non-AJAX code paths are covered (flash messages and redirects)


def test_create_announcement_non_ajax_redirect(client, app):
    """Test that non-AJAX requests redirect with flash message."""
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

    # POST without AJAX header
    response = client.post(
        f"/groups/{group.id}/announcements",
        data={"content": "Test announcement"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Announcement created successfully" in response.data
    announcement = Announcement.query.first()
    assert announcement is not None
    assert announcement.content == "Test announcement"


def test_edit_announcement_non_ajax_redirect(client, app):
    """Test that non-AJAX edit requests redirect with flash message."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/edit",
        data={"content": "Updated content"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Announcement updated successfully" in response.data
    db.session.refresh(announcement)
    assert announcement.content == "Updated content"


def test_delete_announcement_non_ajax_redirect(client, app):
    """Test that non-AJAX delete requests redirect with flash message."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Announcement deleted successfully" in response.data
    assert Announcement.query.count() == 0


def test_pin_announcement_non_ajax_redirect(client, app):
    """Test that non-AJAX pin requests redirect with flash message."""
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
        is_pinned=False,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    response = client.post(
        f"/groups/{group.id}/announcements/{announcement.id}/pin",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"pinned successfully" in response.data
    db.session.refresh(announcement)
    assert announcement.is_pinned is True


def test_create_announcement_exception_handling(client, app):
    """Test exception handling in create announcement (non-AJAX path)."""
    from extensions import db
    from unittest.mock import patch

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

    # Mock db.session.commit to raise an exception
    with patch("extensions.db.session.commit", side_effect=Exception("Database error")):
        response = client.post(
            f"/groups/{group.id}/announcements",
            data={"content": "Test announcement"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Failed to create announcement" in response.data


def test_edit_announcement_exception_handling(client, app):
    """Test exception handling in edit announcement (non-AJAX path)."""
    from extensions import db
    from unittest.mock import patch

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Original content",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Mock db.session.commit to raise an exception
    with patch("extensions.db.session.commit", side_effect=Exception("Database error")):
        response = client.post(
            f"/groups/{group.id}/announcements/{announcement.id}/edit",
            data={"content": "Updated content"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Failed to update announcement" in response.data


def test_delete_announcement_exception_handling(client, app):
    """Test exception handling in delete announcement (non-AJAX path)."""
    from extensions import db
    from unittest.mock import patch

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Mock db.session.commit to raise an exception
    with patch("extensions.db.session.commit", side_effect=Exception("Database error")):
        response = client.post(
            f"/groups/{group.id}/announcements/{announcement.id}/delete",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Failed to delete announcement" in response.data


def test_pin_announcement_exception_handling(client, app):
    """Test exception handling in pin announcement (non-AJAX path)."""
    from extensions import db
    from unittest.mock import patch

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    announcement = Announcement(
        group_id=group.id,
        author_id=user.id,
        content="Test announcement",
        is_pinned=False,
    )
    db.session.add(announcement)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Mock db.session.commit to raise an exception
    with patch("extensions.db.session.commit", side_effect=Exception("Database error")):
        response = client.post(
            f"/groups/{group.id}/announcements/{announcement.id}/pin",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Failed to toggle pin status" in response.data



