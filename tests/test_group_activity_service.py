"""Unit tests for GroupActivityService."""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

# Set test environment variables
os.environ["MAIL_USERNAME"] = "test@example.com"
os.environ["MAIL_PASSWORD"] = "test_password"
os.environ["EMAIL_ENABLED"] = "false"

from app import create_app
from extensions import db
from models import Expense, Group, Settlement, User
from services.group_activity_service import GroupActivityService


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


def create_test_group_with_members(name="Test Group", email_suffix=""):
    """Helper to create a group with members."""
    user1 = User(email=f"user1{email_suffix}@example.com", display_name=f"User One{email_suffix}")
    user2 = User(email=f"user2{email_suffix}@example.com", display_name=f"User Two{email_suffix}")
    user3 = User(email=f"user3{email_suffix}@example.com", display_name=f"User Three{email_suffix}")

    db.session.add_all([user1, user2, user3])
    db.session.commit()

    group = Group(name=name, created_by_id=user1.id)
    group.members.extend([user1, user2, user3])

    db.session.add(group)
    db.session.commit()

    return group, [user1, user2, user3]


def create_test_expense(group, payer, amount, days_ago=0):
    """Helper to create a test expense."""
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    expense = Expense(
        description=f"Test Expense {amount}",
        amount=amount,
        payer=payer,
        group_id=group.id,
        split_type="equal",
        split_details=json.dumps({"User One": amount / 2, "User Two": amount / 2}),
        created_at=created_at,
        expense_date=created_at.date(),
    )
    db.session.add(expense)
    db.session.commit()
    return expense


def create_test_settlement(payer, recipient, amount, days_ago=0):
    """Helper to create a test settlement."""
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    settlement = Settlement(
        amount=amount,
        payer_id=payer.id,
        recipient_id=recipient.id,
        note="Test payment",
        created_at=created_at,
    )
    db.session.add(settlement)
    db.session.commit()
    return settlement


class TestGetWeekDateRange:
    """Tests for get_week_date_range method."""

    def test_returns_tuple_of_datetimes(self, app):
        """Test that method returns tuple of two datetimes."""
        with app.app_context():
            start, end = GroupActivityService.get_week_date_range()

            assert isinstance(start, datetime)
            assert isinstance(end, datetime)
            assert start < end

    def test_returns_timezone_aware_datetimes(self, app):
        """Test that returned datetimes are timezone-aware."""
        with app.app_context():
            start, end = GroupActivityService.get_week_date_range()

            assert start.tzinfo is not None
            assert end.tzinfo is not None

    def test_returns_7_day_range(self, app):
        """Test that date range is approximately 7 days."""
        with app.app_context():
            start, end = GroupActivityService.get_week_date_range()

            delta = end - start
            # Should be 7 days minus 1 second (6 days + 86399 seconds)
            assert 6 <= delta.days <= 7


class TestGetWeeklyActivity:
    """Tests for get_weekly_activity method."""

    def test_returns_none_for_invalid_group(self, app):
        """Test that method returns None for non-existent group."""
        with app.app_context():
            result = GroupActivityService.get_weekly_activity(99999)

            assert result is None

    def test_returns_empty_activity_for_group_with_no_activity(self, app):
        """Test returns empty lists when no activity."""
        with app.app_context():
            group, members = create_test_group_with_members()

            result = GroupActivityService.get_weekly_activity(group.id)

            assert result is not None
            assert result["group"] == group
            assert len(result["expenses"]) == 0
            assert len(result["settlements"]) == 0
            assert result["has_activity"] is False

    def test_returns_expenses_within_date_range(self, app):
        """Test returns only expenses within specified date range."""
        with app.app_context():
            group, members = create_test_group_with_members()

            # Create expenses at different times
            create_test_expense(group, "User One", 100.0, days_ago=3)  # Within range
            create_test_expense(group, "User Two", 50.0, days_ago=15)  # Outside range

            # Get activity for last 7 days
            start = datetime.now(timezone.utc) - timedelta(days=7)
            end = datetime.now(timezone.utc)

            result = GroupActivityService.get_weekly_activity(group.id, start, end)

            assert len(result["expenses"]) == 1
            assert result["expenses"][0].amount == 100.0

    def test_returns_settlements_for_group_members(self, app):
        """Test returns settlements involving group members."""
        with app.app_context():
            group, members = create_test_group_with_members()

            # Create settlement between group members
            create_test_settlement(members[0], members[1], 75.0, days_ago=2)

            start = datetime.now(timezone.utc) - timedelta(days=7)
            end = datetime.now(timezone.utc)

            result = GroupActivityService.get_weekly_activity(group.id, start, end)

            assert len(result["settlements"]) == 1
            assert result["settlements"][0].amount == 75.0

    def test_has_activity_flag_true_with_expenses(self, app):
        """Test has_activity flag is True when expenses exist."""
        with app.app_context():
            group, members = create_test_group_with_members()
            create_test_expense(group, "User One", 100.0, days_ago=3)

            start = datetime.now(timezone.utc) - timedelta(days=7)
            end = datetime.now(timezone.utc)

            result = GroupActivityService.get_weekly_activity(group.id, start, end)

            assert result["has_activity"] is True

    def test_has_activity_flag_true_with_settlements(self, app):
        """Test has_activity flag is True when settlements exist."""
        with app.app_context():
            group, members = create_test_group_with_members()
            create_test_settlement(members[0], members[1], 50.0, days_ago=2)

            start = datetime.now(timezone.utc) - timedelta(days=7)
            end = datetime.now(timezone.utc)

            result = GroupActivityService.get_weekly_activity(group.id, start, end)

            assert result["has_activity"] is True


