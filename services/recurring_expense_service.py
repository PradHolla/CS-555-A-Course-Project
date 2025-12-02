"""Service for handling recurring expense generation."""

from datetime import date
from typing import List, Tuple

from dateutil.relativedelta import relativedelta

from extensions import db
from models import Expense


class RecurringExpenseService:
    """Service for managing recurring expenses."""

    @staticmethod
    def get_due_recurring_expenses() -> List[Expense]:
        """Get all recurring expenses that are due for generation today or earlier."""
        today = date.today()
        return Expense.query.filter(
            Expense.is_recurring == True,  # noqa: E712
            Expense.next_occurrence != None,  # noqa: E711
            Expense.next_occurrence <= today,
        ).all()

    @staticmethod
    def calculate_next_occurrence(
        current_date: date, frequency: str, end_date: date = None
    ) -> date:
        """Calculate the next occurrence date based on frequency.

        Args:
            current_date: The current occurrence date
            frequency: One of 'weekly', 'monthly', 'yearly'
            end_date: Optional end date for recurrence

        Returns:
            The next occurrence date, or None if past end_date
        """
        if frequency == "weekly":
            next_date = current_date + relativedelta(weeks=1)
        elif frequency == "monthly":
            next_date = current_date + relativedelta(months=1)
        elif frequency == "yearly":
            next_date = current_date + relativedelta(years=1)
        else:
            return None

        # Check if next occurrence is past end date
        if end_date and next_date > end_date:
            return None

        return next_date

    @staticmethod
    def generate_expense_from_recurring(parent_expense: Expense) -> Expense:
        """Generate a new expense instance from a recurring expense.

        Args:
            parent_expense: The parent recurring expense

        Returns:
            A new Expense instance (not yet committed to database)
        """
        new_expense = Expense(
            description=parent_expense.description,
            amount=parent_expense.amount,
            currency=parent_expense.currency,
            payer=parent_expense.payer,
            group_id=parent_expense.group_id,
            split_type=parent_expense.split_type,
            split_details=parent_expense.split_details,
            participants=parent_expense.participants,
            category=parent_expense.category,
            expense_date=parent_expense.next_occurrence,
            is_recurring=False,  # Generated expenses are not recurring themselves
            parent_expense_id=parent_expense.id,
        )
        return new_expense

    @staticmethod
    def process_recurring_expense(expense: Expense) -> Tuple[Expense, bool]:
        """Process a single recurring expense.

        Creates a new expense and updates the next occurrence date.

        Args:
            expense: The recurring expense to process

        Returns:
            Tuple of (generated_expense, success)
        """
        try:
            # Generate the new expense
            new_expense = RecurringExpenseService.generate_expense_from_recurring(expense)
            db.session.add(new_expense)

            # Calculate and update next occurrence
            next_date = RecurringExpenseService.calculate_next_occurrence(
                expense.next_occurrence,
                expense.recurrence_frequency,
                expense.recurrence_end_date,
            )
            expense.next_occurrence = next_date

            db.session.commit()
            return new_expense, True
        except Exception as e:
            db.session.rollback()
            print(f"Error processing recurring expense {expense.id}: {str(e)}")
            return None, False

    @staticmethod
    def process_all_due_expenses() -> Tuple[int, int]:
        """Process all recurring expenses that are due.

        Returns:
            Tuple of (successful_count, failed_count)
        """
        due_expenses = RecurringExpenseService.get_due_recurring_expenses()
        successful = 0
        failed = 0

        for expense in due_expenses:
            _, success = RecurringExpenseService.process_recurring_expense(expense)
            if success:
                successful += 1
            else:
                failed += 1

        return successful, failed

    @staticmethod
    def get_recurring_expenses_for_group(group_id: int) -> List[Expense]:
        """Get all active recurring expenses for a group.

        Args:
            group_id: The group ID

        Returns:
            List of recurring expenses
        """
        return Expense.query.filter(
            Expense.group_id == group_id,
            Expense.is_recurring == True,  # noqa: E712
            Expense.next_occurrence != None,  # noqa: E711
        ).order_by(Expense.next_occurrence.asc()).all()

    @staticmethod
    def cancel_recurring_expense(expense_id: int) -> bool:
        """Cancel a recurring expense by clearing its next occurrence.

        Args:
            expense_id: The expense ID to cancel

        Returns:
            True if successful, False otherwise
        """
        try:
            expense = db.session.get(Expense, expense_id)
            if expense and expense.is_recurring:
                expense.next_occurrence = None
                db.session.commit()
                return True
            return False
        except Exception:
            db.session.rollback()
            return False
