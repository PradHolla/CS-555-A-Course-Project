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
                'outstanding_balance': float,  # Net balance (positive = owed to user, negative = user owes)
                'has_data': bool              # True if any financial data exists
            }
        """
        import json
        
        # Get user object to determine payer identifier
        user = db.session.get(User, user_id)
        if not user:
            return {
                "total_expenses": 0.0,
                "total_payments": 0.0,
                "outstanding_balance": 0.0,
                "has_data": False,
            }

        user_email = user.email
        user_display_name = user.display_name
        
        # Calculate net balance across all expenses
        net_balance = 0.0
        
        # Get all expenses
        all_expenses = Expense.query.all()
        
        for expense in all_expenses:
            # Check if user is involved in this expense
            if user_email in expense.split_details or (user_display_name and user_display_name in expense.split_details):
                try:
                    split_details = json.loads(expense.split_details)
                    
                    # Find user's share
                    user_share = 0.0
                    for participant, amount in split_details.items():
                        if participant == user_email or (user_display_name and participant == user_display_name):
                            user_share = float(amount)
                            break
                    
                    # If user is the payer, they are owed money (positive)
                    if expense.payer == user_email or expense.payer == user_display_name:
                        # User paid the full amount but only owes their share
                        # So they are owed: (total - their_share)
                        net_balance += (expense.amount - user_share)
                    else:
                        # User didn't pay but owes their share (negative)
                        net_balance -= user_share
                        
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        
        # Query expenses where payer matches user (for total_expenses display)
        expenses = Expense.query.filter(
            db.or_(Expense.payer == user.email, Expense.payer == user.display_name)
        ).all()
        total_expenses = sum(e.amount for e in expenses)

        # Query settlements where payer_id matches user_id
        settlements = Settlement.query.filter_by(payer_id=user_id).all()
        total_payments = sum(s.amount for s in settlements)
        
        # Adjust net balance for settlements made
        net_balance += total_payments

        # Determine if user has any data
        has_data = len(all_expenses) > 0 or len(settlements) > 0

        # Return summary with values rounded to 2 decimal places
        return {
            "total_expenses": round(total_expenses, 2),
            "total_payments": round(total_payments, 2),
            "outstanding_balance": round(net_balance, 2),
            "has_data": has_data,
        }
