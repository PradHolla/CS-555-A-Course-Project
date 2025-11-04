"""Tests for dashboard functionality."""

import pytest

from extensions import db
from models import Expense, Group, Settlement, User
from services.dashboard_service import DashboardService


def test_dashboard_service_no_data(app):
    """Test dashboard service returns correct values when user has no data."""
    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        summary = DashboardService.get_user_summary(user_id)

        assert summary['total_expenses'] == 0
        assert summary['total_payments_made'] == 0
        assert summary['total_payments_received'] == 0
        assert summary['outstanding_balance'] == 0
        assert summary['has_data'] is False


def test_dashboard_service_with_expenses(app):
    """Test dashboard service calculates expenses correctly."""
    with app.app_context():
        user = User(email="payer@example.com")
        group = Group(name="Test Group", created_by_id=1)
        db.session.add_all([user, group])
        db.session.commit()

        # Add expenses
        expense1 = Expense(
            description="Lunch",
            amount=50.00,
            payer=user.email,
            group_id=group.id
        )
        expense2 = Expense(
            description="Dinner",
            amount=75.00,
            payer=user.email,
            group_id=group.id
        )
        db.session.add_all([expense1, expense2])
        db.session.commit()

        summary = DashboardService.get_user_summary(user.id)

        assert summary['total_expenses'] == 125.00
        assert summary['has_data'] is True


def test_dashboard_service_with_payments(app):
    """Test dashboard service calculates payments correctly."""
    with app.app_context():
        payer = User(email="payer@example.com")
        recipient = User(email="recipient@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()

        # Add payment
        payment = Settlement(
            amount=100.00,
            payer_id=payer.id,
            recipient_id=recipient.id
        )
        db.session.add(payment)
        db.session.commit()

        summary = DashboardService.get_user_summary(payer.id)

        assert summary['total_payments_made'] == 100.00
        assert summary['has_data'] is True


def test_dashboard_service_outstanding_balance(app):
    """Test dashboard service calculates outstanding balance correctly."""
    import json
    
    with app.app_context():
        user = User(email="user@example.com")
        other_user = User(email="other@example.com")
        group = Group(name="Test Group", created_by_id=1)
        db.session.add_all([user, other_user, group])
        db.session.commit()

        # User adds expense of $100, split equally between 2 people
        split_details = {
            "user@example.com": 50.00,
            "other@example.com": 50.00
        }
        expense = Expense(
            description="Lunch",
            amount=100.00,
            payer=user.email,
            group_id=group.id,
            split_type="custom",
            split_details=json.dumps(split_details),
            participants="user@example.com, other@example.com"
        )
        db.session.add(expense)

        # User makes payment of $30
        payment = Settlement(
            amount=30.00,
            payer_id=user.id,
            recipient_id=other_user.id
        )
        db.session.add(payment)
        db.session.commit()

        summary = DashboardService.get_user_summary(user.id)

        # Outstanding = (100 paid - 50 own share = 50 owed) - 30 (payments made) = 20
        assert summary['outstanding_balance'] == 20.00


def test_dashboard_route_requires_login(client):
    """Test that dashboard route requires login."""
    response = client.get("/dashboard/")
    assert response.status_code == 302  # Redirect to login


def test_dashboard_route_shows_no_data(client, app):
    """Test dashboard shows 'no data' message when user has no data."""
    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_email"] = "test@example.com"

    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"No Data to Display" in response.data


def test_dashboard_route_shows_summary(client, app):
    """Test dashboard shows financial summary when user has data."""
    with app.app_context():
        user = User(email="test@example.com")
        group = Group(name="Test Group", created_by_id=1)
        db.session.add_all([user, group])
        db.session.commit()

        expense = Expense(
            description="Test",
            amount=100.00,
            payer=user.email,
            group_id=group.id
        )
        db.session.add(expense)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_email"] = "test@example.com"

    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Total Expenses" in response.data
    assert b"$100.00" in response.data


def test_dashboard_service_with_received_payments(app):
    """Test dashboard includes payments received in balance calculation."""
    with app.app_context():
        user = User(email="user@example.com")
        payer = User(email="payer@example.com")
        db.session.add_all([user, payer])
        db.session.commit()

        # User receives payment of $50
        payment = Settlement(
            amount=50.00,
            payer_id=payer.id,
            recipient_id=user.id
        )
        db.session.add(payment)
        db.session.commit()

        summary = DashboardService.get_user_summary(user.id)

        assert summary['total_payments_received'] == 50.00
        # Outstanding balance should include received payments
        assert summary['outstanding_balance'] == 50.00
        assert summary['has_data'] is True
