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
