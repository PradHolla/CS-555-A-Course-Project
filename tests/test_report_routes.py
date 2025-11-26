"""Integration tests for report routes."""
from datetime import date
from extensions import db
from models import Expense, Group, User

def test_monthly_expense_form_requires_login(client):
    response = client.get("/reports/monthly-expense")
    assert response.status_code == 302

def test_monthly_expense_form_displays(client, app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.get("/reports/monthly-expense")
        assert response.status_code == 200
        assert b"Monthly Expense Report" in response.data

def test_download_pdf_success(client, app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=100.00, payer=user.email, group_id=group.id, expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/pdf", data={"year": "2024", "month": "1"})
        assert response.status_code == 200
        assert response.content_type == "application/pdf"

def test_download_csv_success(client, app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=100.00, payer=user.email, group_id=group.id, expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/csv", data={"year": "2024", "month": "1"})
        assert response.status_code == 200
        assert "text/csv" in response.content_type

def test_download_pdf_invalid_date(client, app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/pdf", data={"year": "2024", "month": "13"}, follow_redirects=True)
        assert b"Month must be between 1 and 12" in response.data


def test_download_pdf_empty_month(app, client):
    """Test PDF download for month with no expenses."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/pdf", data={"year": "2024", "month": "1"})
        assert response.status_code == 200
        assert response.content_type == "application/pdf"

def test_download_csv_invalid_input(app, client):
    """Test CSV download handles invalid input gracefully."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/csv", data={"year": "invalid", "month": "1"}, follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid input" in response.data or b"error" in response.data.lower()

def test_download_pdf_with_filters(app, client):
    """Test PDF download with group and category filters."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=100.00, payer=user.email, group_id=group.id, category="Food", expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/pdf", data={"year": "2024", "month": "1", "group_ids": [str(group.id)], "category": "Food"})
        assert response.status_code == 200
