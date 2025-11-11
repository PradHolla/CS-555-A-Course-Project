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


# === Percentage Split Tests ===


def test_calculate_percentage_split_valid_percentages(app):
    """Test percentage split with valid percentages that sum to 100."""
    from services.expense_service import ExpenseService

    # Arrange
    percentages = {"alice@test.com": 50.0, "bob@test.com": 30.0, "charlie@test.com": 20.0}
    total_amount = 100.0

    # Act
    result = ExpenseService.calculate_percentage_split(percentages, total_amount)

    # Assert
    assert result == {
        "alice@test.com": 50.0,
        "bob@test.com": 30.0,
        "charlie@test.com": 20.0,
    }


def test_calculate_percentage_split_empty_percentages(app):
    """Test percentage split with empty percentages dict."""
    from services.expense_service import ExpenseService

    # Act
    result = ExpenseService.calculate_percentage_split({}, 100.0)

    # Assert
    assert result == {}


def test_calculate_percentage_split_fractional_amounts(app):
    """Test percentage split resulting in fractional dollar amounts."""
    from services.expense_service import ExpenseService

    # Arrange
    percentages = {"alice@test.com": 33.33, "bob@test.com": 33.33, "charlie@test.com": 33.34}
    total_amount = 90.0

    # Act
    result = ExpenseService.calculate_percentage_split(percentages, total_amount)

    # Assert
    assert abs(result["alice@test.com"] - 29.997) < 0.01
    assert abs(result["bob@test.com"] - 29.997) < 0.01
    assert abs(result["charlie@test.com"] - 30.006) < 0.01


def test_validate_percentage_split_valid(app):
    """Test validation of valid percentage split."""
    from services.expense_service import ExpenseService

    # Arrange
    percentages = {"alice@test.com": 50.0, "bob@test.com": 50.0}

    # Act
    is_valid, error_msg = ExpenseService.validate_percentage_split(percentages)

    # Assert
    assert is_valid
    assert error_msg is None


def test_validate_percentage_split_not_100_percent(app):
    """Test validation fails when percentages don't sum to 100."""
    from services.expense_service import ExpenseService

    # Arrange
    percentages = {"alice@test.com": 50.0, "bob@test.com": 40.0}  # Only 90%

    # Act
    is_valid, error_msg = ExpenseService.validate_percentage_split(percentages)

    # Assert
    assert not is_valid
    assert "must sum to 100%" in error_msg


def test_validate_percentage_split_empty(app):
    """Test validation fails with empty percentages."""
    from services.expense_service import ExpenseService

    # Act
    is_valid, error_msg = ExpenseService.validate_percentage_split({})

    # Assert
    assert not is_valid
    assert "No participants specified" in error_msg


def test_validate_percentage_split_negative_percentage(app):
    """Test validation fails with negative percentage."""
    from services.expense_service import ExpenseService

    # Arrange
    percentages = {"alice@test.com": 120.0, "bob@test.com": -20.0}

    # Act
    is_valid, error_msg = ExpenseService.validate_percentage_split(percentages)

    # Assert
    assert not is_valid
    assert "negative" in error_msg.lower()


def test_validate_percentage_split_over_100_percent(app):
    """Test validation fails when percentages exceed 100."""
    from services.expense_service import ExpenseService

    # Arrange
    percentages = {"alice@test.com": 60.0, "bob@test.com": 50.0}  # 110%

    # Act
    is_valid, error_msg = ExpenseService.validate_percentage_split(percentages)

    # Assert
    assert not is_valid
    assert "must sum to 100%" in error_msg


# === Shares Split Tests ===


def test_calculate_shares_split_valid_shares(app):
    """Test shares split with valid share numbers."""
    from services.expense_service import ExpenseService

    # Arrange
    shares = {"alice@test.com": 2, "bob@test.com": 1, "charlie@test.com": 1}
    total_amount = 100.0

    # Act
    result = ExpenseService.calculate_shares_split(shares, total_amount)

    # Assert
    assert result["alice@test.com"] == 50.0  # 2/4 of 100
    assert result["bob@test.com"] == 25.0  # 1/4 of 100
    assert result["charlie@test.com"] == 25.0  # 1/4 of 100


