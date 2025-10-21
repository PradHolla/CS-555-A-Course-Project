"""Expense management routes blueprint."""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models import Expense, Group
from services.expense_service import ExpenseService
from services.notification_service import notify_expense_participants
from utils.decorators import login_required

expenses_bp = Blueprint("expenses", __name__)


@expenses_bp.route("/expense-splitter", methods=["GET", "POST"])
@login_required
def expense_splitter():
    """Handle expense splitter page - create and view expenses."""
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
        group = Group.query.get(group_id)
        if not group:
            flash("Selected group not found", "error")
            return redirect(url_for("expenses.expense_splitter"))

        # Parse group members
        group_members = [m.strip() for m in group.members.split(",") if m.strip()]

        # Validate payer is in group
        if payer not in group_members:
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
                if participant not in group_members:
                    flash(f"Participant '{participant}' is not in the selected group", "error")
                    return redirect(url_for("expenses.expense_splitter"))

            # Calculate equal split
            split_details = ExpenseService.calculate_equal_split(selected_participants, amount)

        else:  # custom split
            # Get custom split amounts
            split_details = {}
            for member in group_members:
                amount_key = f"custom_amount_{member}"
                custom_amount = request.form.get(amount_key, "").strip()
                if custom_amount:
                    try:
                        split_details[member] = float(custom_amount)
                    except ValueError:
                        flash(f"Invalid amount for {member}", "error")
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
            participants=", ".join(split_details.keys())  # Keep for backward compatibility
        )
        db.session.add(expense)
        db.session.commit()

        # Send email notifications to participants
        participant_list = list(split_details.keys())
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
        expenses = Expense.query.filter_by(group_id=selected_group_id).order_by(Expense.created_at.desc()).all()
    else:
        expenses = Expense.query.order_by(Expense.created_at.desc()).all()

    # Process expenses for display
    expense_views = []
    for expense in expenses:
        split_details = ExpenseService._parse_split_details(expense)
        participants = list(split_details.keys())
        share = list(split_details.values())[0] if len(split_details) == 1 and expense.split_type == "equal" else None
        expense_views.append({
            "model": expense,
            "participants": participants,
            "share": share,
            "split_details": split_details
        })

    # Convert groups to JSON-serializable format
    groups_data = [{"id": group.id, "name": group.name, "members": group.members} for group in groups]

    return render_template(
        "apps/expense_splitter/index.html",
        page_id="expense-splitter",
        expenses=expense_views,
        groups=groups,
        groups_data=groups_data,
        selected_group_id=selected_group_id
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

    # Get groups for the filter dropdown
    groups = Group.query.all()
    groups_data = [{"id": group.id, "name": group.name, "members": group.members} for group in groups]

    return render_template(
        "apps/expense_splitter/balance.html",
        page_id="balance-summary",
        balances=balance_data["balances"],
        transactions=balance_data["transactions"],
        groups=groups,
        groups_data=groups_data,
        selected_group_id=group_id
    )
