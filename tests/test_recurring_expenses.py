"""Tests for recurring expense functionality."""

from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta

from extensions import db
from models import Expense, Group, User


class TestRecurringExpenseModel:
    """Tests for the Expense model with recurring fields."""

    def test_expense_model_has_recurring_fields(self, app):
        """Test that Expense model has all recurring expense fields."""
        with app.app_context():
            # Create a test expense with recurring fields
            expense = Expense(
                description="Monthly Rent",
                amount=1500.00,
                currency="USD",
                payer="test@example.com",
                group_id=1,
                split_type="equal",
                split_details='{"test@example.com": 750, "other@example.com": 750}',
                is_recurring=True,
                recurrence_frequency="monthly",
                recurrence_end_date=date.today() + relativedelta(months=12),
                next_occurrence=date.today() + relativedelta(months=1),
            )

            assert expense.is_recurring is True
            assert expense.recurrence_frequency == "monthly"
            assert expense.recurrence_end_date is not None
            assert expense.next_occurrence is not None

    def test_expense_default_not_recurring(self, app):
        """Test that expenses are not recurring by default."""
        with app.app_context():
            expense = Expense(
                description="Test Expense",
                amount=100.00,
                currency="USD",
                payer="test@example.com",
            )
            db.session.add(expense)
            db.session.commit()

            # After committing, defaults should be applied
            refreshed = db.session.get(Expense, expense.id)
            assert refreshed.is_recurring is False
            assert refreshed.recurrence_frequency is None
            assert refreshed.recurrence_end_date is None
            assert refreshed.next_occurrence is None

    def test_expense_parent_child_relationship(self, app):
        """Test parent-child relationship for generated recurring expenses."""
        with app.app_context():
            # Create parent recurring expense
            parent = Expense(
                description="Monthly Rent",
                amount=1500.00,
                currency="USD",
                payer="test@example.com",
                group_id=1,
                split_type="equal",
                is_recurring=True,
                recurrence_frequency="monthly",
            )
            db.session.add(parent)
            db.session.commit()

            # Create child expense
            child = Expense(
                description="Monthly Rent",
                amount=1500.00,
                currency="USD",
                payer="test@example.com",
                group_id=1,
                split_type="equal",
                is_recurring=False,
                parent_expense_id=parent.id,
            )
            db.session.add(child)
            db.session.commit()

            # Verify relationship
            assert child.parent_expense_id == parent.id
            assert child.parent_expense == parent
            assert child in parent.child_expenses


