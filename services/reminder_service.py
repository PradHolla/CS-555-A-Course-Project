"""Business logic for expense reminder notifications."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from extensions import db
from models import Expense, User
from services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

# Constants
BALANCE_EPSILON = 0.01  # Minimum balance threshold to avoid floating point issues


class ReminderService:
    """Service class for expense reminder notifications."""

    @staticmethod
    def calculate_balance_age(user_id: int) -> Tuple[int, Optional[datetime]]:
        """
        Calculate how long a user's balance has been outstanding.

        Args:
            user_id: The user's ID

        Returns:
            Tuple of (days_outstanding, oldest_expense_date)
            Returns (0, None) if user has no unpaid expenses
        """
        try:
            if not user_id:
                logger.warning("Invalid user_id provided (None or 0)")
                return (0, None)
            
            user = db.session.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return (0, None)

            # Get user's identifier for expense queries
            # Get user's identifiers (both email and display name)
            user_email = user.email
            user_display_name = user.display_name

            # Find expenses where user is a participant but not the payer
            # Check for both email and display name in split_details
            unpaid_expenses = []
            all_expenses = Expense.query.order_by(Expense.created_at.asc()).all()
            
            for expense in all_expenses:
                # Check if user is in split_details (by email or display name)
                if user_email in expense.split_details or (user_display_name and user_display_name in expense.split_details):
                    # Check if user is NOT the payer (compare with both email and display name)
                    if expense.payer != user_email and (not user_display_name or expense.payer != user_display_name):
                        unpaid_expenses.append(expense)

            if not unpaid_expenses:
                return (0, None)

            # Get the oldest unpaid expense to determine how long balance has been outstanding
            oldest_expense = unpaid_expenses[0]
            current_time = datetime.now(timezone.utc)

            # Handle timezone-naive datetime from database
            expense_time = oldest_expense.created_at
            if expense_time.tzinfo is None:
                expense_time = expense_time.replace(tzinfo=timezone.utc)

            days_outstanding = (current_time - expense_time).days

            logger.debug(
                f"User {user.email} has balance outstanding for {days_outstanding} days "
                f"(since {expense_time.date()})"
            )

            return (days_outstanding, expense_time)

        except Exception as e:
            logger.error(f"Error calculating balance age for user {user_id}: {str(e)}")
            return (0, None)

    @staticmethod
    def get_users_needing_reminders(
        days_threshold: int = 7,
    ) -> List[Tuple[User, float, datetime]]:
        """
        Identify users who need payment reminders.

        Args:
            days_threshold: Number of days outstanding before sending reminder

        Returns:
            List of tuples: [(user, negative_balance, oldest_expense_date), ...]
        """
        users_to_remind = []

        try:
            # Get all users who have participated in expenses
            users = User.query.all()
            logger.info(f"Checking {len(users)} users for reminder eligibility")

            for user in users:
                try:
                    # Calculate current balance using existing dashboard service
                    summary = DashboardService.get_user_summary(user.id)

                    # Only consider users with negative balance (they owe money)
                    if summary["outstanding_balance"] < -BALANCE_EPSILON:
                        # Check how long the balance has been outstanding
                        days_outstanding, oldest_date = ReminderService.calculate_balance_age(
                            user.id
                        )

                        if days_outstanding >= days_threshold and oldest_date:
                            users_to_remind.append(
                                (user, summary["outstanding_balance"], oldest_date)
                            )
                            logger.debug(
                                f"User {user.email} needs reminder: "
                                f"${abs(summary['outstanding_balance']):.2f} "
                                f"outstanding for {days_outstanding} days"
                            )

                except Exception as e:
                    logger.error(
                        f"Error processing user {user.email} for reminders: {str(e)}"
                    )
                    continue

            logger.info(f"Found {len(users_to_remind)} users needing reminders")
            return users_to_remind

        except Exception as e:
            logger.error(f"Error getting users needing reminders: {str(e)}")
            return []

    @staticmethod
    def get_balance_breakdown(user_id: int) -> List[dict]:
        """
        Get detailed breakdown of who user owes money to.

        Args:
            user_id: The user's ID

        Returns:
            List of dicts: [{'creditor': str, 'amount': float}, ...]
        """
        try:
            user = db.session.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found for balance breakdown")
                return []

            user_email = user.email
            user_display_name = user.display_name
            breakdown = []

            # Get all expenses where user is participant but not payer
            unpaid_expenses = []
            all_expenses = Expense.query.all()
            
            for expense in all_expenses:
                # Check if user is in split_details (by email or display name)
                if user_email in expense.split_details or (user_display_name and user_display_name in expense.split_details):
                    # Check if user is NOT the payer
                    if expense.payer != user_email and (not user_display_name or expense.payer != user_display_name):
                        unpaid_expenses.append(expense)

            # Group by creditor (payer) and sum amounts owed
            creditor_totals = {}

            for expense in unpaid_expenses:
                creditor = expense.payer

                # Parse split details to get user's share
                try:
                    split_details = json.loads(expense.split_details)
                    user_share = 0.0

                    # Find user's share in the split (check both email and display name)
                    for participant, amount in split_details.items():
                        if participant == user_email or (user_display_name and participant == user_display_name):
                            user_share = float(amount)
                            break

                    if user_share > 0:
                        if creditor not in creditor_totals:
                            creditor_totals[creditor] = 0.0
                        creditor_totals[creditor] += user_share

                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning(
                        f"Error parsing split details for expense {expense.id}: {str(e)}"
                    )
                    continue

            # Convert to list format
            for creditor, amount in creditor_totals.items():
                if amount > BALANCE_EPSILON:  # Only include significant amounts
                    breakdown.append({"creditor": creditor, "amount": round(amount, 2)})

            # Sort by amount descending
            breakdown.sort(key=lambda x: x["amount"], reverse=True)

            logger.debug(
                f"Balance breakdown for {user.email}: "
                f"{len(breakdown)} creditors, "
                f"total: ${sum(item['amount'] for item in breakdown):.2f}"
            )

            return breakdown

        except Exception as e:
            logger.error(f"Error getting balance breakdown for user {user_id}: {str(e)}")
            return []

    @staticmethod
    def send_reminders(days_threshold: int = 7) -> dict:
        """
        Send reminder notifications to users with unpaid balances.

        Args:
            days_threshold: Number of days before sending reminder (default: 7)

        Returns:
            Dictionary with:
            {
                'reminders_sent': int,
                'users_notified': list[str],
                'errors': list[dict]
            }
        """
        from services.notification_service import send_payment_reminder

        reminders_sent = 0
        users_notified = []
        errors = []

        try:
            # Check if reminders are enabled
            from flask import current_app

            if not current_app.config.get("REMINDER_ENABLED", True):
                logger.info("Reminder system is disabled via configuration")
                return {
                    "reminders_sent": 0,
                    "users_notified": [],
                    "errors": [{"error": "Reminder system disabled"}],
                }

            logger.info(f"Starting reminder process with {days_threshold} day threshold")

            # Get users who need reminders
            users_needing_reminders = ReminderService.get_users_needing_reminders(
                days_threshold
            )

            if not users_needing_reminders:
                logger.info("No users need reminders at this time")
                return {"reminders_sent": 0, "users_notified": [], "errors": []}

            logger.info(f"Processing {len(users_needing_reminders)} users for reminders")

            for user, balance_amount, oldest_date in users_needing_reminders:
                try:
                    # Calculate days outstanding
                    days_outstanding, _ = ReminderService.calculate_balance_age(user.id)

                    # Get detailed balance breakdown
                    balance_breakdown = ReminderService.get_balance_breakdown(user.id)

                    if not balance_breakdown:
                        logger.warning(
                            f"No balance breakdown found for {user.email}, skipping reminder"
                        )
                        continue

                    # Send reminder email
                    send_payment_reminder(
                        user=user,
                        balance_amount=balance_amount,
                        days_outstanding=days_outstanding,
                        balance_breakdown=balance_breakdown,
                    )

                    reminders_sent += 1
                    users_notified.append(user.email)

                    logger.info(
                        f"Reminder sent to {user.email}: "
                        f"${abs(balance_amount):.2f} outstanding for {days_outstanding} days"
                    )

                except Exception as e:
                    error_msg = f"Failed to send reminder to {user.email}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(
                        {"user": user.email, "error": str(e), "balance": balance_amount}
                    )
                    # Continue processing other users
                    continue

            # Log summary
            logger.info(
                f"Reminder process completed: {reminders_sent} sent, {len(errors)} errors"
            )

            return {
                "reminders_sent": reminders_sent,
                "users_notified": users_notified,
                "errors": errors,
            }

        except Exception as e:
            error_msg = f"Critical error in reminder process: {str(e)}"
            logger.error(error_msg)
            return {
                "reminders_sent": reminders_sent,
                "users_notified": users_notified,
                "errors": [{"error": error_msg}],
            }
