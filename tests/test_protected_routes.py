"""Tests for protected functionality."""

from models import User


def test_expense_splitter_redirects_if_not_logged_in(client):
    """Test that /expense-splitter redirects to login if user not authenticated."""
    # Act
    response = client.get("/expense-splitter", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_expense_splitter_accessible_when_logged_in(client, app):
    """Test that /expense-splitter redirects to groups when user is logged in."""
    # Arrange - create user and simulate logged in session
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_email"] = "test@example.com"

    # Act
    response = client.get("/expense-splitter", follow_redirects=False)

    # Assert - should redirect to groups list
    assert response.status_code == 302
    assert "/groups/" in response.location


def test_expense_splitter_clears_stale_session(client, app):
    """Test that /expense-splitter clears session and redirects when user doesn't exist."""
    # Arrange - simulate session with non-existent user
    with client.session_transaction() as sess:
        sess["user_id"] = 99999  # User doesn't exist
        sess["user_email"] = "nonexistent@example.com"

    # Act
    response = client.get("/expense-splitter", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Your session has expired" in response.data
    assert b"Log in" in response.data or b"Login" in response.data

    # Verify session was cleared
    with client.session_transaction() as sess:
        assert "user_id" not in sess
