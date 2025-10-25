"""Tests for service functionality."""

from models import Expense


def test_expense_service_parse_split_details_json_error(app):
    """Covers json.loads exception path (lines 133-134)."""
    from extensions import db
    from services.expense_service import ExpenseService

    expense = Expense(
        description="Test",
        amount=10.0,
        payer="Alice",
        split_details="invalid json {",  # triggers JSONDecodeError
    )
    db.session.add(expense)
    db.session.commit()

    result = ExpenseService._parse_split_details(expense)
    assert result == {}


def test_expense_service_validate_custom_split_empty_details(app):
    """Covers empty split_details early return (line 158)."""
    from services.expense_service import ExpenseService

    is_valid, error_msg = ExpenseService.validate_custom_split({}, 50.0)
    assert not is_valid
    assert error_msg == "No participants specified"


def test_expense_service_calculate_equal_split_empty_participants(app):
    """Covers empty participants early return (line 181)."""
    from services.expense_service import ExpenseService

    result = ExpenseService.calculate_equal_split([], 50.0)
    assert result == {}
