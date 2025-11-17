"""Business logic for dashboard financial calculations."""

from extensions import db
from models import Expense, Settlement, User
from services.expense_service import ExpenseService


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
                'outstanding_balance': float,  # Net balance after accounting for settlements
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
            db.or_(Expense.payer == user.email, Expense.payer == user.display_name)
        ).all()
        total_expenses = sum(e.amount for e in expenses)

        # Query settlements where payer_id matches user_id
        settlements = Settlement.query.filter_by(payer_id=user_id).all()
        total_payments = sum(s.amount for s in settlements)

        # Calculate outstanding balance using proper balance calculation
        # Get all expenses across the system to calculate what user owes/is owed
        all_expenses = Expense.query.all()
        balance_data = ExpenseService.calculate_balances(all_expenses)
        
        # Get user's balance from expense calculations (positive = owed to them, negative = they owe)
        # Note: balances use email as key for participants, but payer field may use display_name
        # We need to check both email and display_name
        expense_balance = balance_data["balances"].get(user.email, 0.0)
        # Also check by display_name if it exists (for backward compatibility with payer field)
        if user.display_name and user.display_name != user.email:
            expense_balance += balance_data["balances"].get(user.display_name, 0.0)
        
        # Adjust balance for settlements made and received
        settlements_paid = Settlement.query.filter_by(payer_id=user_id).all()
        settlements_received = Settlement.query.filter_by(recipient_id=user_id).all()
        
        # When user pays someone, their debt decreases (balance increases toward positive)
        # When user receives payment, what they're owed decreases (balance decreases toward negative)  
        adjusted_balance = expense_balance + sum(s.amount for s in settlements_paid) - sum(s.amount for s in settlements_received)
        
        # Outstanding balance is the adjusted balance
        # Positive = others owe you, Negative = you owe others, Zero = all settled
        outstanding_balance = adjusted_balance

        # Determine if user has any data
        has_data = len(expenses) > 0 or len(settlements) > 0

        # Return summary with values rounded to 2 decimal places
        return {
            "total_expenses": round(total_expenses, 2),
            "total_payments": round(total_payments, 2),
            "outstanding_balance": round(outstanding_balance, 2),
            "has_data": has_data,
        }
