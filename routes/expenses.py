"""Expense management routes blueprint."""

from flask import Blueprint, redirect, render_template, request, url_for

from extensions import db
from models import Expense, Group, Settlement, User
from services.expense_service import ExpenseService
from services.settlement_service import SettlementService
from utils.decorators import login_required

expenses_bp = Blueprint("expenses", __name__)


@expenses_bp.route("/expense-splitter", methods=["GET", "POST"])
@login_required
def expense_splitter():
    """Redirect to groups list - expenses are now group-specific."""
    # Redirect to groups list since expenses are now group-scoped
    return redirect(url_for("groups.list_groups"))


@expenses_bp.route("/balance-summary", methods=["GET"])
@login_required
def balance_summary():
    """Display balance summary showing who owes whom across all expenses."""
    # Get group filter if specified
    group_id = request.args.get("group_id")

    # Get expenses (filter by group if specified)
    if group_id:
        expenses = Expense.query.filter_by(group_id=group_id).all()
    else:
        expenses = Expense.query.all()

    # Calculate balances using the service
    balance_data = ExpenseService.calculate_balances(expenses)

    # Calculate detailed breakdown (all pairwise debts)
    detailed_breakdown = ExpenseService.calculate_detailed_breakdown(expenses)
    
    # Get all settlements to adjust balances
    all_settlements = Settlement.query.all()
    
    # Create a copy of balances and adjust for settlements
    adjusted_balances = dict(balance_data["balances"])
    
    # Adjust each person's balance by subtracting settlements they paid and adding settlements they received
    for settlement in all_settlements:
        payer = db.session.get(User, settlement.payer_id)
        recipient = db.session.get(User, settlement.recipient_id)
        
        if payer and recipient:
            # Payer paid money, so their balance increases (less negative or more positive)
            adjusted_balances[payer.email] = adjusted_balances.get(payer.email, 0.0) + settlement.amount
            # Recipient received money, so their balance decreases (less positive or more negative)
            adjusted_balances[recipient.email] = adjusted_balances.get(recipient.email, 0.0) - settlement.amount
    
    # Adjust transactions for settlements - subtract settlements from debts
    adjusted_transactions = []
    for transaction in balance_data["transactions"]:
        # Get the actual current debt between these users (accounting for settlements)
        current_debt = SettlementService.get_debt_between_users(
            transaction["from"], 
            transaction["to"]
        )
        
        # Only include the transaction if there's still debt remaining
        if current_debt > 0.01:  # Use small epsilon for floating point comparison
            adjusted_transactions.append({
                "from": transaction["from"],
                "to": transaction["to"],
                "amount": current_debt,
                "expense_description": transaction.get("expense_description", ""),
            })
    
    # Also adjust detailed breakdown for settlements
    adjusted_detailed = []
    for transaction in detailed_breakdown:
        current_debt = SettlementService.get_debt_between_users(
            transaction["from"], 
            transaction["to"]
        )
        
        # Only include if there's remaining debt
        if current_debt > 0.01:
            adjusted_detailed.append({
                "from": transaction["from"],
                "to": transaction["to"],
                "amount": current_debt,
                "expense_description": transaction.get("expense_description", ""),
                "expense_id": transaction.get("expense_id"),
            })

    # Create mapping of email to display name
    all_emails = set(balance_data["balances"].keys())
    for transaction in adjusted_transactions:
        all_emails.add(transaction["from"])
        all_emails.add(transaction["to"])

    # Also include emails from detailed breakdown
    for transaction in adjusted_detailed:
        all_emails.add(transaction["from"])
        all_emails.add(transaction["to"])

    # Bulk fetch all users for the emails to avoid N+1 queries
    if all_emails:
        users = User.query.filter(User.email.in_(all_emails)).all()
        user_map = {user.email: user for user in users}
    else:
        users = []
        user_map = {}

    email_to_name = {}
    user_emails_to_ids = {}
    for email in all_emails:
        user = user_map.get(email)
        if user:
            email_to_name[email] = user.display_name or user.email
            user_emails_to_ids[email] = user.id
        else:
            email_to_name[email] = email  # Fallback to email if user not found

    # Get groups for the filter dropdown
    groups = Group.query.all()
    groups_data = [
        {"id": group.id, "name": group.name, "members": group.members} for group in groups
    ]

    return render_template(
        "apps/expense_splitter/balance.html",
        page_id="balance-summary",
        balances=adjusted_balances,
        transactions=adjusted_transactions,
        detailed_breakdown=adjusted_detailed,
        email_to_name=email_to_name,
        user_emails_to_ids=user_emails_to_ids,
        user_map=user_map,
        groups=groups,
        groups_data=groups_data,
        selected_group_id=group_id,
    )
