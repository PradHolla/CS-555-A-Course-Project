"""Unit tests for expense report service."""
from datetime import date
from extensions import db
from models import Expense, Group, User
from services.expense_report_service import ExpenseReportService

def test_get_monthly_expenses_with_data(app):
    with app.app_context():
        user = User(email="user@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=100.00, payer=user.email, group_id=group.id, category="Food", expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        report = ExpenseReportService.get_monthly_expenses(user.id, 2024, 1)
        assert len(report["expenses"]) == 1
        assert report["summary"]["total_amount"] == 100.00

def test_get_monthly_expenses_no_groups(app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        report = ExpenseReportService.get_monthly_expenses(user.id, 2024, 1)
        assert len(report["expenses"]) == 0

def test_generate_csv(app):
    with app.app_context():
        report_data = {"filters": {"year": 2024, "month": 1}, "summary": {"total_expenses": 1, "total_amount": 100.00, "by_category": {}, "by_group": {}}, "expenses": [{"date": "2024-01-15", "description": "Test", "amount": 100.00, "category": "Food", "payer": "user@example.com", "group_name": "Test"}]}
        csv_content = ExpenseReportService.generate_csv(report_data)
        assert b"Monthly Expense Report" in csv_content

def test_generate_pdf(app):
    with app.app_context():
        report_data = {"filters": {"year": 2024, "month": 1}, "summary": {"total_expenses": 1, "total_amount": 100.00, "by_category": {}, "by_group": {}}, "expenses": [{"date": "2024-01-15", "description": "Test", "amount": 100.00, "category": "Food", "payer": "user@example.com", "group_name": "Test"}]}
        pdf_content = ExpenseReportService.generate_pdf(report_data)
        assert pdf_content[:4] == b"%PDF"

def test_validate_date_range_valid(app):
    with app.app_context():
        is_valid, error = ExpenseReportService.validate_date_range(2024, 6)
        assert is_valid is True

def test_validate_date_range_invalid_month(app):
    with app.app_context():
        is_valid, error = ExpenseReportService.validate_date_range(2024, 13)
        assert is_valid is False

def test_get_available_categories(app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=50.00, payer=user.email, group_id=group.id, category="Food", expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        categories = ExpenseReportService.get_available_categories(user.id)
        assert "Food" in categories

def test_get_monthly_expenses_with_filters(app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=50.00, payer=user.email, group_id=group.id, category="Food", expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        report = ExpenseReportService.get_monthly_expenses(user.id, 2024, 1, group_ids=[group.id], category="Food")
        assert len(report["expenses"]) == 1


def test_get_monthly_expenses_permission_check(app):
    """Test that users can only see expenses from their groups."""
    with app.app_context():
        user1 = User(email="user1@example.com")
        user2 = User(email="user2@example.com")
        db.session.add_all([user1, user2])
        db.session.flush()
        group = Group(name="User 2 Group", created_by_id=user2.id)
        group.members.append(user2)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="User 2 Expense", amount=100.00, payer=user2.email, group_id=group.id, expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        report = ExpenseReportService.get_monthly_expenses(user1.id, 2024, 1)
        assert len(report["expenses"]) == 0

def test_get_monthly_expenses_invalid_user(app):
    """Test get_monthly_expenses handles invalid user ID."""
    with app.app_context():
        report = ExpenseReportService.get_monthly_expenses(99999, 2024, 1)
        assert "error" in report
        assert report["error"] == "User not found"

def test_get_monthly_expenses_with_category_filter(app):
    """Test get_monthly_expenses with category filter."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense1 = Expense(description="Food", amount=50.00, payer=user.email, group_id=group.id, category="Food", expense_date=date(2024, 1, 15))
        expense2 = Expense(description="Transport", amount=30.00, payer=user.email, group_id=group.id, category="Transport", expense_date=date(2024, 1, 20))
        db.session.add_all([expense1, expense2])
        db.session.commit()
        report = ExpenseReportService.get_monthly_expenses(user.id, 2024, 1, category="Food")
        assert len(report["expenses"]) == 1
        assert report["expenses"][0]["category"] == "Food"

def test_generate_pdf_empty_expenses(app):
    """Test PDF generation handles empty expense list."""
    with app.app_context():
        report_data = {"filters": {"year": 2024, "month": 1}, "summary": {"total_expenses": 0, "total_amount": 0.0, "by_category": {}, "by_group": {}}, "expenses": []}
        pdf_content = ExpenseReportService.generate_pdf(report_data)
        assert pdf_content is not None
        assert pdf_content[:4] == b"%PDF"

def test_csv_includes_filters_in_header(app):
    """Test CSV includes filter information in header."""
    with app.app_context():
        report_data = {"filters": {"year": 2024, "month": 1, "category": "Food", "group_ids": [1, 2]}, "summary": {"total_expenses": 0, "total_amount": 0.0, "by_category": {}, "by_group": {}}, "expenses": []}
        csv_content = ExpenseReportService.generate_csv(report_data)
        csv_str = csv_content.decode("utf-8")
        assert "Category Filter: Food" in csv_str
        assert "Group Filter: 1, 2" in csv_str

def test_validate_date_range_invalid_year(app):
    """Test validate_date_range rejects invalid year."""
    with app.app_context():
        is_valid, error = ExpenseReportService.validate_date_range(1999, 6)
        assert is_valid is False
        assert "Year must be between" in error

def test_get_available_categories_no_groups(app):
    """Test get_available_categories when user has no groups."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        categories = ExpenseReportService.get_available_categories(user.id)
        assert len(categories) == 0

def test_get_monthly_expenses_unauthorized_group_filter(app):
    """Test filtering by groups user doesn't have access to."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()
        report = ExpenseReportService.get_monthly_expenses(user.id, 2024, 1, group_ids=[999])
        assert len(report["expenses"]) == 0
