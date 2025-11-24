"""Business logic for expense calculations and balance summaries."""

import json
from collections import defaultdict


class ExpenseService:
    """Service class for expense-related business logic."""

    @staticmethod
    def calculate_balances(expenses, settlements=None):
        """
        Calculate who owes whom based on a list of expenses and settlements.

        This function:
        1. Calculates how much each person paid
        2. Calculates how much each person should pay (based on split_details)
        3. Applies settlements (recorded payments) to adjust balances
        4. Determines the net balance (what they paid - what they should pay + settlements)

        Args:
            expenses: List of Expense model objects with amount, payer, and split_details fields
            settlements: Optional list of Settlement model objects representing recorded payments

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

        # Apply settlements (recorded payments)
        if settlements:
            for settlement in settlements:
                payer_email = settlement.payer.email
                recipient_email = settlement.recipient.email

                # The payer settled some debt, so their balance increases (they owe less)
                balances[payer_email] = balances.get(payer_email, 0.0) + settlement.amount

                # The recipient received payment, so their balance decreases (they are owed less)
                balances[recipient_email] = balances.get(recipient_email, 0.0) - settlement.amount

                # Round to avoid floating point issues
                balances[payer_email] = round(balances[payer_email], 2)
                balances[recipient_email] = round(balances[recipient_email], 2)

        # Generate simplified transactions
        transactions = ExpenseService._simplify_debts(balances)

        return {"balances": balances, "transactions": transactions}

    @staticmethod
    def calculate_detailed_breakdown(expenses):
        """
        Calculate detailed breakdown showing ALL pairwise debts from each expense.

        Unlike calculate_balances() which simplifies debts, this shows the actual
        debts created by each expense (who owes the payer for their share).

        Args:
            expenses: List of Expense model objects

        Returns:
            List of detailed debt transactions in format:
            [{
                'from': person_who_owes,
                'to': person_who_paid,
                'amount': amount_owed,
                'expense_description': 'Lunch',
                'expense_id': 123
            }, ...]
        """
        if not expenses:
            return []

        detailed_transactions = []

        for expense in expenses:
            payer = expense.payer
            split_details = ExpenseService._parse_split_details(expense)

            if not split_details:
                continue

            # For each participant (excluding payer), create a debt record
            for participant, amount in split_details.items():
                if participant != payer and amount > 0.01:  # Skip payer and zero amounts
                    detailed_transactions.append(
                        {
                            "from": participant,
                            "to": payer,
                            "amount": round(amount, 2),
                            "expense_description": expense.description,
                            "expense_id": expense.id,
                        }
                    )

        # Sort by amount (largest first) for better readability
        detailed_transactions.sort(key=lambda x: x["amount"], reverse=True)

        return detailed_transactions

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
            return (
                False,
                f"Split amounts ({total_split:.2f}) must equal total amount ({total_amount:.2f})",
            )

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

    @staticmethod
    def calculate_percentage_split(percentages, total_amount):
        """
        Calculate split based on percentages.

        Args:
            percentages: Dictionary mapping participant names to their percentage (0-100)
            total_amount: Total expense amount

        Returns:
            Dictionary mapping participant names to their calculated amount
        """
        if not percentages:
            return {}

        return {
            participant: (percentage / 100.0) * total_amount
            for participant, percentage in percentages.items()
        }

    @staticmethod
    def validate_percentage_split(percentages):
        """
        Validate that percentages are valid and sum to 100.

        Args:
            percentages: Dictionary mapping participant names to percentages

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not percentages:
            return False, "No participants specified"

        # Check for negative percentages
        for participant, percentage in percentages.items():
            if percentage < 0:
                return False, f"Percentage for {participant} cannot be negative"

        total_percentage = sum(percentages.values())
        tolerance = 0.01  # Allow small floating point differences

        if abs(total_percentage - 100.0) > tolerance:
            return (
                False,
                f"Percentages must sum to 100% (current total: {total_percentage:.2f}%)",
            )

        return True, None

    @staticmethod
    def calculate_shares_split(shares, total_amount):
        """
        Calculate split based on shares.

        Args:
            shares: Dictionary mapping participant names to their number of shares
            total_amount: Total expense amount

        Returns:
            Dictionary mapping participant names to their calculated amount
        """
        if not shares:
            return {}

        total_shares = sum(shares.values())
        if total_shares == 0:
            return {}

        return {
            participant: (share_count / total_shares) * total_amount
            for participant, share_count in shares.items()
        }

    @staticmethod
    def validate_shares_split(shares):
        """
        Validate that shares are valid positive numbers.

        Args:
            shares: Dictionary mapping participant names to share counts

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not shares:
            return False, "No participants specified"

        # Check for non-positive shares
        for participant, share_count in shares.items():
            if share_count <= 0:
                return False, f"Share count for {participant} must be positive"

        return True, None

    @staticmethod
    def get_user_balance_in_group(user_email, group_id):
        """
        Calculate a user's net balance within a specific group.

        Args:
            user_email: Email of the user
            group_id: ID of the group

        Returns:
            float: User's balance (positive = owed money, negative = owes money)
        """
        from models import Expense, Settlement

        # Get all expenses for this group
        expenses = Expense.query.filter_by(group_id=group_id).all()

        # Get all settlements (we need to filter by group participants)
        settlements = Settlement.query.all()

        # Calculate balances for the group
        balance_data = ExpenseService.calculate_balances(expenses, settlements)

        # Return this user's balance (0 if not in balance data)
        return balance_data["balances"].get(user_email, 0.0)

    @staticmethod
    def get_user_total_balance(user_email):
        """
        Calculate a user's net balance across ALL groups.

        Args:
            user_email: Email of the user

        Returns:
            float: User's total balance (positive = owed money, negative = owes money)
        """
        from models import Expense, Settlement

        # Get all expenses
        expenses = Expense.query.all()

        # Get all settlements
        settlements = Settlement.query.all()

        # Calculate balances across all expenses
        balance_data = ExpenseService.calculate_balances(expenses, settlements)

        # Return this user's balance (0 if not in balance data)
        return balance_data["balances"].get(user_email, 0.0)

    @staticmethod
    def has_outstanding_balance_in_group(user_email, group_id):
        """
        Check if a user has any outstanding balance (owes or is owed) in a specific group.

        Args:
            user_email: Email of the user
            group_id: ID of the group

        Returns:
            Tuple of (has_balance, balance_amount)
        """
        balance = ExpenseService.get_user_balance_in_group(user_email, group_id)
        # Consider balances > $0.01 or < -$0.01 as outstanding (to handle floating point)
        has_balance = abs(balance) > 0.01
        return has_balance, balance

    @staticmethod
    def has_outstanding_balance(user_email):
        """
        Check if a user has any outstanding balance (owes or is owed) across ALL groups.

        Args:
            user_email: Email of the user

        Returns:
            Tuple of (has_balance, balance_amount)
        """
        balance = ExpenseService.get_user_total_balance(user_email)
        # Consider balances > $0.01 or < -$0.01 as outstanding (to handle floating point)
        has_balance = abs(balance) > 0.01
        return has_balance, balance
