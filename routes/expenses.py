"""Expense management routes blueprint."""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models import Expense, Group, User
from services.expense_service import ExpenseService
from services.notification_service import notify_expense_participants
from utils.decorators import login_required

expenses_bp = Blueprint("expenses", __name__)


@expenses_bp.route("/expense-splitter", methods=["GET", "POST"])
@login_required
def expense_splitter():
    """Redirect to groups list - expenses are now group-specific."""
    # Redirect to groups list since expenses are now group-scoped
    return redirect(url_for("groups.list_groups"))


@expenses_bp.route("/expense-splitter-old", methods=["GET", "POST"])
@login_required
def expense_splitter_old():
    """Old expense splitter - kept for reference but redirects."""
    # Get all groups for the form
    groups = Group.query.all()

    if request.method == "POST":
        # Extract form data
        description = request.form.get("description", "").strip()
        amount_raw = request.form.get("amount", "").strip()
        payer = request.form.get("payer", "").strip()
        group_id = request.form.get("group_id", "").strip()
        split_type = request.form.get("split_type", "equal").strip()

        # Validate required fields
        if not description:
            flash("Description is required", "error")
            return redirect(url_for("expenses.expense_splitter"))

        if not group_id:
            flash("Please select a group", "error")
            return redirect(url_for("expenses.expense_splitter"))

        if not payer:
            flash("Payer is required", "error")
            return redirect(url_for("expenses.expense_splitter"))

        # Validate amount
        try:
            amount = float(amount_raw)
            if amount <= 0:
                flash("Amount must be greater than zero", "error")
                return redirect(url_for("expenses.expense_splitter"))
        except (ValueError, TypeError):
            flash("Please enter a valid amount", "error")
            return redirect(url_for("expenses.expense_splitter"))

        # Get selected group
        group = db.session.get(Group, group_id)
        if not group:
            flash("Selected group not found", "error")
            return redirect(url_for("expenses.expense_splitter"))

        # Get group member emails for validation
        group_member_emails = [member.email for member in group.members]

        # Validate payer is in group
        if payer not in group_member_emails:
            flash("Payer must be a member of the selected group", "error")
            return redirect(url_for("expenses.expense_splitter"))

        # Handle participants and split details
        if split_type == "equal":
            # Get selected participants for equal split
            selected_participants = request.form.getlist("participants")
            if not selected_participants:
                flash("Please select at least one participant", "error")
                return redirect(url_for("expenses.expense_splitter"))

            # Validate all participants are in group
            for participant in selected_participants:
                if participant not in group_member_emails:
                    flash(f"Participant '{participant}' is not in the selected group", "error")
                    return redirect(url_for("expenses.expense_splitter"))

            # Calculate equal split
            split_details = ExpenseService.calculate_equal_split(selected_participants, amount)

        else:  # custom split
            # Get custom split amounts
            split_details = {}
            for member_email in group_member_emails:
                amount_key = f"custom_amount_{member_email}"
                custom_amount = request.form.get(amount_key, "").strip()
                if custom_amount:
                    try:
                        split_details[member_email] = float(custom_amount)
                    except ValueError:
                        flash(f"Invalid amount for {member_email}", "error")
                        return redirect(url_for("expenses.expense_splitter"))

            if not split_details:
                flash("Please specify amounts for at least one participant", "error")
                return redirect(url_for("expenses.expense_splitter"))

            # Validate custom split
            is_valid, error_msg = ExpenseService.validate_custom_split(split_details, amount)
            if not is_valid:
                flash(error_msg, "error")
                return redirect(url_for("expenses.expense_splitter"))

        # Create expense
        expense = Expense(
            description=description,
            amount=amount,
            payer=payer,
            group_id=group_id,
            split_type=split_type,
            split_details=json.dumps(split_details),
            participants=", ".join(split_details.keys()),  # Keep for backward compatibility
        )
        db.session.add(expense)
        db.session.commit()

        # Send email notifications to participants (excluding the payer)
        participant_list = [email for email in split_details.keys() if email != payer]
        if participant_list:
            try:
                notify_expense_participants(expense, participant_list)
                print(f"Sent notifications to: {participant_list}")
            except Exception as e:
                print(f"Failed to send notifications: {e}")

        flash("Expense added successfully!", "success")
        return redirect(url_for("expenses.expense_splitter"))

    # GET request - show form and expenses
    selected_group_id = request.args.get("group_id")

    # Get expenses (filter by group if specified)
    if selected_group_id:
        expenses = (
            Expense.query.filter_by(group_id=selected_group_id)
            .order_by(Expense.created_at.desc())
            .all()
        )
    else:
        expenses = Expense.query.order_by(Expense.created_at.desc()).all()

    # Process expenses for display
    expense_views = []
    all_emails = set()
    for expense in expenses:
        split_details = ExpenseService._parse_split_details(expense)
        participants = list(split_details.keys())
        share = (
            list(split_details.values())[0]
            if len(split_details) == 1 and expense.split_type == "equal"
            else None
        )
        expense_views.append(
            {
                "model": expense,
                "participants": participants,
                "share": share,
                "split_details": split_details,
            }
        )
        # Collect all emails for display name lookup
        all_emails.add(expense.payer)
        all_emails.update(participants)

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

    # Convert groups to JSON-serializable format with member names
    groups_data = [
        {
            "id": group.id,
            "name": group.name,
            "members": [
                {
                    "email": m.email,
                    "display_name": m.display_name or m.email,
                }
                for m in group.members
            ],
        }
        for group in groups
    ]

    return render_template(
        "apps/expense_splitter/index.html",
        page_id="expense-splitter",
        expenses=expense_views,
        groups=groups,
        groups_data=groups_data,
        selected_group_id=selected_group_id,
        email_to_name=email_to_name,
    )


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

    # Create mapping of email to display name
    all_emails = set(balance_data["balances"].keys())
    for transaction in balance_data["transactions"]:
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
        email_to_name=email_to_name,
        groups=groups,
        groups_data=groups_data,
        selected_group_id=group_id,
    )
