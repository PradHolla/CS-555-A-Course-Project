from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from extensions import db
from models import Settlement
from services.notification_service import notify_settlement_recipient
from services.settlement_service import SettlementService
from utils.decorators import login_required

settlements_bp = Blueprint("settlements", __name__, url_prefix="/settlements")


@settlements_bp.route("", methods=["POST"])
@login_required
def create():
    """Create a settlement after validation."""
    try:
        amount = float(request.form.get("amount", "0") or 0.0)
        payer_id = int(request.form.get("payer_id"))
        recipient_id = int(request.form.get("recipient_id"))
        note = request.form.get("note") or None
    except (ValueError, TypeError):
        flash("Invalid settlement data provided.", "error")
        return redirect(url_for("expenses.balance_summary"))

    # Use settlement service to create with validation
    success, settlement, error = SettlementService.create_settlement(
        payer_id=payer_id, recipient_id=recipient_id, amount=amount, note=note
    )

    if not success:
        flash(error, "error")
        return redirect(url_for("expenses.balance_summary"))

    # Send notification
    notify_settlement_recipient(settlement)

    # Get user names for flash message
    payer_name = settlement.payer.display_name or settlement.payer.email
    recipient_name = settlement.recipient.display_name or settlement.recipient.email

    # Calculate remaining debt after this payment by checking current debt
    # (The settlement we just made is already factored into the balance)
    remaining_debt = SettlementService.get_debt_between_users(
        settlement.payer.email, settlement.recipient.email
    )

    # Build success message
    if remaining_debt > 0.01:  # Small epsilon for floating point comparison
        message = (
            f"✅ Partial payment recorded! {payer_name} paid ${amount:.2f} to {recipient_name}. "
            f"Remaining debt: ${remaining_debt:.2f}. "
            f"<a href='{url_for('settlements.detail', settlement_id=settlement.id)}' class='underline'>View details</a>"
        )
    else:
        message = (
            f"🎉 Payment recorded! {payer_name} paid ${amount:.2f} to {recipient_name}. "
            f"All settled up! "
            f"<a href='{url_for('settlements.detail', settlement_id=settlement.id)}' class='underline'>View details</a>"
        )

    flash(message, "success")
    return redirect(url_for("expenses.balance_summary"))


@settlements_bp.route("/<int:settlement_id>")
@login_required
def detail(settlement_id):
    s = db.session.get(Settlement, settlement_id)
    if not s:
        abort(404)
    return render_template("settlements/details.html", settlement=s)