class TestGetAllActiveGroups:
    """Tests for get_all_active_groups method."""

    def test_returns_empty_list_when_no_groups(self, app):
        """Test returns empty list when no groups exist."""
        with app.app_context():
            groups = GroupActivityService.get_all_active_groups()

            assert isinstance(groups, list)
            assert len(groups) == 0

    def test_returns_only_groups_with_members(self, app):
        """Test returns only groups that have members."""
        with app.app_context():
            # Create group with members
            group1, members = create_test_group_with_members("Active Group")

            # Create group without members
            user = User(email="creator@example.com", display_name="Creator")
            db.session.add(user)
            db.session.commit()

            group2 = Group(name="Empty Group", created_by_id=user.id)
            db.session.add(group2)
            db.session.commit()

            groups = GroupActivityService.get_all_active_groups()

            assert len(groups) == 1
            assert groups[0].name == "Active Group"

    def test_returns_multiple_active_groups(self, app):
        """Test returns all groups with members."""
        with app.app_context():
            group1, members1 = create_test_group_with_members("Group 1", "_g1")
            group2, members2 = create_test_group_with_members("Group 2", "_g2")

            groups = GroupActivityService.get_all_active_groups()

            assert len(groups) == 2
            group_names = [g.name for g in groups]
            assert "Group 1" in group_names
            assert "Group 2" in group_names


class TestFormatActivitySummary:
    """Tests for format_activity_summary method."""

    def test_returns_none_for_no_activity(self, app):
        """Test returns None when no activity."""
        with app.app_context():
            group, members = create_test_group_with_members()

            activity_data = GroupActivityService.get_weekly_activity(group.id)
            summary = GroupActivityService.format_activity_summary(activity_data)

            assert summary is None

    def test_formats_expenses_correctly(self, app):
        """Test formats expense data correctly."""
        with app.app_context():
            group, members = create_test_group_with_members()
            create_test_expense(group, "User One", 100.0, days_ago=2)

            start = datetime.now(timezone.utc) - timedelta(days=7)
            end = datetime.now(timezone.utc)

            activity_data = GroupActivityService.get_weekly_activity(group.id, start, end)
            summary = GroupActivityService.format_activity_summary(activity_data)

            assert summary is not None
            assert summary["expense_count"] == 1
            assert summary["total_expenses"] == 100.0
            assert len(summary["expenses"]) == 1
            assert summary["expenses"][0]["amount"] == 100.0

    def test_formats_settlements_correctly(self, app):
        """Test formats settlement data correctly."""
        with app.app_context():
            group, members = create_test_group_with_members()
            create_test_settlement(members[0], members[1], 50.0, days_ago=2)

            start = datetime.now(timezone.utc) - timedelta(days=7)
            end = datetime.now(timezone.utc)

            activity_data = GroupActivityService.get_weekly_activity(group.id, start, end)
            summary = GroupActivityService.format_activity_summary(activity_data)

            assert summary is not None
            assert summary["settlement_count"] == 1
            assert summary["total_settlements"] == 50.0
            assert len(summary["settlements"]) == 1

    def test_includes_group_information(self, app):
        """Test includes group name and date range."""
        with app.app_context():
            group, members = create_test_group_with_members("My Test Group")
            create_test_expense(group, "User One", 100.0, days_ago=2)

            start = datetime.now(timezone.utc) - timedelta(days=7)
            end = datetime.now(timezone.utc)

            activity_data = GroupActivityService.get_weekly_activity(group.id, start, end)
            summary = GroupActivityService.format_activity_summary(activity_data)

            assert summary["group_name"] == "My Test Group"
            assert summary["group_id"] == group.id
            assert "week_start" in summary
            assert "week_end" in summary


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_timezone_naive_dates(self, app):
        """Test handles timezone-naive dates gracefully."""
        with app.app_context():
            group, members = create_test_group_with_members()

            # Pass timezone-naive dates
            start = datetime.now() - timedelta(days=7)
            end = datetime.now()

            result = GroupActivityService.get_weekly_activity(group.id, start, end)

            assert result is not None
            assert "expenses" in result

    def test_handles_empty_group_members(self, app):
        """Test handles group with no members."""
        with app.app_context():
            user = User(email="creator@example.com", display_name="Creator")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Empty Group", created_by_id=user.id)
            db.session.add(group)
            db.session.commit()

            result = GroupActivityService.get_weekly_activity(group.id)

            assert result is not None
            assert len(result["settlements"]) == 0

    def test_format_activity_summary_with_none_input(self, app):
        """Test format_activity_summary handles None input."""
        with app.app_context():
            result = GroupActivityService.format_activity_summary(None)
            assert result is None

    def test_format_activity_summary_with_empty_dict(self, app):
        """Test format_activity_summary handles empty dict."""
        with app.app_context():
            result = GroupActivityService.format_activity_summary({})
            assert result is None
