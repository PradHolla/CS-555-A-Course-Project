# Testing Guide

This document provides comprehensive information about testing in the SSW555 Example Project.

## Table of Contents
- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [Best Practices](#best-practices)
- [Customizing Tests](#customizing-tests)

## Overview

The project uses **pytest** as its testing framework. Tests are organized into two main categories:
- **Unit Tests**: Test individual components (models) in isolation
- **Integration Tests**: Test HTTP endpoints and form submissions

All tests use a temporary SQLite database that is created fresh for each test and automatically cleaned up.

## Test Structure

```
tests/
├── __init__.py          # Test suite documentation
├── conftest.py          # Shared pytest fixtures (app, client)
├── test_models.py       # Unit tests for database models
└── test_routes.py       # Integration tests for HTTP endpoints
```

### Test Files

#### `conftest.py`
Contains shared fixtures used across all test files:
- `app`: Flask application instance with test configuration
- `client`: Flask test client for making HTTP requests

#### `test_models.py`
Unit tests for database models:
- **Habit Model**: Creation, persistence, optional fields
- **MoodEntry Model**: Creation, required fields validation
- **Expense Model**: Creation, required fields validation
- **Recipe Model**: Creation, optional fields handling

#### `test_routes.py`
Integration tests for HTTP endpoints:
- **Habit Tracker**: GET/POST requests, data persistence
- **Mood Journal**: GET/POST requests, validation
- **Expense Splitter**: GET/POST requests, validation
- **Recipe Assistant**: GET/POST requests, edge cases
- **Parametrized Tests**: Tests that run across all modules

## Running Tests

### Basic Commands

Run all tests:
```bash
uv run pytest
```

Run with verbose output:
```bash
uv run pytest -v
```

Run specific test file:
```bash
uv run pytest tests/test_models.py
uv run pytest tests/test_routes.py
```

Run specific test:
```bash
uv run pytest tests/test_models.py::test_habit_create_and_persist
```

Run tests matching a pattern:
```bash
uv run pytest -k "habit"
uv run pytest -k "post_creates"
```

### Test Output

Successful test run example:
```
============================= test session starts ==============================
collected 25 items

tests/test_models.py::test_habit_create_and_persist PASSED               [  4%]
tests/test_routes.py::test_habit_tracker_get_returns_ok PASSED           [ 40%]
...
============================== 25 passed in 0.62s ==============================
```

## Writing Tests

### Test Naming Convention

Follow the pattern: `test_<what>_<condition>_<expected>`

Examples:
- `test_habit_tracker_get_returns_ok`
- `test_mood_journal_rejects_blank_mood`
- `test_expense_splitter_post_creates_expense`

### AAA Pattern

All tests follow the **Arrange-Act-Assert** pattern for clarity:

```python
def test_habit_tracker_post_creates_habit(client):
    """Test that POST /habit-tracker creates a new habit in the database."""
    # Arrange
    habit_data = {'name': 'Read 20 pages', 'description': 'Daily reading goal'}

    # Act
    response = client.post('/habit-tracker', data=habit_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    stored = Habit.query.filter_by(name='Read 20 pages').first()
    assert stored is not None
    assert stored.description == 'Daily reading goal'
```

### Using Fixtures

Import models and use fixtures defined in `conftest.py`:

```python
from models import Habit, MoodEntry

def test_example(app, client):
    # 'app' provides Flask application context
    # 'client' provides test client for HTTP requests
    response = client.get('/habit-tracker')
    assert response.status_code == 200
```

### Parametrized Tests

Use `@pytest.mark.parametrize` to run the same test with multiple inputs:

```python
@pytest.mark.parametrize(
    "endpoint",
    ["/habit-tracker", "/mood-journal", "/expense-splitter", "/recipe-assistant"]
)
def test_all_modules_get_returns_ok(client, endpoint):
    """Test that all module endpoints return 200 status code on GET requests."""
    response = client.get(endpoint)
    assert response.status_code == 200
```

### Testing Database Models

Example model test with validation:

```python
def test_mood_entry_requires_mood(app):
    """Test that MoodEntry model raises IntegrityError when mood is None."""
    # Arrange
    entry = MoodEntry(mood=None, notes="Forgot")
    db.session.add(entry)

    # Act & Assert
    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()
```

### Testing Routes

Example route test with form submission:

```python
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
```

## Test Coverage

### Generating Coverage Reports

Install coverage support:
```bash
uv pip install pytest-cov
```

Run tests with coverage:
```bash
uv run pytest --cov=. --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Best Practices

- Aim for **80%+ coverage** for core functionality
- Focus on testing critical paths and edge cases
- Don't chase 100% coverage at the expense of meaningful tests
- Exclude generated files and configuration from coverage reports

## Best Practices

### 1. Clear Test Names
✅ **Good**: `test_mood_journal_rejects_blank_mood`
❌ **Bad**: `test_mood_journal_2`

### 2. Use Docstrings
Every test should have a clear docstring explaining what it tests:
```python
def test_recipe_assistant_rejects_missing_ingredients(client):
    """Test that POST /recipe-assistant rejects recipes with missing required fields."""
    # ...
```

### 3. Follow AAA Pattern
Clearly separate Arrange, Act, and Assert sections with comments.

### 4. Test One Thing
Each test should verify a single behavior or condition.

### 5. Keep Tests Independent
Tests should not depend on each other or run in a specific order.

### 6. Use Descriptive Assertions
```python
# Good
assert stored.amount == 36.75
assert stored.payer == 'Alex'

# Better - with error messages
assert stored.amount == 36.75, f"Expected 36.75, got {stored.amount}"
```

### 7. Test Edge Cases
- Empty strings
- Null/None values
- Negative numbers
- Maximum values
- Invalid data types

## Customizing Tests

### When Students Remove Modules

If students decide to keep only one module (e.g., only Habit Tracker), they should:

1. **Remove unused model tests** from `test_models.py`:
   - Delete test sections for unwanted models
   - Keep only tests for the chosen module

2. **Remove unused route tests** from `test_routes.py`:
   - Delete test functions for unwanted routes
   - Update parametrized tests to include only kept endpoints

3. **Update parametrized tests**:
```python
# If keeping only Habit Tracker
@pytest.mark.parametrize("endpoint", ["/habit-tracker"])
def test_all_modules_get_returns_ok(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 200
```

4. **Run tests to verify**:
```bash
uv run pytest -v
```

### Adding New Tests

When adding new features, follow this workflow:

1. **Write the test first** (Test-Driven Development):
```python
def test_new_feature_works(client):
    """Test that new feature does what it should."""
    # Arrange
    test_data = {...}

    # Act
    response = client.post('/new-endpoint', data=test_data)

    # Assert
    assert response.status_code == 200
```

2. **Run the test** (it should fail):
```bash
uv run pytest tests/test_routes.py::test_new_feature_works
```

3. **Implement the feature** in your application code

4. **Run the test again** (it should pass)

### Example: Adding Tests for a New Module

If adding a "Goal Tracker" module:

1. Add model test in `test_models.py`:
```python
# === Goal Model Tests ===

def test_goal_create_and_persist(app):
    """Test that Goal model can be created and persisted to the database."""
    # Arrange
    goal = Goal(title="Learn Python", deadline="2025-12-31")

    # Act
    db.session.add(goal)
    db.session.commit()

    # Assert
    stored = Goal.query.first()
    assert stored is not None
    assert stored.title == "Learn Python"
```

2. Add route tests in `test_routes.py`:
```python
# === Goal Tracker Tests ===

def test_goal_tracker_get_returns_ok(client):
    """Test that GET /goal-tracker returns a 200 status code."""
    response = client.get('/goal-tracker')
    assert response.status_code == 200

def test_goal_tracker_post_creates_goal(client):
    """Test that POST /goal-tracker creates a new goal in the database."""
    goal_data = {'title': 'Learn Flask', 'deadline': '2025-12-31'}
    response = client.post('/goal-tracker', data=goal_data, follow_redirects=False)
    assert response.status_code == 302
    stored = Goal.query.filter_by(title='Learn Flask').first()
    assert stored is not None
```

3. Update parametrized test:
```python
@pytest.mark.parametrize(
    "endpoint",
    ["/habit-tracker", "/mood-journal", "/expense-splitter", "/recipe-assistant", "/goal-tracker"]
)
def test_all_modules_get_returns_ok(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 200
```

## Troubleshooting

### Common Issues

**Issue**: Tests fail with database errors
```
Solution: Ensure the app fixture is properly creating a fresh database.
Check that conftest.py is in the tests/ directory.
```

**Issue**: ImportError for models
```
Solution: Run tests from the project root directory, not from within tests/.
Ensure PYTHONPATH includes the project root.
```

**Issue**: Tests pass individually but fail together
```
Solution: Tests may have shared state. Ensure db.session.rollback()
is called in error cases and database is properly cleaned between tests.
```

### Getting Help

If you encounter testing issues:
1. Run tests with verbose output: `uv run pytest -v`
2. Check test logs for detailed error messages
3. Verify database schema matches models
4. Ensure all dependencies are installed: `uv sync`

---

For more information, see:
- [Development Guide](DEVELOPMENT.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [pytest Documentation](https://docs.pytest.org/)
