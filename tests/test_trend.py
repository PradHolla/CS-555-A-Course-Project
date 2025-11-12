"""Tests for the /groups/trend page."""

from datetime import date

from models import Group, User


def test_trend_page_shows_monthly_totals(client, app):
    """Ensure the trend page aggregates expenses per payer by month."""
    from extensions import db
    from models import Expense

    # Arrange - create users and group
    creator = User(email="trend_creator@example.com", display_name="Creator")
    member = User(email="trend_member@example.com", display_name="Member")
    db.session.add_all([creator, member])
    db.session.commit()

    group = Group(name="TrendGroup", created_by_id=creator.id)
    group.members.extend([creator, member])
    db.session.add(group)
    db.session.commit()

    # Create two expenses in different months
    today = date.today()
    # this month
    e1 = Expense(description="ThisMonth", amount=25.0, payer=creator.email, group_id=group.id, split_type="equal", split_details='{"trend_creator@example.com": 25.0}', participants=creator.email, expense_date=today)
    # previous month - safe fallback when month==1
    prev_month_year = today.year if today.month > 1 else today.year - 1
    prev_month = today.month - 1 if today.month > 1 else 12
    e2 = Expense(description="PrevMonth", amount=15.0, payer=creator.email, group_id=group.id, split_type="equal", split_details='{"trend_creator@example.com": 15.0}', participants=creator.email, expense_date=date(prev_month_year, prev_month, min(28, today.day)))

    db.session.add_all([e1, e2])
    db.session.commit()

    # Act - login as creator and request trend page
    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email

    response = client.get("/groups/trend")

    # Assert
    assert response.status_code == 200
    assert b"Creator" in response.data or b"trend_creator@example.com" in response.data
    # amounts should appear formatted
    assert b"25.00" in response.data
    assert b"15.00" in response.data
