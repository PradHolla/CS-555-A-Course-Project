"""Tests for protected functionality."""

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
