from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Expense, User

# === User Model Tests ===


def test_user_create_with_email(app):
    """Test that User model can be created with email."""
    # Arrange
    user = User(email="test@example.com")

    # Act
    db.session.add(user)
    db.session.commit()

    # Assert
    stored = User.query.first()
    assert stored is not None
    assert stored.email == "test@example.com"
    assert stored.otp is None
    assert stored.otp_expiry is None


def test_user_email_is_unique(app):
    """Test that User model enforces unique email constraint."""
    # Arrange
    user1 = User(email="test@example.com")
    user2 = User(email="test@example.com")

    # Act
    db.session.add(user1)
    db.session.commit()
    db.session.add(user2)

    # Assert
    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_user_can_store_otp(app):
    """Test that User model can store OTP and expiry."""
    # Arrange
    user = User(email="test@example.com")
    user.otp = "123456"
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Act
    db.session.add(user)
    db.session.commit()

    # Assert
    stored = User.query.first()
    assert stored.otp == "123456"
    assert stored.otp_expiry is not None


def test_user_otp_is_valid_within_expiry(app):
    """Test that OTP is valid if not expired."""
    # Arrange
    user = User(email="test@example.com")
    user.otp = "123456"
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.add(user)
    db.session.commit()

    # Act
    is_valid = user.is_otp_valid("123456")

    # Assert
    assert is_valid is True


def test_user_otp_is_invalid_if_expired(app):
    """Test that OTP is invalid if expired."""
    # Arrange
    user = User(email="test@example.com")
    user.otp = "123456"
    user.otp_expiry = datetime.now(timezone.utc) - timedelta(minutes=1)  # Expired
    db.session.add(user)
    db.session.commit()

    # Act
    is_valid = user.is_otp_valid("123456")

    # Assert
    assert is_valid is False


def test_user_otp_is_invalid_if_wrong_code(app):
    """Test that OTP is invalid if code doesn't match."""
    # Arrange
    user = User(email="test@example.com")
    user.otp = "123456"
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.add(user)
    db.session.commit()

    # Act
    is_valid = user.is_otp_valid("999999")

    # Assert
    assert is_valid is False


# === Expense Model Tests ===


def test_expense_create_and_persist(app):
    """Test that Expense model can be created and persisted to the database."""
    # Arrange
    expense = Expense(description="Lunch", amount=15.50, payer="Sam", participants="Sam, Alex")

    # Act
    db.session.add(expense)
    db.session.commit()

    # Assert
    stored = Expense.query.first()
    assert stored is not None
    assert stored.description == "Lunch"
    assert stored.amount == 15.50
    assert stored.payer == "Sam"


def test_expense_requires_amount(app):
    """Test that Expense model raises IntegrityError when amount is None."""
    # Arrange
    expense = Expense(description="Dinner", amount=None, payer="Alex")
    db.session.add(expense)

    # Act & Assert
    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_expense_requires_description(app):
    """Test that Expense model raises IntegrityError when description is None."""
    # Arrange
    expense = Expense(description=None, amount=20.00, payer="Jordan")
    db.session.add(expense)

    # Act & Assert
    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()
