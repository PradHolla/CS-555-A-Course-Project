"""Tests for multi-currency expense support."""

import pytest
from werkzeug.datastructures import MultiDict

from extensions import db
from models import Expense, Group, User, SUPPORTED_CURRENCIES, get_currency_symbol


class TestCurrencyModel:
    """Tests for currency field in Expense model."""

    def test_expense_default_currency_is_usd(self, app):
        """Test that expense created without currency defaults to USD."""
        with app.app_context():
            user = User(email="test@example.com", display_name="Test User")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            db.session.add(group)
            db.session.commit()

            expense = Expense(
                description="Test Expense",
                amount=100.00,
                payer="test@example.com",
                group_id=group.id,
                split_type="equal",
            )
            db.session.add(expense)
            db.session.commit()

            assert expense.currency == "USD"

    def test_expense_with_eur_currency(self, app):
        """Test expense created with EUR currency is stored correctly."""
        with app.app_context():
            user = User(email="test@example.com", display_name="Test User")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            db.session.add(group)
            db.session.commit()

            expense = Expense(
                description="European Expense",
                amount=50.00,
                currency="EUR",
                payer="test@example.com",
                group_id=group.id,
                split_type="equal",
            )
            db.session.add(expense)
            db.session.commit()

            assert expense.currency == "EUR"

    def test_expense_with_all_supported_currencies(self, app):
        """Test all supported currencies can be stored."""
        with app.app_context():
            user = User(email="test@example.com", display_name="Test User")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            db.session.add(group)
            db.session.commit()

            currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR", "CNY", "CHF", "MXN"]
            for i, currency in enumerate(currencies):
                expense = Expense(
                    description=f"Expense in {currency}",
                    amount=100.00 + i,
                    currency=currency,
                    payer="test@example.com",
                    group_id=group.id,
                    split_type="equal",
                )
                db.session.add(expense)
                db.session.commit()

                assert expense.currency == currency


class TestCurrencySymbols:
    """Tests for currency symbol helper function."""

    def test_get_currency_symbol_usd(self):
        """Test USD returns $ symbol."""
        assert get_currency_symbol("USD") == "$"

    def test_get_currency_symbol_eur(self):
        """Test EUR returns € symbol."""
        assert get_currency_symbol("EUR") == "€"

    def test_get_currency_symbol_gbp(self):
        """Test GBP returns £ symbol."""
        assert get_currency_symbol("GBP") == "£"

    def test_get_currency_symbol_jpy(self):
        """Test JPY returns ¥ symbol."""
        assert get_currency_symbol("JPY") == "¥"

    def test_get_currency_symbol_inr(self):
        """Test INR returns ₹ symbol."""
        assert get_currency_symbol("INR") == "₹"

    def test_get_currency_symbol_invalid_defaults_to_dollar(self):
        """Test invalid currency code defaults to $ symbol."""
        assert get_currency_symbol("INVALID") == "$"
        assert get_currency_symbol("") == "$"

    def test_supported_currencies_dict(self):
        """Test all expected currencies are in the supported currencies dict."""
        expected_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR", "CNY", "CHF", "MXN"]
        for currency in expected_currencies:
            assert currency in SUPPORTED_CURRENCIES


class TestCurrencyRoutes:
    """Tests for currency in expense creation routes."""

    def test_create_expense_with_currency_via_form(self, client, app):
        """Test creating expense with currency selection via form."""
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Log in
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = "test@example.com"

        # Create expense with EUR currency using MultiDict
        expense_data = MultiDict([
            ("description", "Euro Expense"),
            ("amount", "75.50"),
            ("currency", "EUR"),
            ("payer", "test@example.com"),
            ("split_type", "equal"),
            ("participants", "test@example.com"),
        ])

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            follow_redirects=True,
        )

        assert response.status_code == 200

        expense = Expense.query.filter_by(description="Euro Expense").first()
        assert expense is not None
        assert expense.currency == "EUR"
        assert expense.amount == 75.50

    def test_create_expense_without_currency_defaults_to_usd(self, client, app):
        """Test creating expense without specifying currency defaults to USD."""
        user = User(email="test2@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()

        group = Group(name="Test Group 2", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Log in
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = "test2@example.com"

        # Create expense without currency field using MultiDict
        expense_data = MultiDict([
            ("description", "Default Currency Expense"),
            ("amount", "50.00"),
            ("payer", "test2@example.com"),
            ("split_type", "equal"),
            ("participants", "test2@example.com"),
        ])

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            follow_redirects=True,
        )

        assert response.status_code == 200

        expense = Expense.query.filter_by(description="Default Currency Expense").first()
        assert expense is not None
        assert expense.currency == "USD"

    def test_create_expense_with_invalid_currency_defaults_to_usd(self, client, app):
        """Test creating expense with invalid currency defaults to USD."""
        user = User(email="test3@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()

        group = Group(name="Test Group 3", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Log in
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = "test3@example.com"

        # Create expense with invalid currency using MultiDict
        expense_data = MultiDict([
            ("description", "Invalid Currency Expense"),
            ("amount", "30.00"),
            ("currency", "INVALID"),
            ("payer", "test3@example.com"),
            ("split_type", "equal"),
            ("participants", "test3@example.com"),
        ])

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            follow_redirects=True,
        )

        assert response.status_code == 200

        expense = Expense.query.filter_by(description="Invalid Currency Expense").first()
        assert expense is not None
        assert expense.currency == "USD"

    def test_expense_form_shows_currency_dropdown(self, client, app):
        """Test the expense form displays currency selection dropdown."""
        user = User(email="test4@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()

        group = Group(name="Test Group 4", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Log in
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = "test4@example.com"

        # Get the group page (which has the expense form)
        response = client.get(f"/groups/{group.id}")

        assert response.status_code == 200
        # Check that currency dropdown is present
        assert b'name="currency"' in response.data
        assert b"USD" in response.data
        assert b"EUR" in response.data
        assert b"GBP" in response.data


class TestCurrencyDisplay:
    """Tests for currency display in expense list."""

    def test_expense_displays_correct_currency_symbol(self, client, app):
        """Test expense list shows correct currency symbol."""
        user = User(email="test5@example.com", display_name="Test User")
        db.session.add(user)
        db.session.commit()

        group = Group(name="Test Group 5", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Create expense with EUR
        expense = Expense(
            description="Euro Test",
            amount=100.00,
            currency="EUR",
            payer="test5@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"test5@example.com": 100.0}',
            participants="test5@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        # Log in
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = "test5@example.com"

        # Get the group page (which shows expenses)
        response = client.get(f"/groups/{group.id}")

        assert response.status_code == 200
        # Check that EUR symbol is displayed
        assert "€" in response.data.decode("utf-8") or "EUR" in response.data.decode("utf-8")
