"""Service for expense-related business logic."""


class ExpenseService:
    """Service class for expense calculations."""

    @staticmethod
    def calculate_balances(expenses):
        """
        Calculate who owes whom based on expenses.
        
        Returns:
            dict: Contains 'balances' (net amounts) and 'transactions' (simplified payments)
        """
        balances = {}
        
        for expense in expenses:
            if not expense.participants:
                continue
                
            participants = [p.strip() for p in expense.participants.split(",") if p.strip()]
            if not participants:
                continue
                
            share = expense.amount / len(participants)
            
            # Payer is owed money
            balances[expense.payer] = balances.get(expense.payer, 0) + expense.amount
            
            # Each participant owes their share
            for participant in participants:
                balances[participant] = balances.get(participant, 0) - share
        
        # Calculate simplified transactions
        transactions = []
        debtors = {name: amt for name, amt in balances.items() if amt < 0}
        creditors = {name: amt for name, amt in balances.items() if amt > 0}
        
        for debtor, debt in sorted(debtors.items(), key=lambda x: x[1]):
            debt = abs(debt)
            for creditor, credit in sorted(creditors.items(), key=lambda x: -x[1]):
                if debt <= 0 or credit <= 0:
                    continue
                    
                amount = min(debt, credit)
                transactions.append({
                    "from": debtor,
                    "to": creditor,
                    "amount": amount
                })
                
                debt -= amount
                creditors[creditor] -= amount
        
        return {
            "balances": balances,
            "transactions": transactions
        }
