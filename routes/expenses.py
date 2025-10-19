"""Expense management routes blueprint."""

from flask import Blueprint, redirect, render_template, request, url_for

from extensions import db
from models import Expense
from services.expense_service import ExpenseService
from utils.decorators import login_required

expenses_bp = Blueprint("expenses", __name__)


@expenses_bp.route("/expense-splitter", methods=["GET", "POST"])
@login_required
def expense_splitter():
    """Handle expense splitter page - create and view expenses."""
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        amount_raw = request.form.get("amount", "").strip()
        payer = request.form.get("payer", "").strip()
        participants = request.form.get("participants", "").strip()

        try:
            amount = float(amount_raw)
        except ValueError:
            amount = None

        if description and amount is not None and payer:
            expense = Expense(
                description=description,
                amount=amount,
                payer=payer,
                participants=participants or None,
            )
            db.session.add(expense)
            db.session.commit()

        return redirect(url_for("expenses.expense_splitter"))

    expenses = Expense.query.order_by(Expense.created_at.desc()).all()
    expense_views = []
    for expense in expenses:
        people = [p.strip() for p in (expense.participants or "").split(",") if p.strip()]
        share = expense.amount / len(people) if people else None
        expense_views.append({"model": expense, "participants": people, "share": share})

    return render_template(
        "apps/expense_splitter/index.html", page_id="expense-splitter", expenses=expense_views
    )


@expenses_bp.route("/balance-summary", methods=["GET"])
@login_required
def balance_summary():
    """Display balance summary showing who owes whom across all expenses."""
    # Get all expenses from the database
    expenses = Expense.query.all()

    # Calculate balances using the service
    balance_data = ExpenseService.calculate_balances(expenses)

    return render_template(
        "apps/expense_splitter/balance.html",
        page_id="balance-summary",
        balances=balance_data["balances"],
        transactions=balance_data["transactions"],
    )
