"""Business logic for expense calculations and balance summaries."""

import json
from collections import defaultdict


class ExpenseService:
    """Service class for expense-related business logic."""

    @staticmethod
    def calculate_balances(expenses):
        """
        Calculate who owes whom based on a list of expenses.

        This function:
        1. Calculates how much each person paid
        2. Calculates how much each person should pay (based on split_details)
        3. Determines the net balance (what they paid - what they should pay)

        Args:
            expenses: List of Expense model objects with amount, payer, and split_details fields

        Returns:
            Dictionary with:
            - 'balances': dict mapping person name to their net balance
              (positive = owed money, negative = owes money)
            - 'transactions': list of simplified payment transactions
        """
        if not expenses:
            return {"balances": {}, "transactions": []}

        # Track how much each person paid
        paid = defaultdict(float)
        # Track how much each person should pay (their share)
        should_pay = defaultdict(float)

        for expense in expenses:
            # The payer paid the full amount
            paid[expense.payer] += expense.amount

            # Parse split details
            split_details = ExpenseService._parse_split_details(expense)
            
            if not split_details:
                continue

            # Each participant should pay their share based on split_details
            for participant, amount in split_details.items():
                should_pay[participant] += amount

        # Calculate net balance for each person
        all_people = set(paid.keys()) | set(should_pay.keys())
        balances = {}
        for person in all_people:
            # Positive balance = they are owed money
            # Negative balance = they owe money
            balances[person] = round(paid[person] - should_pay[person], 2)

        # Generate simplified transactions
        transactions = ExpenseService._simplify_debts(balances)

        return {"balances": balances, "transactions": transactions}

    @staticmethod
    def _simplify_debts(balances):
        """
        Simplify debts into minimal transactions.

        Args:
            balances: Dictionary mapping person to their balance
                      (positive = owed, negative = owes)

        Returns:
            List of transactions in format:
            [{'from': 'Alice', 'to': 'Bob', 'amount': 10.0}, ...]
        """
        # Separate people who owe money from people who are owed money
        debtors = []  # People who owe money (negative balance)
        creditors = []  # People who are owed money (positive balance)

        for person, balance in balances.items():
            if balance < -0.01:  # Owes money (use small epsilon for floating point)
                debtors.append({"name": person, "amount": -balance})
            elif balance > 0.01:  # Is owed money
                creditors.append({"name": person, "amount": balance})

        transactions = []

        # Sort for consistent results
        debtors.sort(key=lambda x: x["amount"], reverse=True)
        creditors.sort(key=lambda x: x["amount"], reverse=True)

        # Match debtors with creditors
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            debtor = debtors[i]
            creditor = creditors[j]

            # Amount to transfer is the minimum of what debtor owes and creditor is owed
            amount = min(debtor["amount"], creditor["amount"])

            transactions.append(
                {"from": debtor["name"], "to": creditor["name"], "amount": round(amount, 2)}
            )

            # Update remaining amounts
            debtor["amount"] -= amount
            creditor["amount"] -= amount

            # Move to next person if this one is settled
            if debtor["amount"] < 0.01:
                i += 1
            if creditor["amount"] < 0.01:
                j += 1

        return transactions

    @staticmethod
    def _parse_split_details(expense):
        """
        Parse split details from expense, handling both old and new formats.
        
        Args:
            expense: Expense model object
            
        Returns:
            Dictionary mapping participant names to their share amounts
        """
        # Try new format first (split_details JSON)
        if expense.split_details:
            try:
                return json.loads(expense.split_details)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fall back to old format (participants text field)
        if expense.participants:
            participants = [p.strip() for p in expense.participants.split(",") if p.strip()]
            if participants:
                share = expense.amount / len(participants)
                return {participant: share for participant in participants}
        
        return {}

    @staticmethod
    def validate_custom_split(split_details, total_amount):
        """
        Validate that custom split amounts sum to the total amount.
        
        Args:
            split_details: Dictionary mapping participant names to amounts
            total_amount: Total expense amount
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not split_details:
            return False, "No participants specified"
        
        total_split = sum(split_details.values())
        tolerance = 0.01  # Allow small floating point differences
        
        if abs(total_split - total_amount) > tolerance:
            return False, f"Split amounts ({total_split:.2f}) must equal total amount ({total_amount:.2f})"
        
        return True, None

    @staticmethod
    def calculate_equal_split(participants, total_amount):
        """
        Calculate equal split for given participants.
        
        Args:
            participants: List of participant names
            total_amount: Total expense amount
            
        Returns:
            Dictionary mapping participant names to their equal share
        """
        if not participants:
            return {}
        
        share = total_amount / len(participants)
        return {participant: share for participant in participants}
