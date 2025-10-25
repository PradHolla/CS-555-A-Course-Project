"""Tests for home route."""

def test_home_page_returns_ok(client):
    """Test that GET / returns 200."""
    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert b"Expense Splitter" in response.data
