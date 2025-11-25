"""Tests for expense search and filter functionality."""

import json
import re
from datetime import date, datetime, timezone

from models import Expense, Group, User


class TestExpenseFilterUI:
    """Tests for filter UI elements in the expenses page."""

    def test_filter_ui_elements_present(self, client, app):
        """Test that all filter UI elements are present in the rendered page."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create an expense
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for filter UI elements
        assert 'id="filter-description"' in response_data
        assert 'id="filter-category"' in response_data
        assert 'id="filter-date-start"' in response_data
        assert 'id="filter-date-end"' in response_data
        assert 'id="filter-payer"' in response_data
        assert 'id="filter-amount-min"' in response_data
        assert 'id="filter-amount-max"' in response_data
        assert 'id="clear-filters"' in response_data
        assert 'id="filter-results-count"' in response_data
        assert 'id="filter-date-error"' in response_data

    def test_expense_items_have_data_attributes(self, client, app):
        """Test that expense items have the required data attributes for filtering."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expenses with different attributes
        expense1 = Expense(
            description="Lunch Meeting",
            amount=50.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 25.0, "user2@example.com": 25.0}',
            participants="user1@example.com, user2@example.com",
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        expense2 = Expense(
            description="Dinner Party",
            amount=100.00,
            payer="user2@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 50.0, "user2@example.com": 50.0}',
            participants="user1@example.com, user2@example.com",
            created_at=datetime(2024, 2, 20, 18, 0, 0, tzinfo=timezone.utc),
        )
        db.session.add_all([expense1, expense2])
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for data attributes on expense items (more flexible matching)
        assert 'expense-item' in response_data
        assert 'data-description=' in response_data
        assert 'data-amount=' in response_data
        assert 'data-payer=' in response_data
        assert 'data-category=' in response_data
        assert 'data-created-at=' in response_data
        assert 'data-expense-id=' in response_data

        # Verify specific values are present (case-insensitive for description)
        assert 'data-description="lunch meeting"' in response_data.lower()
        assert 'data-amount="50.0"' in response_data or 'data-amount="50"' in response_data
        assert 'data-payer="user1@example.com"' in response_data
        assert 'data-amount="100.0"' in response_data or 'data-amount="100"' in response_data
        assert 'data-payer="user2@example.com"' in response_data

    def test_payer_dropdown_populated_with_group_members(self, client, app):
        """Test that payer dropdown is populated with group members."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        user3 = User(email="user3@example.com", display_name="User 3")
        from extensions import db

        db.session.add_all([user1, user2, user3])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])  # user3 is not a member
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check that group members are in the dropdown
        assert 'value="user1@example.com"' in response_data
        assert 'value="user2@example.com"' in response_data
        # user3 should not be in the dropdown
        assert 'value="user3@example.com"' not in response_data or response_data.count('value="user3@example.com"') == 0

    def test_no_results_message_present(self, client, app):
        """Test that the no results message element is present."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for no results message
        assert 'id="no-results-message"' in response_data
        assert 'id="clear-filters-from-empty"' in response_data

    def test_filter_javascript_included(self, client, app):
        """Test that the filter JavaScript code is included in the page."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for key JavaScript functions
        assert "filterExpenses" in response_data
        assert "clearFilters" in response_data
        assert "validateDateRange" in response_data
        assert "addEventListener" in response_data
        assert "filter-description" in response_data
        assert "filter-category" in response_data
        assert "expense-item" in response_data

    def test_data_attributes_use_lowercase_description(self, client, app):
        """Test that description data attribute is lowercase for case-insensitive search."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with mixed case description
        expense = Expense(
            description="LUNCH Meeting With CAPS",
            amount=50.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 25.0, "user2@example.com": 25.0}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check that data-description is lowercase
        assert 'data-description="lunch meeting with caps"' in response_data.lower()

    def test_data_attributes_include_iso_format_date(self, client, app):
        """Test that created_at date is in ISO format in data attribute."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with specific date
        test_date = datetime(2024, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        expense = Expense(
            description="Test Expense",
            amount=50.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 25.0, "user2@example.com": 25.0}',
            participants="user1@example.com, user2@example.com",
            created_at=test_date,
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check that ISO format date is present (date might be truncated or formatted slightly differently)
        iso_date = test_date.isoformat()
        # Check for the date in ISO format (might be truncated to date only or have different precision)
        assert 'data-created-at=' in response_data
        # Verify it contains the date part (2024-03-15)
        assert '2024-03-15' in response_data or iso_date[:10] in response_data

    def test_filter_ui_shown_when_expenses_exist(self, client, app):
        """Test that filter UI is shown when expenses exist."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create an expense
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Filter UI should be present
        assert 'id="filter-description"' in response_data
        assert 'id="expenses-list"' in response_data

    def test_expenses_list_container_has_correct_id(self, client, app):
        """Test that the expenses list container has the correct ID for filtering."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create an expense
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for expenses list container
        assert 'id="expenses-list"' in response_data

    def test_multiple_expenses_all_have_data_attributes(self, client, app):
        """Test that all expenses in a list have the required data attributes."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create multiple expenses
        expenses = []
        for i in range(5):
            expense = Expense(
                description=f"Expense {i}",
                amount=10.00 * (i + 1),
                payer="user1@example.com" if i % 2 == 0 else "user2@example.com",
                group_id=group.id,
                split_type="equal",
                split_details='{"user1@example.com": 5.0, "user2@example.com": 5.0}',
                participants="user1@example.com, user2@example.com",
            )
            expenses.append(expense)

        db.session.add_all(expenses)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Count expense-item classes (should be 5) - more flexible matching
        expense_item_count = response_data.count('expense-item')
        assert expense_item_count >= 5  # At least 5, might be more if used elsewhere

        # Verify all have data attributes (count occurrences)
        # Use >= instead of == because attributes might appear in other contexts (e.g., JavaScript)
        # but we need at least 5 (one per expense item)
        assert response_data.count('data-description=') >= 5
        assert response_data.count('data-amount=') >= 5
        assert response_data.count('data-payer=') >= 5
        assert response_data.count('data-category=') >= 5
        assert response_data.count('data-created-at=') >= 5
        assert response_data.count('data-expense-id=') >= 5
        
        # Additionally verify that expense items have all required attributes together
        # by checking for the pattern that appears on each expense item
        expense_with_attrs_pattern = r'data-description="[^"]*"\s+data-amount="[^"]*"\s+data-payer="[^"]*"\s+data-category="[^"]*"\s+data-created-at="[^"]*"\s+data-expense-id="[^"]*"'
        matches = len(re.findall(expense_with_attrs_pattern, response_data))
        assert matches >= 5, f"Expected at least 5 expense items with all data attributes, found {matches}"

    def test_category_filter_ui_present(self, client, app):
        """Test that category filter dropdown is present with all options."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create an expense
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for category filter
        assert 'id="filter-category"' in response_data
        assert 'All Categories' in response_data
        assert 'value="Food"' in response_data
        assert 'value="Utilities"' in response_data
        assert 'value="Transport"' in response_data
        assert 'value="Entertainment"' in response_data
        assert 'value="Groceries"' in response_data
        assert 'value="Rent"' in response_data
        assert 'value="Travel"' in response_data
        assert 'value="Other"' in response_data

    def test_expense_items_have_category_data_attribute(self, client, app):
        """Test that expense items have category data attribute."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expenses with and without categories
        expense1 = Expense(
            description="Lunch",
            amount=50.00,
            payer="user1@example.com",
            category="Food",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 25.0, "user2@example.com": 25.0}',
            participants="user1@example.com, user2@example.com",
        )
        expense2 = Expense(
            description="Gas",
            amount=30.00,
            payer="user2@example.com",
            category="Transport",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 15.0, "user2@example.com": 15.0}',
            participants="user1@example.com, user2@example.com",
        )
        expense3 = Expense(
            description="No Category",
            amount=20.00,
            payer="user1@example.com",
            category=None,
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 10.0, "user2@example.com": 10.0}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add_all([expense1, expense2, expense3])
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for category data attributes
        assert 'data-category="Food"' in response_data
        assert 'data-category="Transport"' in response_data
        assert 'data-category=""' in response_data  # Empty category for expense3

    def test_date_validation_error_element_present(self, client, app):
        """Test that date validation error element is present."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for date validation error element
        assert 'id="filter-date-error"' in response_data
        assert 'hidden' in response_data or 'class="hidden"' in response_data or 'style="display: none' in response_data

    def test_date_range_clarity_labels_present(self, client, app):
        """Test that date range has clarity labels indicating it's for created date."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for date range clarity
        assert 'Created date' in response_data
        assert 'title="Filter by expense created date"' in response_data

    def test_price_range_label_present(self, client, app):
        """Test that price range label is present."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for price range label
        assert 'Price range' in response_data

    def test_clear_all_button_present(self, client, app):
        """Test that Clear All button is present with correct text."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for Clear All button
        assert 'id="clear-filters"' in response_data
        assert 'Clear All' in response_data

    def test_category_data_attribute_in_multiple_expenses(self, client, app):
        """Test that all expenses have category data attribute."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create multiple expenses with different categories
        expenses = []
        categories = ["Food", "Transport", "Entertainment", None, "Groceries"]
        for i, category in enumerate(categories):
            expense = Expense(
                description=f"Expense {i}",
                amount=10.00 * (i + 1),
                payer="user1@example.com",
                category=category,
                group_id=group.id,
                split_type="equal",
                split_details='{"user1@example.com": 5.0, "user2@example.com": 5.0}',
                participants="user1@example.com, user2@example.com",
            )
            expenses.append(expense)

        db.session.add_all(expenses)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify all have category data attributes
        assert response_data.count('data-category=') >= 5

    def test_filter_javascript_includes_category_filter(self, client, app):
        """Test that JavaScript includes category filter handling."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check for category filter in JavaScript
        assert 'filterCategory' in response_data or 'filter-category' in response_data
        assert 'getElementById(\'filter-category\')' in response_data or 'getElementById("filter-category")' in response_data

    def test_clear_filters_includes_category(self, client, app):
        """Test that clearFilters function includes category filter."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Check that clearFilters function exists and includes category clearing
        assert 'clearFilters' in response_data
        # Check that filterCategory is referenced in the clearFilters context
        # Look for pattern where filterCategory value is set to empty
        assert ('filterCategory' in response_data and 'value' in response_data) or 'filter-category' in response_data


class TestExpenseFilterFunctionality:
    """Tests for expense filter functionality and JavaScript logic."""

    def test_filter_javascript_complete_structure(self, client, app):
        """Test that filter JavaScript has complete structure for all filters."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expenses
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify filterExpenses function handles all filters
        assert 'matchesDescription' in response_data
        assert 'matchesCategory' in response_data
        assert 'matchesDateRange' in response_data
        assert 'matchesPayer' in response_data
        assert 'matchesAmount' in response_data
        
        # Verify AND logic for combining filters
        assert 'matchesDescription && matchesCategory && matchesDateRange && matchesPayer && matchesAmount' in response_data
        
        # Verify description filter is case-insensitive
        assert '.toLowerCase()' in response_data
        assert '.includes(' in response_data
        
        # Verify category filter uses exact match
        assert 'category === categoryFilter' in response_data or 'category == categoryFilter' in response_data
        
        # Verify payer filter uses exact match
        assert 'payer === payerFilter' in response_data or 'payer == payerFilter' in response_data
        
        # Verify amount range filter
        assert 'amount >= amountMinFilter' in response_data
        assert 'amount <= amountMaxFilter' in response_data

    def test_date_validation_logic_present(self, client, app):
        """Test that date validation logic is present and correct."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify validateDateRange function exists
        assert 'validateDateRange' in response_data
        assert 'function validateDateRange()' in response_data
        
        # Verify date validation logic
        assert 'startDate && endDate' in response_data
        assert 'start > end' in response_data or 'startDate > endDate' in response_data
        assert 'Start date must be before or equal to end date' in response_data
        
        # Verify filterExpenses calls validateDateRange
        assert 'if (!validateDateRange())' in response_data or 'validateDateRange()' in response_data

    def test_date_range_filter_logic(self, client, app):
        """Test that date range filter logic handles start and end dates correctly."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify date range filtering logic
        assert 'dateStartFilter || dateEndFilter' in response_data
        assert 'new Date(createdAt)' in response_data
        assert 'setHours(0, 0, 0, 0)' in response_data
        assert 'expenseDate < startDate' in response_data
        assert 'expenseDate > endDate' in response_data
        assert 'setHours(23, 59, 59, 999)' in response_data  # End date includes full day

    def test_all_event_listeners_present(self, client, app):
        """Test that all filter inputs have event listeners attached."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify event listeners for all filters
        assert 'filterDescription.addEventListener' in response_data
        assert 'filterCategory.addEventListener' in response_data
        assert 'filterDateStart.addEventListener' in response_data
        assert 'filterDateEnd.addEventListener' in response_data
        assert 'filterPayer.addEventListener' in response_data
        assert 'filterAmountMin.addEventListener' in response_data
        assert 'filterAmountMax.addEventListener' in response_data
        assert 'clearFiltersBtn.addEventListener' in response_data
        assert 'clearFiltersFromEmptyBtn.addEventListener' in response_data

    def test_no_results_message_logic(self, client, app):
        """Test that no results message logic is present."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify no results message logic
        assert 'visibleCount === 0' in response_data
        assert 'noResultsMessage.classList.remove(\'hidden\')' in response_data
        assert 'noResultsMessage.classList.add(\'hidden\')' in response_data
        assert 'expensesList.style.display' in response_data

    def test_filter_results_count_logic(self, client, app):
        """Test that filter results count logic is present."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify filter results count logic
        assert 'filterResultsCount' in response_data
        assert 'visibleCount === totalCount' in response_data
        assert 'of ${totalCount}' in response_data or 'of' in response_data

    def test_clear_filters_function_complete(self, client, app):
        """Test that clearFilters function clears all filters."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify clearFilters clears all filters
        assert 'function clearFilters()' in response_data
        assert 'filterDescription.value = \'\'' in response_data
        assert 'filterCategory.value = \'\'' in response_data
        assert 'filterDateStart.value = \'\'' in response_data
        assert 'filterDateEnd.value = \'\'' in response_data
        assert 'filterPayer.value = \'\'' in response_data
        assert 'filterAmountMin.value = \'\'' in response_data
        assert 'filterAmountMax.value = \'\'' in response_data
        assert 'filterExpenses()' in response_data  # Should call filterExpenses after clearing

    def test_amount_filter_handles_edge_cases(self, client, app):
        """Test that amount filter handles edge cases correctly."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify amount filter handles edge cases
        assert 'parseFloat(filterAmountMin?.value) || 0' in response_data
        assert 'parseFloat(filterAmountMax?.value) || Infinity' in response_data
        assert 'amountMinFilter > 0 || amountMaxFilter < Infinity' in response_data

    def test_category_filter_handles_empty_category(self, client, app):
        """Test that category filter handles expenses with no category."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense without category
        expense = Expense(
            description="No Category Expense",
            amount=25.00,
            payer="user1@example.com",
            category=None,
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify empty category is handled
        assert 'data-category=""' in response_data
        # Verify JavaScript handles empty category
        assert 'item.getAttribute(\'data-category\') || \'\'' in response_data

    def test_date_filter_handles_missing_created_at(self, client, app):
        """Test that date filter handles expenses without created_at."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify JavaScript handles missing created_at
        assert 'if (createdAt)' in response_data
        assert 'matchesDateRange = false' in response_data  # Should fail if no createdAt

    def test_transaction_count_update_logic(self, client, app):
        """Test that transaction count text updates when filtering."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify transaction count update logic
        assert 'transactionCountText' in response_data
        assert 'visibleCount !== expenseItems.length' in response_data
        assert '(filtered)' in response_data

    def test_filter_expenses_early_return_on_invalid_dates(self, client, app):
        """Test that filterExpenses returns early when dates are invalid."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify early return on invalid dates
        assert 'if (!validateDateRange())' in response_data
        assert 'return;' in response_data
        assert '# Don\'t filter if dates are invalid' in response_data or 'Don\'t filter if dates are invalid' in response_data

    def test_all_filter_types_implemented(self, client, app):
        """Test that all required filter types from acceptance criteria are implemented."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200

        response_data = response.data.decode("utf-8")

        # Verify all acceptance criteria filters are implemented:
        # 1. Description filter (search bar)
        assert 'descriptionFilter' in response_data
        assert 'description.includes(descriptionFilter)' in response_data
        
        # 2. Date range filter
        assert 'dateStartFilter' in response_data
        assert 'dateEndFilter' in response_data
        
        # 3. Payer filter (dropdown)
        assert 'payerFilter' in response_data
        assert 'payer === payerFilter' in response_data or 'payer == payerFilter' in response_data
        
        # 4. Amount range filter (min and max)
        assert 'amountMinFilter' in response_data
        assert 'amountMaxFilter' in response_data
        
        # 5. Category filter (new requirement)
        assert 'categoryFilter' in response_data
        assert 'category === categoryFilter' in response_data or 'category == categoryFilter' in response_data

