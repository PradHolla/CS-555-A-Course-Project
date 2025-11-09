"""
Pytest configuration and fixtures for testing.

This module provides shared fixtures used across all test files:
- app: Flask application instance with test configuration
- client: Flask test client for making HTTP requests
"""

import pytest

from app import app as flask_app
from extensions import db
from models import Group, User


@pytest.fixture
def app(tmp_path):
    """
    Create and configure a Flask application instance for testing.

    Uses a temporary SQLite database that is created fresh for each test
    and cleaned up after the test completes.

    Args:
        tmp_path: pytest fixture providing a temporary directory path

    Yields:
        Flask application configured for testing
    """
    db_path = tmp_path / "test.db"
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"check_same_thread": False}},
        # Email configuration for testing - records emails without sending
        MAIL_SUPPRESS_SEND=True,  # Don't actually send emails in tests
        MAIL_DEFAULT_SENDER="test@sprintpay.local",
        EMAIL_ENABLED=False,  # Always use detailed notification logging in tests
    )

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """
    Create a Flask test client for making HTTP requests in tests.

    Args:
        app: Flask application fixture

    Returns:
        Flask test client instance
    """
    return app.test_client()


def create_user_with_group(name, member_names, created_by_email="creator@example.com"):
    """
    Helper function to create a group with users in the new schema.

    Args:
        name: Name of the group
        member_names: List of member display names (e.g., ["Alice", "Bob"])
        created_by_email: Email of the user who creates the group

    Returns:
        Tuple of (group, creator_user, list of member users)
    """
    # Create creator
    creator = User(
        email=created_by_email, display_name=member_names[0] if member_names else "Creator"
    )
    db.session.add(creator)
    db.session.flush()  # Get the creator ID

    # Create group
    group = Group(name=name, created_by_id=creator.id)

    # Create and add members
    members = []
    for i, member_name in enumerate(member_names):
        # Use creator for first member if email matches
        if i == 0:
            user = creator
        else:
            user = User(email=f"{member_name.lower()}@example.com", display_name=member_name)
            db.session.add(user)

        group.members.append(user)
        members.append(user)

    db.session.add(group)
    db.session.commit()

    return group, creator, members