def test_calculate_shares_split_empty_shares(app):
    """Test shares split with empty shares dict."""
    from services.expense_service import ExpenseService

    # Act
    result = ExpenseService.calculate_shares_split({}, 100.0)

    # Assert
    assert result == {}


def test_calculate_shares_split_fractional_amounts(app):
    """Test shares split resulting in fractional dollar amounts."""
    from services.expense_service import ExpenseService

    # Arrange
    shares = {"alice@test.com": 1, "bob@test.com": 1, "charlie@test.com": 1}
    total_amount = 100.0

    # Act
    result = ExpenseService.calculate_shares_split(shares, total_amount)

    # Assert
    assert abs(result["alice@test.com"] - 33.333333333333336) < 0.01
    assert abs(result["bob@test.com"] - 33.333333333333336) < 0.01
    assert abs(result["charlie@test.com"] - 33.333333333333336) < 0.01


def test_calculate_shares_split_unequal_shares(app):
    """Test shares split with very unequal share distribution."""
    from services.expense_service import ExpenseService

    # Arrange
    shares = {"alice@test.com": 5, "bob@test.com": 1}
    total_amount = 60.0

    # Act
    result = ExpenseService.calculate_shares_split(shares, total_amount)

    # Assert
    assert result["alice@test.com"] == 50.0  # 5/6 of 60
    assert result["bob@test.com"] == 10.0  # 1/6 of 60


def test_validate_shares_split_valid(app):
    """Test validation of valid shares split."""
    from services.expense_service import ExpenseService

    # Arrange
    shares = {"alice@test.com": 2, "bob@test.com": 1}

    # Act
    is_valid, error_msg = ExpenseService.validate_shares_split(shares)

    # Assert
    assert is_valid
    assert error_msg is None


def test_validate_shares_split_empty(app):
    """Test validation fails with empty shares."""
    from services.expense_service import ExpenseService

    # Act
    is_valid, error_msg = ExpenseService.validate_shares_split({})

    # Assert
    assert not is_valid
    assert "No participants specified" in error_msg


def test_validate_shares_split_negative_shares(app):
    """Test validation fails with negative shares."""
    from services.expense_service import ExpenseService

    # Arrange
    shares = {"alice@test.com": 2, "bob@test.com": -1}

    # Act
    is_valid, error_msg = ExpenseService.validate_shares_split(shares)

    # Assert
    assert not is_valid
    assert "positive" in error_msg.lower()


def test_validate_shares_split_zero_shares(app):
    """Test validation fails with zero shares."""
    from services.expense_service import ExpenseService

    # Arrange
    shares = {"alice@test.com": 2, "bob@test.com": 0}

    # Act
    is_valid, error_msg = ExpenseService.validate_shares_split(shares)

    # Assert
    assert not is_valid
    assert "positive" in error_msg.lower()


# === Detailed Breakdown Tests ===


def test_calculate_detailed_breakdown_with_single_expense(app):
    """Test detailed breakdown with one expense."""
    from extensions import db
    from services.expense_service import ExpenseService

    # Arrange - Alice paid $30 for lunch split equally among Alice, Bob, Charlie
    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="alice@test.com",
        split_type="equal",
        split_details='{"alice@test.com": 10.0, "bob@test.com": 10.0, "charlie@test.com": 10.0}',
    )
    db.session.add(expense)
    db.session.commit()

    # Act
    breakdown = ExpenseService.calculate_detailed_breakdown([expense])

    # Assert
    # Bob owes Alice $10, Charlie owes Alice $10 (Alice doesn't owe herself)
    assert len(breakdown) == 2
    assert {"from": "bob@test.com", "to": "alice@test.com", "amount": 10.0} in [
        {k: v for k, v in t.items() if k in ["from", "to", "amount"]} for t in breakdown
    ]
    assert {"from": "charlie@test.com", "to": "alice@test.com", "amount": 10.0} in [
        {k: v for k, v in t.items() if k in ["from", "to", "amount"]} for t in breakdown
    ]
    # Check expense description is included
    assert all(t["expense_description"] == "Lunch" for t in breakdown)


