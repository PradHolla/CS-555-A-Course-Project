"""Business logic for expense calculations and balance summaries."""

from collections import defaultdict


class ExpenseService:
    """Service class for expense-related business logic."""

    @staticmethod
    def calculate_balances(expenses):
        """
        Calculate who owes whom based on a list of expenses.

        This function:
        1. Calculates how much each person paid
        2. Calculates how much each person should pay (equal split)
        3. Determines the net balance (what they paid - what they should pay)

        Args:
            expenses: List of Expense model objects with amount, payer, and participants fields

        Returns:
            Dictionary with:
            - 'balances': dict mapping person name to their net balance
              (positive = owed money, negative = owes money)
            - 'transactions': list of simplified payment transactions

        Example:
            expenses = [
                Expense(amount=30, payer="Alice", participants="Alice, Bob, Charlie"),
                Expense(amount=60, payer="Bob", participants="Alice, Bob, Charlie")
            ]
            result = ExpenseService.calculate_balances(expenses)
            # result['balances'] = {'Alice': -10, 'Bob': 10, 'Charlie': -20}
            # Alice owes $10, Bob is owed $10, Charlie owes $20
        """
        if not expenses:
            return {"balances": {}, "transactions": []}

        # Track how much each person paid
        paid = defaultdict(float)
        # Track how much each person should pay (their share)
        should_pay = defaultdict(float)

        for expense in expenses:
            # Parse participants
            participants = [p.strip() for p in (expense.participants or "").split(",") if p.strip()]

            if not participants:
                continue

            # The payer paid the full amount
            paid[expense.payer] += expense.amount

            # Each participant should pay their share
            share = expense.amount / len(participants)
            for participant in participants:
                should_pay[participant] += share

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