class TestRecurringExpenseService:
    """Tests for the RecurringExpenseService."""

    def test_calculate_next_occurrence_weekly(self, app):
        """Test weekly next occurrence calculation."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            today = date.today()
            next_date = RecurringExpenseService.calculate_next_occurrence(today, "weekly")
            assert next_date == today + timedelta(weeks=1)

    def test_calculate_next_occurrence_monthly(self, app):
        """Test monthly next occurrence calculation."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            today = date.today()
            next_date = RecurringExpenseService.calculate_next_occurrence(today, "monthly")
            assert next_date == today + relativedelta(months=1)

    def test_calculate_next_occurrence_yearly(self, app):
        """Test yearly next occurrence calculation."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            today = date.today()
            next_date = RecurringExpenseService.calculate_next_occurrence(today, "yearly")
            assert next_date == today + relativedelta(years=1)

    def test_calculate_next_occurrence_respects_end_date(self, app):
        """Test that next occurrence is None when past end date."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            today = date.today()
            # End date is before next occurrence would be
            end_date = today + timedelta(days=5)
            next_date = RecurringExpenseService.calculate_next_occurrence(
                today, "monthly", end_date
            )
            assert next_date is None

    def test_calculate_next_occurrence_invalid_frequency(self, app):
        """Test that invalid frequency returns None."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            today = date.today()
            next_date = RecurringExpenseService.calculate_next_occurrence(today, "invalid")
            assert next_date is None

    def test_get_due_recurring_expenses(self, app):
        """Test getting recurring expenses that are due."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            # Create a recurring expense due today
            due_expense = Expense(
                description="Due Expense",
                amount=100.00,
                currency="USD",
                payer="test@example.com",
                group_id=1,
                is_recurring=True,
                recurrence_frequency="monthly",
                next_occurrence=date.today(),
            )
            db.session.add(due_expense)

            # Create a recurring expense not yet due
            future_expense = Expense(
                description="Future Expense",
                amount=100.00,
                currency="USD",
                payer="test@example.com",
                group_id=1,
                is_recurring=True,
                recurrence_frequency="monthly",
                next_occurrence=date.today() + timedelta(days=10),
            )
            db.session.add(future_expense)
            db.session.commit()

            due_expenses = RecurringExpenseService.get_due_recurring_expenses()
            assert len(due_expenses) == 1
            assert due_expenses[0].description == "Due Expense"

    def test_generate_expense_from_recurring(self, app):
        """Test generating a new expense from a recurring expense."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            parent = Expense(
                description="Monthly Rent",
                amount=1500.00,
                currency="EUR",
                payer="landlord@example.com",
                group_id=1,
                split_type="equal",
                split_details='{"tenant1@example.com": 750, "tenant2@example.com": 750}',
                participants="tenant1@example.com, tenant2@example.com",
                category="Rent",
                is_recurring=True,
                recurrence_frequency="monthly",
                next_occurrence=date.today(),
            )
            db.session.add(parent)
            db.session.commit()

            new_expense = RecurringExpenseService.generate_expense_from_recurring(parent)

            assert new_expense.description == parent.description
            assert new_expense.amount == parent.amount
            assert new_expense.currency == parent.currency
            assert new_expense.payer == parent.payer
            assert new_expense.group_id == parent.group_id
            assert new_expense.split_type == parent.split_type
            assert new_expense.split_details == parent.split_details
            assert new_expense.category == parent.category
            assert new_expense.is_recurring is False
            assert new_expense.parent_expense_id == parent.id

    def test_process_recurring_expense(self, app):
        """Test processing a single recurring expense."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            today = date.today()
            parent = Expense(
                description="Weekly Groceries",
                amount=200.00,
                currency="USD",
                payer="shopper@example.com",
                group_id=1,
                split_type="equal",
                is_recurring=True,
                recurrence_frequency="weekly",
                next_occurrence=today,
            )
            db.session.add(parent)
            db.session.commit()

            new_expense, success = RecurringExpenseService.process_recurring_expense(parent)

            assert success is True
            assert new_expense is not None
            assert new_expense.description == "Weekly Groceries"
            assert new_expense.parent_expense_id == parent.id

            # Verify parent's next_occurrence was updated
            updated_parent = db.session.get(Expense, parent.id)
            assert updated_parent.next_occurrence == today + timedelta(weeks=1)

    def test_process_all_due_expenses(self, app):
        """Test processing all due recurring expenses."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            today = date.today()

            # Create multiple due expenses
            for i in range(3):
                expense = Expense(
                    description=f"Due Expense {i}",
                    amount=100.00 * (i + 1),
                    currency="USD",
                    payer="test@example.com",
                    group_id=1,
                    is_recurring=True,
                    recurrence_frequency="monthly",
                    next_occurrence=today,
                )
                db.session.add(expense)
            db.session.commit()

            successful, failed = RecurringExpenseService.process_all_due_expenses()

            assert successful == 3
            assert failed == 0

            # Verify 3 new expenses were created (6 total now)
            all_expenses = Expense.query.all()
            assert len(all_expenses) == 6  # 3 parents + 3 children

    def test_cancel_recurring_expense(self, app):
        """Test canceling a recurring expense."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            expense = Expense(
                description="Cancelable Expense",
                amount=100.00,
                currency="USD",
                payer="test@example.com",
                group_id=1,
                is_recurring=True,
                recurrence_frequency="monthly",
                next_occurrence=date.today() + timedelta(days=30),
            )
            db.session.add(expense)
            db.session.commit()

            result = RecurringExpenseService.cancel_recurring_expense(expense.id)

            assert result is True

            # Verify next_occurrence is now None
            updated = db.session.get(Expense, expense.id)
            assert updated.next_occurrence is None

    def test_get_recurring_expenses_for_group(self, app):
        """Test getting recurring expenses for a specific group."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            # Create recurring expenses for group 1
            for i in range(2):
                expense = Expense(
                    description=f"Group 1 Expense {i}",
                    amount=100.00,
                    currency="USD",
                    payer="test@example.com",
                    group_id=1,
                    is_recurring=True,
                    recurrence_frequency="monthly",
                    next_occurrence=date.today() + timedelta(days=i * 10),
                )
                db.session.add(expense)

            # Create recurring expense for group 2
            expense2 = Expense(
                description="Group 2 Expense",
                amount=100.00,
                currency="USD",
                payer="test@example.com",
                group_id=2,
                is_recurring=True,
                recurrence_frequency="monthly",
                next_occurrence=date.today(),
            )
            db.session.add(expense2)
            db.session.commit()

            group1_expenses = RecurringExpenseService.get_recurring_expenses_for_group(1)

            assert len(group1_expenses) == 2
            for exp in group1_expenses:
                assert exp.group_id == 1


class TestRecurringExpenseRoutes:
    """Tests for recurring expense creation via routes."""

    def test_create_recurring_expense(self, client, app):
        """Test creating a recurring expense through the route."""
        with app.app_context():
            # Create test user and group
            user = User(email="test@example.com")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            # Log in
            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["email"] = user.email

            # Create recurring expense
            response = client.post(
                f"/groups/{group.id}",
                data={
                    "description": "Monthly Rent",
                    "amount": "1500.00",
                    "payer": user.email,
                    "split_type": "equal",
                    "participants": user.email,
                    "currency": "USD",
                    "is_recurring": "on",
                    "recurrence_frequency": "monthly",
                    "recurrence_end_date": "",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            # Verify expense was created with recurring settings
            expense = Expense.query.filter_by(description="Monthly Rent").first()
            assert expense is not None
            assert expense.is_recurring is True
            assert expense.recurrence_frequency == "monthly"
            assert expense.next_occurrence is not None

    def test_create_recurring_expense_with_end_date(self, client, app):
        """Test creating a recurring expense with an end date."""
        with app.app_context():
            # Create test user and group
            user = User(email="test@example.com")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            end_date = date.today() + relativedelta(months=6)

            # Log in
            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["email"] = user.email

            # Create recurring expense with end date
            response = client.post(
                f"/groups/{group.id}",
                data={
                    "description": "6-Month Subscription",
                    "amount": "50.00",
                    "payer": user.email,
                    "split_type": "equal",
                    "participants": user.email,
                    "currency": "USD",
                    "is_recurring": "on",
                    "recurrence_frequency": "monthly",
                    "recurrence_end_date": end_date.strftime("%Y-%m-%d"),
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            # Verify expense was created with end date
            expense = Expense.query.filter_by(description="6-Month Subscription").first()
            assert expense is not None
            assert expense.is_recurring is True
            assert expense.recurrence_end_date == end_date

    def test_create_weekly_recurring_expense(self, client, app):
        """Test creating a weekly recurring expense."""
        with app.app_context():
            user = User(email="test@example.com")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["email"] = user.email

            response = client.post(
                f"/groups/{group.id}",
                data={
                    "description": "Weekly Groceries",
                    "amount": "100.00",
                    "payer": user.email,
                    "split_type": "equal",
                    "participants": user.email,
                    "currency": "USD",
                    "is_recurring": "on",
                    "recurrence_frequency": "weekly",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            expense = Expense.query.filter_by(description="Weekly Groceries").first()
            assert expense is not None
            assert expense.recurrence_frequency == "weekly"
            expected_next = date.today() + timedelta(weeks=1)
            assert expense.next_occurrence == expected_next

    def test_create_yearly_recurring_expense(self, client, app):
        """Test creating a yearly recurring expense."""
        with app.app_context():
            user = User(email="test@example.com")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["email"] = user.email

            response = client.post(
                f"/groups/{group.id}",
                data={
                    "description": "Annual Insurance",
                    "amount": "1200.00",
                    "payer": user.email,
                    "split_type": "equal",
                    "participants": user.email,
                    "currency": "USD",
                    "is_recurring": "on",
                    "recurrence_frequency": "yearly",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            expense = Expense.query.filter_by(description="Annual Insurance").first()
            assert expense is not None
            assert expense.recurrence_frequency == "yearly"
            expected_next = date.today() + relativedelta(years=1)
            assert expense.next_occurrence == expected_next

    def test_create_non_recurring_expense(self, client, app):
        """Test creating a non-recurring expense still works."""
        with app.app_context():
            user = User(email="test@example.com")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["email"] = user.email

            response = client.post(
                f"/groups/{group.id}",
                data={
                    "description": "One-time Purchase",
                    "amount": "50.00",
                    "payer": user.email,
                    "split_type": "equal",
                    "participants": user.email,
                    "currency": "USD",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            expense = Expense.query.filter_by(description="One-time Purchase").first()
            assert expense is not None
            assert expense.is_recurring is False
            assert expense.recurrence_frequency is None
            assert expense.next_occurrence is None

    def test_create_recurring_expense_with_invalid_frequency(self, client, app):
        """Test that invalid frequency defaults to monthly."""
        with app.app_context():
            user = User(email="test@example.com")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["email"] = user.email

            response = client.post(
                f"/groups/{group.id}",
                data={
                    "description": "Invalid Frequency Test",
                    "amount": "100.00",
                    "payer": user.email,
                    "split_type": "equal",
                    "participants": user.email,
                    "currency": "USD",
                    "is_recurring": "on",
                    "recurrence_frequency": "invalid_frequency",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            expense = Expense.query.filter_by(description="Invalid Frequency Test").first()
            assert expense is not None
            assert expense.is_recurring is True
            # Invalid frequency should default to monthly
            assert expense.recurrence_frequency == "monthly"

    def test_create_recurring_expense_end_date_before_next_occurrence(self, client, app):
        """Test recurring expense where end date is before next occurrence."""
        with app.app_context():
            user = User(email="test@example.com")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            # Set end date to tomorrow (before next monthly occurrence)
            end_date = date.today() + timedelta(days=1)

            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["email"] = user.email

            response = client.post(
                f"/groups/{group.id}",
                data={
                    "description": "Short-lived Recurring",
                    "amount": "100.00",
                    "payer": user.email,
                    "split_type": "equal",
                    "participants": user.email,
                    "currency": "USD",
                    "is_recurring": "on",
                    "recurrence_frequency": "monthly",
                    "recurrence_end_date": end_date.strftime("%Y-%m-%d"),
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            expense = Expense.query.filter_by(description="Short-lived Recurring").first()
            assert expense is not None
            assert expense.is_recurring is True
            # Next occurrence should be None since it would be after end date
            assert expense.next_occurrence is None

    def test_create_recurring_expense_with_invalid_end_date(self, client, app):
        """Test recurring expense with invalid end date format."""
        with app.app_context():
            user = User(email="test@example.com")
            db.session.add(user)
            db.session.commit()

            group = Group(name="Test Group", created_by_id=user.id)
            group.members.append(user)
            db.session.add(group)
            db.session.commit()

            with client.session_transaction() as sess:
                sess["user_id"] = user.id
                sess["email"] = user.email

            response = client.post(
                f"/groups/{group.id}",
                data={
                    "description": "Invalid End Date Test",
                    "amount": "100.00",
                    "payer": user.email,
                    "split_type": "equal",
                    "participants": user.email,
                    "currency": "USD",
                    "is_recurring": "on",
                    "recurrence_frequency": "monthly",
                    "recurrence_end_date": "not-a-valid-date",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            expense = Expense.query.filter_by(description="Invalid End Date Test").first()
            assert expense is not None
            assert expense.is_recurring is True
            # Invalid date should result in None
            assert expense.recurrence_end_date is None
            # But next_occurrence should still be set
            assert expense.next_occurrence is not None


class TestRecurringExpenseServiceEdgeCases:
    """Additional edge case tests for RecurringExpenseService."""

    def test_cancel_non_recurring_expense(self, app):
        """Test canceling a non-recurring expense returns False."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            expense = Expense(
                description="Non-recurring",
                amount=100.00,
                currency="USD",
                payer="test@example.com",
                group_id=1,
                is_recurring=False,
            )
            db.session.add(expense)
            db.session.commit()

            result = RecurringExpenseService.cancel_recurring_expense(expense.id)
            assert result is False

    def test_cancel_nonexistent_expense(self, app):
        """Test canceling a non-existent expense returns False."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            result = RecurringExpenseService.cancel_recurring_expense(99999)
            assert result is False

    def test_process_recurring_expense_with_error(self, app, monkeypatch):
        """Test processing recurring expense handles errors gracefully."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            expense = Expense(
                description="Error Test",
                amount=100.00,
                currency="USD",
                payer="test@example.com",
                group_id=1,
                is_recurring=True,
                recurrence_frequency="monthly",
                next_occurrence=date.today(),
            )
            db.session.add(expense)
            db.session.commit()

            # Monkeypatch to simulate an error
            def mock_commit():
                raise Exception("Simulated database error")

            monkeypatch.setattr(db.session, "commit", mock_commit)

            new_expense, success = RecurringExpenseService.process_recurring_expense(expense)

            assert success is False
            assert new_expense is None

    def test_process_all_due_expenses_with_failures(self, app, monkeypatch):
        """Test processing all due expenses counts failures correctly."""
        from services.recurring_expense_service import RecurringExpenseService

        with app.app_context():
            # Create two due expenses
            for i in range(2):
                expense = Expense(
                    description=f"Due Expense {i}",
                    amount=100.00,
                    currency="USD",
                    payer="test@example.com",
                    group_id=1,
                    is_recurring=True,
                    recurrence_frequency="monthly",
                    next_occurrence=date.today(),
                )
                db.session.add(expense)
            db.session.commit()

            # Mock process_recurring_expense to fail
            call_count = [0]

            def mock_process(expense):
                call_count[0] += 1
                if call_count[0] == 1:
                    return None, False  # First one fails
                return Expense(description="Generated"), True  # Second succeeds

            monkeypatch.setattr(
                RecurringExpenseService, "process_recurring_expense", mock_process
            )

            successful, failed = RecurringExpenseService.process_all_due_expenses()

            assert successful == 1
            assert failed == 1
