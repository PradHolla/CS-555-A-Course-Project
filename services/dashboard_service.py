"""Dashboard service for calculating financial summaries."""

import json

from models import Expense, Settlement


class DashboardService:
    """Service for dashboard summary calculations."""

    @staticmethod
    def get_user_summary(user_id):
        """
        Calculate financial summary for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            dict: {
                'total_expenses': float,
                'total_payments_made': float,
                'total_payments_received': float,
                'outstanding_balance': float,
                'has_data': bool
            }
        """
        from models import User
        
        # Get user's email
        user = User.query.get(user_id)
        if not user:
            return {
                'total_expenses': 0,
                'total_payments_made': 0,
                'total_payments_received': 0,
                'outstanding_balance': 0,
                'has_data': False
            }
        
        # Calculate total expenses where user participates (not just where they paid)
        all_expenses = Expense.query.all()
        total_expenses = 0
        total_user_owes = 0
        
        for expense in all_expenses:
            # Parse split details to see if user is a participant
            if expense.split_details:
                try:
                    split_details = json.loads(expense.split_details)
                    if user.email in split_details:
                        # User participates in this expense, add to total
                        total_expenses += expense.amount
                        
                        # User owes their share of this expense
                        user_share = float(split_details[user.email])
                        
                        # If user is the payer, they're owed (expense - their share)
                        # If user is not the payer, they owe their share
                        if expense.payer == user.email:
                            # User paid, so they're owed (total - their share)
                            total_user_owes -= (expense.amount - user_share)
                        else:
                            # User didn't pay, so they owe their share
                            total_user_owes += user_share
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
        
        # Calculate total payments made by user
        payments_made = Settlement.query.filter_by(payer_id=user_id).all()
        total_payments_made = sum(payment.amount for payment in payments_made)
        
        # Calculate total payments received by user
        payments_received = Settlement.query.filter_by(recipient_id=user_id).all()
        total_payments_received = sum(payment.amount for payment in payments_received)
        
        # Outstanding balance calculation:
        # total_user_owes: positive = user owes money, negative = user is owed money
        # 
        # Scenario 1: User is owed $50 from expenses (total_user_owes = -50)
        #   - Before payment: outstanding = -50 (negative means owed)
        #   - After receiving $50: outstanding = -50 + 50 = 0 ✓
        #
        # Scenario 2: User owes $50 from expenses (total_user_owes = 50)
        #   - Before payment: outstanding = 50 (positive means owes)
        #   - After paying $50: outstanding = 50 - 50 = 0 ✓
        #
        # Formula: total_user_owes - payments_made + payments_received
        # Negative result = user is owed, Positive result = user owes
        outstanding_balance = total_user_owes - total_payments_made + total_payments_received
        
        # Check if user has any data
        has_data = total_expenses > 0 or len(payments_made) > 0 or len(payments_received) > 0 or total_user_owes != 0
        
        return {
            'total_expenses': total_expenses,
            'total_payments_made': total_payments_made,
            'total_payments_received': total_payments_received,
            'outstanding_balance': outstanding_balance,
            'has_data': has_data
        }
