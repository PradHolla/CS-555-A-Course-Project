from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Expense, User, Group

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


# === Group Model Tests ===


def test_group_create_and_persist(app):
    """Test that Group model can be created and persisted to the database."""
    # Arrange
    group = Group(name="Team Alpha", members="Alice, Bob, Charlie")

    # Act
    db.session.add(group)
    db.session.commit()

    # Assert
    stored = Group.query.first()
    assert stored is not None
    assert stored.name == "Team Alpha"
    assert stored.members == "Alice, Bob, Charlie"


def test_group_requires_name(app):
    """Test that Group model raises IntegrityError when name is None."""
    # Arrange
    group = Group(name=None, members="Alice, Bob")
    db.session.add(group)

    # Act & Assert
    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


# === Expense-Group Relationship Tests ===


def test_expense_group_relationship(app):
    """Test that Expense can be associated with a Group."""
    # Arrange
    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()
    
    expense = Expense(
        description="Lunch", 
        amount=30.0, 
        payer="Alice",
        group_id=group.id,
        split_type="equal",
        split_details='{"Alice": 15.0, "Bob": 15.0}'
    )

    # Act
    db.session.add(expense)
    db.session.commit()

    # Assert
    stored_expense = Expense.query.first()
    assert stored_expense.group_id == group.id
    assert stored_expense.group == group
    assert expense in group.expenses


def test_expense_split_details_json_storage(app):
    """Test that split_details can store and retrieve JSON data."""
    # Arrange
    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()
    
    split_details = {"Alice": 20.0, "Bob": 10.0}
    expense = Expense(
        description="Dinner", 
        amount=30.0, 
        payer="Alice",
        group_id=group.id,
        split_type="custom",
        split_details='{"Alice": 20.0, "Bob": 10.0}'
    )

    # Act
    db.session.add(expense)
    db.session.commit()

    # Assert
    stored_expense = Expense.query.first()
    assert stored_expense.split_details == '{"Alice": 20.0, "Bob": 10.0}'
    assert stored_expense.split_type == "custom"


def test_expense_default_split_type(app):
    """Test that Expense defaults to 'equal' split_type."""
    # Arrange
    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()
    
    expense = Expense(
        description="Lunch", 
        amount=20.0, 
        payer="Alice",
        group_id=group.id
    )

    # Act
    db.session.add(expense)
    db.session.commit()

    # Assert
    stored_expense = Expense.query.first()
    assert stored_expense.split_type == "equal"


def test_group_expenses_backref(app):
    """Test that Group.expenses backref works correctly."""
    # Arrange
    group = Group(name="Test Group", members="Alice, Bob")
    db.session.add(group)
    db.session.commit()
    
    expense1 = Expense(
        description="Lunch", 
        amount=20.0, 
        payer="Alice",
        group_id=group.id
    )
    expense2 = Expense(
        description="Dinner", 
        amount=40.0, 
        payer="Bob",
        group_id=group.id
    )

    # Act
    db.session.add_all([expense1, expense2])
    db.session.commit()

    # Assert
    stored_group = Group.query.first()
    assert len(stored_group.expenses) == 2
    assert expense1 in stored_group.expenses
    assert expense2 in stored_group.expenses
