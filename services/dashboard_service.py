"""Business logic for dashboard financial calculations."""

from extensions import db
from models import Expense, Settlement, User


class DashboardService:
    """Service class for dashboard financial calculations."""

    @staticmethod
    def get_user_summary(user_id: int) -> dict:
        """
        Calculate financial summary for a user.

        Args:
            user_id: The authenticated user's ID

        Returns:
            Dictionary containing:
            {
                'total_expenses': float,       # Sum of expenses where user is payer
                'total_payments': float,       # Sum of settlements where user is payer
                'outstanding_balance': float,  # total_expenses - total_payments
                'has_data': bool              # True if any financial data exists
            }
        """
        # Get user object to determine payer identifier
        user = db.session.get(User, user_id)
        if not user:
            return {
                "total_expenses": 0.0,
                "total_payments": 0.0,
                "outstanding_balance": 0.0,
                "has_data": False,
            }

        # Query expenses where payer matches user's email OR display_name
        # Need to check both because expenses can be stored with either
        expenses = Expense.query.filter(
            db.or_(
                Expense.payer == user.email,
                Expense.payer == user.display_name
            )
        ).all()
        total_expenses = sum(e.amount for e in expenses)

        # Query settlements where payer_id matches user_id
        settlements = Settlement.query.filter_by(payer_id=user_id).all()
        total_payments = sum(s.amount for s in settlements)

        # Calculate outstanding balance
        outstanding_balance = total_expenses - total_payments

        # Determine if user has any data
        has_data = len(expenses) > 0 or len(settlements) > 0

        # Return summary with values rounded to 2 decimal places
        return {
            "total_expenses": round(total_expenses, 2),
            "total_payments": round(total_payments, 2),
            "outstanding_balance": round(outstanding_balance, 2),
            "has_data": has_data,
        }
