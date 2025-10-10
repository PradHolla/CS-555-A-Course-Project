import pytest
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Expense


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
