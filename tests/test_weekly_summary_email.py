"""Integration tests for weekly summary email functionality."""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ["MAIL_USERNAME"] = "test@example.com"
os.environ["MAIL_PASSWORD"] = "test_password"
os.environ["EMAIL_ENABLED"] = "false"

from app import create_app
from extensions import db
from models import Expense, Group, Settlement, User
from services.group_activity_service import GroupActivityService
from services.notification_service import send_group_activity_summary


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestWeeklySummaryEmail:
    """Tests for weekly summary email generation."""

    def test_send_email_with_expenses_only(self, app):
        """Test sending email with only expenses."""
        with app.app_context():
            # Create test data
            user = User(email="test@example.com", display_name="Test User")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            # Create expense
            expense = Expense(
                description="Test Expense",
                amount=100.0,
                payer="Test User",
                group_id=group.id,
                split_type="equal",
                split_details=json.dumps({"Test User": 100.0}),
                created_at=datetime.now(timezone.utc),
                expense_date=datetime.now(timezone.utc).date(),
            )
            db.session.add(expense)
            db.session.commit()

            # Get activity and format
            activity = GroupActivityService.get_weekly_activity(
                group.id,
                datetime.now(timezone.utc) - timedelta(days=7),
                datetime.now(timezone.utc)
            )
            summary = GroupActivityService.format_activity_summary(activity)

            # Send email (should not raise exception)
            send_group_activity_summary(user, summary)

    def test_send_email_with_settlements_only(self, app):
        """Test sending email with only settlements."""
        with app.app_context():
            user1 = User(email="user1@example.com", display_name="User One")
            user2 = User(email="user2@example.com", display_name="User Two")
            db.session.add_all([user1, user2])
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user1.id)
            group.members.extend([user1, user2])
            db.session.add(group)
            db.session.commit()

            # Create settlement
            settlement = Settlement(
                amount=50.0,
                payer_id=user1.id,
                recipient_id=user2.id,
                note="Test payment",
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(settlement)
            db.session.commit()

            # Get activity and format
            activity = GroupActivityService.get_weekly_activity(
                group.id,
                datetime.now(timezone.utc) - timedelta(days=7),
                datetime.now(timezone.utc)
            )
            summary = GroupActivityService.format_activity_summary(activity)

            # Send email
            send_group_activity_summary(user1, summary)

    def test_send_email_with_both_expenses_and_settlements(self, app):
        """Test sending email with both expenses and settlements."""
        with app.app_context():
            user1 = User(email="user1@example.com", display_name="User One")
            user2 = User(email="user2@example.com", display_name="User Two")
            db.session.add_all([user1, user2])
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user1.id)
            group.members.extend([user1, user2])
            db.session.add(group)
            db.session.commit()

            # Create expense
            expense = Expense(
                description="Dinner",
                amount=100.0,
                payer="User One",
                group_id=group.id,
                split_type="equal",
                split_details=json.dumps({"User One": 50.0, "User Two": 50.0}),
                created_at=datetime.now(timezone.utc),
                expense_date=datetime.now(timezone.utc).date(),
            )
            db.session.add(expense)

            # Create settlement
            settlement = Settlement(
                amount=50.0,
                payer_id=user2.id,
                recipient_id=user1.id,
                note="Paying back",
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(settlement)
            db.session.commit()

            # Get activity and format
            activity = GroupActivityService.get_weekly_activity(
                group.id,
                datetime.now(timezone.utc) - timedelta(days=7),
                datetime.now(timezone.utc)
            )
            summary = GroupActivityService.format_activity_summary(activity)

            # Verify summary has both
            assert summary["expense_count"] == 1
            assert summary["settlement_count"] == 1

            # Send email
            send_group_activity_summary(user1, summary)

    def test_email_fails_with_invalid_user(self, app):
        """Test email sending fails gracefully with invalid user."""
        with app.app_context():
            summary = {
                "group_name": "Test",
                "week_start": "Jan 1",
                "week_end": "Jan 7",
                "expenses": [],
                "settlements": [],
                "expense_count": 0,
                "settlement_count": 0,
                "total_expenses": 0,
                "total_settlements": 0,
            }

            with pytest.raises(ValueError):
                send_group_activity_summary(None, summary)

    def test_email_fails_with_invalid_summary(self, app):
        """Test email sending fails gracefully with invalid summary."""
        with app.app_context():
            user = User(email="test@example.com", display_name="Test")
            db.session.add(user)
            db.session.commit()

            with pytest.raises(ValueError):
                send_group_activity_summary(user, None)


class TestWeeklySummaryCommand:
    """Tests for the weekly summary command."""

    def test_command_processes_multiple_groups(self, app):
        """Test command processes all active groups."""
        with app.app_context():
            # Create multiple groups with activity
            for i in range(3):
                user = User(email=f"user{i}@example.com", display_name=f"User {i}")
                db.session.add(user)
                db.session.commit()

                group = Group(name=f"Group {i}", created_by_id=user.id)
                group.members.append(user)
                db.session.add(group)
                db.session.commit()

                # Add expense
                expense = Expense(
                    description=f"Expense {i}",
                    amount=100.0 * (i + 1),
                    payer=f"User {i}",
                    group_id=group.id,
                    split_type="equal",
                    split_details=json.dumps({f"User {i}": 100.0 * (i + 1)}),
                    created_at=datetime.now(timezone.utc),
                    expense_date=datetime.now(timezone.utc).date(),
                )
                db.session.add(expense)
            db.session.commit()

            # Get all active groups
            groups = GroupActivityService.get_all_active_groups()
            assert len(groups) == 3

    def test_command_skips_groups_without_activity(self, app):
        """Test command skips groups with no activity."""
        with app.app_context():
            user = User(email="user@example.com", display_name="User")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Inactive Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            # Get activity (should be empty)
            activity = GroupActivityService.get_weekly_activity(group.id)
            assert activity["has_activity"] is False

            # Format should return None
            summary = GroupActivityService.format_activity_summary(activity)
            assert summary is None
