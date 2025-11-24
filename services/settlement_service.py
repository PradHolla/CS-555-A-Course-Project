"""Business logic for settlement validation and processing."""

from extensions import db
from models import Expense, Settlement, User
from services.expense_service import ExpenseService


class SettlementService:
    """Service class for settlement validation and calculations."""

    @staticmethod
    def get_debt_between_users(payer_email: str, recipient_email: str) -> float:
        """
        Calculate how much payer owes to recipient based on expenses minus settlements.

        Uses the balance calculation logic and then subtracts any settlements already made.
        Returns positive amount if payer owes recipient, negative if recipient owes payer.

        Args:
            payer_email: Email of the person who would make the payment
            recipient_email: Email of the person who would receive the payment

        Returns:
            float: Amount payer owes recipient (positive = payer owes, negative = recipient owes)
        """
        # Get all expenses to calculate current balances
        expenses = Expense.query.all()

        # Calculate detailed breakdown to find specific debt between these two users from expenses
        detailed_breakdown = ExpenseService.calculate_detailed_breakdown(expenses)

        # Find gross debt from expenses (before settlements)
        gross_debt = 0.0
        for transaction in detailed_breakdown:
            if transaction["from"] == payer_email and transaction["to"] == recipient_email:
                gross_debt = transaction["amount"]
                break

        # Get payer and recipient user IDs
        payer = User.query.filter_by(email=payer_email).first()
        recipient = User.query.filter_by(email=recipient_email).first()

        if not payer or not recipient:
            return 0.0

        # Calculate total settlements already made from payer to recipient
        settlements_paid = (
            db.session.query(db.func.sum(Settlement.amount))
            .filter(Settlement.payer_id == payer.id, Settlement.recipient_id == recipient.id)
            .scalar()
            or 0.0
        )

        # Net debt = gross debt from expenses - settlements already paid
        net_debt = gross_debt - settlements_paid

        return max(0.0, net_debt)  # Can't owe negative amount

    @staticmethod
    def validate_settlement(payer_id: int, recipient_id: int, amount: float) -> dict:
        """
        Validate a proposed settlement between two users.

        Args:
            payer_id: User ID of the person making payment
            recipient_id: User ID of the person receiving payment
            amount: Proposed settlement amount

        Returns:
            dict: {
                'valid': bool,
                'error': str or None,
                'current_debt': float,
                'payer_email': str,
                'recipient_email': str
            }
        """
        # Validate amount is positive
        if amount <= 0:
            return {
                "valid": False,
                "error": "Settlement amount must be greater than $0.00",
                "current_debt": 0.0,
                "payer_email": None,
                "recipient_email": None,
            }

        # Get user objects
        payer = db.session.get(User, payer_id)
        recipient = db.session.get(User, recipient_id)

        if not payer or not recipient:
            return {
                "valid": False,
                "error": "Invalid payer or recipient",
                "current_debt": 0.0,
                "payer_email": None,
                "recipient_email": None,
            }

        # Prevent settling with yourself
        if payer_id == recipient_id:
            return {
                "valid": False,
                "error": "Cannot settle a payment with yourself",
                "current_debt": 0.0,
                "payer_email": payer.email,
                "recipient_email": recipient.email,
            }

        # Calculate current debt
        current_debt = SettlementService.get_debt_between_users(payer.email, recipient.email)

        # Check if there's any debt
        if current_debt <= 0:
            return {
                "valid": False,
                "error": f"No debt exists. {payer.display_name or payer.email} does not owe {recipient.display_name or recipient.email} any money.",
                "current_debt": 0.0,
                "payer_email": payer.email,
                "recipient_email": recipient.email,
            }

        # Check if amount exceeds debt
        if amount > current_debt:
            return {
                "valid": False,
                "error": f"Settlement amount ${amount:.2f} exceeds the owed amount of ${current_debt:.2f}",
                "current_debt": current_debt,
                "payer_email": payer.email,
                "recipient_email": recipient.email,
            }

        # Valid settlement
        return {
            "valid": True,
            "error": None,
            "current_debt": current_debt,
            "payer_email": payer.email,
            "recipient_email": recipient.email,
        }

    @staticmethod
    def create_settlement(
        payer_id: int, recipient_id: int, amount: float, note: str = None
    ) -> tuple:
        """
        Create a settlement after validation.

        Args:
            payer_id: User ID of the person making payment
            recipient_id: User ID of the person receiving payment
            amount: Settlement amount
            note: Optional note for the settlement

        Returns:
            tuple: (success: bool, settlement: Settlement or None, error: str or None)
        """
        # Validate settlement
        validation = SettlementService.validate_settlement(payer_id, recipient_id, amount)

        if not validation["valid"]:
            return (False, None, validation["error"])

        # Create settlement
        settlement = Settlement(
            amount=amount, payer_id=payer_id, recipient_id=recipient_id, note=note
        )

        db.session.add(settlement)
        db.session.commit()

        return (True, settlement, None)
