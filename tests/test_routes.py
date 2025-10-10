import pytest
from models import Expense

def test_expense_splitter_get_returns_ok(client):
    """Test that GET /expense-splitter returns a 200 status code."""
    # Act
    response = client.get('/expense-splitter')

    # Assert
    assert response.status_code == 200


def test_expense_splitter_post_creates_expense(client):
    """Test that POST /expense-splitter creates a new expense in the database."""
    # Arrange
    expense_data = {
        'description': 'Dinner',
        'amount': '36.75',
        'payer': 'Alex',
        'participants': 'Alex, Sam, Jo',
    }

    # Act
    response = client.post('/expense-splitter', data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    stored = Expense.query.filter_by(description='Dinner').first()
    assert stored is not None
    assert stored.amount == 36.75
    assert stored.payer == 'Alex'
    assert stored.participants == 'Alex, Sam, Jo'


def test_expense_splitter_rejects_invalid_amount(client):
    """Test that POST /expense-splitter rejects non-numeric amount values."""
    # Arrange
    invalid_data = {
        'description': 'Snacks',
        'amount': 'abc',
        'payer': 'Riley',
        'participants': 'Riley, Pat',
    }

    # Act
    response = client.post('/expense-splitter', data=invalid_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert Expense.query.count() == 0
