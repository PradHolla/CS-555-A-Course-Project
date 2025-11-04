"""Expense management routes blueprint."""

from flask import Blueprint, redirect, render_template, request, url_for

from models import Expense, Group, User
from services.expense_service import ExpenseService
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

    # Create mapping of email to display name
    all_emails = set(balance_data["balances"].keys())
    for transaction in balance_data["transactions"]:
        all_emails.add(transaction["from"])
        all_emails.add(transaction["to"])
    
    # Also include emails from detailed breakdown
    for transaction in detailed_breakdown:
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
    for email in all_emails:
        user = user_map.get(email)
        if user:
            email_to_name[email] = user.display_name or user.email
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
        balances=balance_data["balances"],
        transactions=balance_data["transactions"],
        detailed_breakdown=detailed_breakdown,
        email_to_name=email_to_name,
        groups=groups,
        groups_data=groups_data,
        selected_group_id=group_id,
    )
