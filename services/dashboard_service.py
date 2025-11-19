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
            # Parse split details using same logic as ExpenseService
            split_details = {}
            if expense.split_details:
                try:
                    split_details = json.loads(expense.split_details)
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Fall back to participants field if no split_details
            if not split_details and expense.participants:
                participants = [p.strip() for p in expense.participants.split(",") if p.strip()]
                if participants:
                    share = expense.amount / len(participants)
                    split_details = {participant: share for participant in participants}
            
            # If user is the payer, they are owed money (positive)
            if expense.payer == user_email or expense.payer == user_display_name:
                if split_details:
                    # Find user's share
                    user_share = 0.0
                    for participant, amount in split_details.items():
                        if participant == user_email or (user_display_name and participant == user_display_name):
                            user_share = float(amount)
                            break
                    
                    # User paid the full amount but only owes their share
                    # So they are owed: (total - their_share)
                    net_balance += (expense.amount - user_share)
                else:
                    # No split details, user is owed the full amount
                    net_balance += expense.amount
            elif split_details:
                # User is not the payer, check if they owe money
                for participant, amount in split_details.items():
                    if participant == user_email or (user_display_name and participant == user_display_name):
                        # User didn't pay but owes their share (negative)
                        net_balance -= float(amount)
                        break
        
        # Query expenses where payer matches user (for total_expenses display)
        expenses = Expense.query.filter(
            db.or_(Expense.payer == user.email, Expense.payer == user.display_name)
        ).all()
        total_expenses = sum(e.amount for e in expenses)

        # Query settlements where payer_id matches user_id
        settlements_paid = Settlement.query.filter_by(payer_id=user_id).all()
        total_payments = sum(s.amount for s in settlements_paid)

        # Adjust net_balance for settlements
        # Settlement payments resolve debts that are already counted in net_balance
        # - When user pays a settlement (is payer), they are paying off debt they owe, so outstanding balance increases (less negative / more positive)
        # - When user receives a settlement (is recipient), someone is paying off debt owed to them, so outstanding balance decreases (less positive / more negative)  
        settlements_received = Settlement.query.filter_by(recipient_id=user_id).all()
        
        outstanding_balance = net_balance + sum(s.amount for s in settlements_paid) - sum(s.amount for s in settlements_received)

        # Determine if user has any data
        has_data = len(all_expenses) > 0 or len(settlements_paid) > 0

        # Return summary with values rounded to 2 decimal places
        return {
            "total_expenses": round(total_expenses, 2),
            "total_payments": round(total_payments, 2),
            "outstanding_balance": round(outstanding_balance, 2),
            "has_data": has_data,
        }
