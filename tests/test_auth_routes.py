"""Tests for authentication routes."""

from models import User


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


def test_request_otp_rejects_invalid_email_format(client):
    """Test that POST /auth/request-otp rejects malformed emails."""
    # Arrange - invalid email formats
    invalid_emails = [
        "notanemail",
        "@example.com",
        "test@",
        "test@@example.com",
        "test@example",
    ]

    # Act & Assert
    for email in invalid_emails:
        response = client.post("/auth/request-otp", data={"email": email})
        assert response.status_code == 400, f"Should reject invalid email: {email}"


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