def test_calculate_detailed_breakdown_with_multiple_expenses(app):
    """Test detailed breakdown with multiple expenses."""
    from extensions import db
    from services.expense_service import ExpenseService

    # Arrange
    expense1 = Expense(
        description="Lunch",
        amount=30.0,
        payer="alice@test.com",
        split_type="equal",
        split_details='{"alice@test.com": 10.0, "bob@test.com": 10.0, "charlie@test.com": 10.0}',
    )
    expense2 = Expense(
        description="Dinner",
        amount=60.0,
        payer="bob@test.com",
        split_type="equal",
        split_details='{"alice@test.com": 20.0, "bob@test.com": 20.0, "charlie@test.com": 20.0}',
    )
    db.session.add_all([expense1, expense2])
    db.session.commit()

    # Act
    breakdown = ExpenseService.calculate_detailed_breakdown([expense1, expense2])

    # Assert
    # From expense1: Bob->Alice $10, Charlie->Alice $10
    # From expense2: Alice->Bob $20, Charlie->Bob $20
    # Total: 4 debt transactions
    assert len(breakdown) == 4

    # Check all transactions exist
    transactions = [
        {k: v for k, v in t.items() if k in ["from", "to", "amount", "expense_description"]}
        for t in breakdown
    ]
    assert {
        "from": "bob@test.com",
        "to": "alice@test.com",
        "amount": 10.0,
        "expense_description": "Lunch",
    } in transactions
    assert {
        "from": "charlie@test.com",
        "to": "alice@test.com",
        "amount": 10.0,
        "expense_description": "Lunch",
    } in transactions
    assert {
        "from": "alice@test.com",
        "to": "bob@test.com",
        "amount": 20.0,
        "expense_description": "Dinner",
    } in transactions
    assert {
        "from": "charlie@test.com",
        "to": "bob@test.com",
        "amount": 20.0,
        "expense_description": "Dinner",
    } in transactions


def test_calculate_detailed_breakdown_with_empty_expenses(app):
    """Test detailed breakdown returns empty list for no expenses."""
    from services.expense_service import ExpenseService

    # Act
    breakdown = ExpenseService.calculate_detailed_breakdown([])

    # Assert
    assert breakdown == []


def test_calculate_detailed_breakdown_excludes_payer(app):
    """Test that payer is not included in their own debt list."""
    from extensions import db
    from services.expense_service import ExpenseService

    # Arrange
    expense = Expense(
        description="Coffee",
        amount=15.0,
        payer="alice@test.com",
        split_type="equal",
        split_details='{"alice@test.com": 5.0, "bob@test.com": 5.0, "charlie@test.com": 5.0}',
    )
    db.session.add(expense)
    db.session.commit()

    # Act
    breakdown = ExpenseService.calculate_detailed_breakdown([expense])

    # Assert
    # Only Bob and Charlie owe Alice (Alice doesn't owe herself)
    assert len(breakdown) == 2
    assert not any(t["from"] == "alice@test.com" and t["to"] == "alice@test.com" for t in breakdown)


def test_calculate_detailed_breakdown_with_percentage_split(app):
    """Test detailed breakdown with percentage-based split."""
    from extensions import db
    from services.expense_service import ExpenseService

    # Arrange - Alice paid $100, split 60% Bob, 40% Charlie
    expense = Expense(
        description="Groceries",
        amount=100.0,
        payer="alice@test.com",
        split_type="percentage",
        split_details='{"bob@test.com": 60.0, "charlie@test.com": 40.0}',
    )
    db.session.add(expense)
    db.session.commit()

    # Act
    breakdown = ExpenseService.calculate_detailed_breakdown([expense])

    # Assert
    assert len(breakdown) == 2
    assert {"from": "bob@test.com", "to": "alice@test.com", "amount": 60.0} in [
        {k: v for k, v in t.items() if k in ["from", "to", "amount"]} for t in breakdown
    ]
    assert {"from": "charlie@test.com", "to": "alice@test.com", "amount": 40.0} in [
        {k: v for k, v in t.items() if k in ["from", "to", "amount"]} for t in breakdown
    ]
