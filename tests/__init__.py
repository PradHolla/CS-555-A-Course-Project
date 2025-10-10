"""
Test suite for SSW555 Example Project.

Test Organization:
- test_models.py: Unit tests for database models (Habit, MoodEntry, Expense, Recipe)
- test_routes.py: Integration tests for HTTP endpoints and form submissions
- conftest.py: Shared pytest fixtures (app, client)

Running Tests:
    pytest                    # Run all tests
    pytest tests/test_models.py  # Run only model tests
    pytest -v                 # Verbose output
    pytest -k "habit"         # Run tests matching "habit"

Test Coverage:
    pytest --cov=. --cov-report=html
"""
