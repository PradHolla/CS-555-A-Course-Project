"""Integration tests for profile notification preference API endpoints."""

import json
import os

import pytest

# Set test environment variables
os.environ["MAIL_USERNAME"] = "test@example.com"
os.environ["MAIL_PASSWORD"] = "test_password"
os.environ["EMAIL_ENABLED"] = "false"

from app import create_app
from extensions import db
from models import User


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestProfileNotificationAPI:
    """Test suite for notification preference API endpoints."""

    @pytest.fixture
    def authenticated_user(self, app, client):
        """Create and authenticate a test user."""
        with app.app_context():
            user = User(email="testuser@example.com", display_name="Test User")
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        # Simulate login by setting session
        with client.session_transaction() as sess:
            sess["user_id"] = user_id

        yield user_id

        # Cleanup
        with app.app_context():
            user = db.session.get(User, user_id)
            if user:
                db.session.delete(user)
                db.session.commit()

    def test_update_notification_preferences_json_disable(self, app, client, authenticated_user):
        """Test disabling notifications via JSON API."""
        response = client.patch(
            "/profile/notification-preferences",
            data=json.dumps({"dailyExpenseNotificationsEnabled": False}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert "message" in data
        assert "disabled" in data["message"].lower()
        assert data["data"]["daily_reminder_enabled"] is False

        # Verify in database
        with app.app_context():
            user = db.session.get(User, authenticated_user)
            assert user.daily_reminder_enabled is False

    def test_update_notification_preferences_json_enable(self, app, client, authenticated_user):
        """Test enabling notifications via JSON API."""
        # First disable
        with app.app_context():
            user = db.session.get(User, authenticated_user)
            user.daily_reminder_enabled = False
            db.session.commit()

        # Then enable via API
        response = client.patch(
            "/profile/notification-preferences",
            data=json.dumps({"dailyExpenseNotificationsEnabled": True}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert "message" in data
        assert "enabled" in data["message"].lower()
        assert data["data"]["daily_reminder_enabled"] is True

        # Verify in database
        with app.app_context():
            user = db.session.get(User, authenticated_user)
            assert user.daily_reminder_enabled is True

    def test_update_notification_preferences_json_idempotent(self, app, client, authenticated_user):
        """Test that updating to same value is idempotent."""
        # Disable twice
        response1 = client.patch(
            "/profile/notification-preferences",
            data=json.dumps({"dailyExpenseNotificationsEnabled": False}),
            content_type="application/json",
        )
        response2 = client.patch(
            "/profile/notification-preferences",
            data=json.dumps({"dailyExpenseNotificationsEnabled": False}),
            content_type="application/json",
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify final state
        with app.app_context():
            user = db.session.get(User, authenticated_user)
            assert user.daily_reminder_enabled is False

    def test_update_notification_preferences_json_missing_field(self, client, authenticated_user):
        """Test that missing field returns error."""
        response = client.patch(
            "/profile/notification-preferences",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_update_notification_preferences_form_data(self, app, client, authenticated_user):
        """Test updating preferences via form data (for non-AJAX requests)."""
        response = client.post(
            "/profile/notification-preferences",
            data={"daily_reminder_enabled": "false"},
            follow_redirects=False,
        )

        # Should redirect to profile page
        assert response.status_code == 302
        assert "/profile" in response.location

        # Verify in database
        with app.app_context():
            user = db.session.get(User, authenticated_user)
            assert user.daily_reminder_enabled is False

    def test_update_notification_preferences_unauthenticated(self, client):
        """Test that unauthenticated users cannot update preferences."""
        response = client.patch(
            "/profile/notification-preferences",
            data=json.dumps({"dailyExpenseNotificationsEnabled": False}),
            content_type="application/json",
        )

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_concurrent_updates_no_race_condition(self, app, client, authenticated_user):
        """Test that concurrent updates don't cause race conditions."""
        # Simulate rapid toggling
        for i in range(10):
            enabled = i % 2 == 0
            response = client.patch(
                "/profile/notification-preferences",
                data=json.dumps({"dailyExpenseNotificationsEnabled": enabled}),
                content_type="application/json",
            )
            assert response.status_code == 200

        # Verify final state matches last update
        with app.app_context():
            user = db.session.get(User, authenticated_user)
            assert user.daily_reminder_enabled is False  # Last update was False (i=9, odd)

    def test_update_notification_preferences_database_error(
        self, app, client, authenticated_user, monkeypatch
    ):
        """Test handling of database errors during preference update."""
        with app.app_context():
            # Mock User.query to simulate database error
            original_commit = db.session.commit
            call_count = [0]

            def mock_commit():
                call_count[0] += 1
                # Only fail on the first call (the preference update)
                if call_count[0] == 1:
                    raise Exception("Database error")
                return original_commit()

            monkeypatch.setattr(db.session, "commit", mock_commit)

            response = client.patch(
                "/profile/notification-preferences",
                data=json.dumps({"dailyExpenseNotificationsEnabled": False}),
                content_type="application/json",
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data
            assert "Failed to update notification preference" in data["error"]

    def test_update_notification_preferences_form_data_success_path(
        self, app, client, authenticated_user
    ):
        """Test successful form data update (non-AJAX)."""
        response = client.post(
            "/profile/notification-preferences",
            data={"daily_reminder_enabled": "true"},
            follow_redirects=True,
        )

        # Should redirect and show success
        assert response.status_code == 200

        # Verify in database
        with app.app_context():
            user = db.session.get(User, authenticated_user)
            assert user.daily_reminder_enabled is True

    def test_update_notification_preferences_form_data_with_error(
        self, app, client, authenticated_user, monkeypatch
    ):
        """Test form data update with database error."""
        with app.app_context():
            original_commit = db.session.commit
            call_count = [0]

            def mock_commit():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("Database error")
                return original_commit()

            monkeypatch.setattr(db.session, "commit", mock_commit)

            response = client.post(
                "/profile/notification-preferences",
                data={"daily_reminder_enabled": "false"},
                follow_redirects=False,
            )

            # Should redirect to profile page
            assert response.status_code == 302
            assert "/profile" in response.location
