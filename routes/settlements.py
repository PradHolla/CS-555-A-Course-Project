from flask import Blueprint, request, redirect, url_for, render_template, flash
from utils.decorators import login_required
from extensions import db
from models import Settlement
from services.notification_service import notify_settlement_recipient

settlements_bp = Blueprint('settlements', __name__, url_prefix='/settlements')

@settlements_bp.route('', methods=['POST'])
@login_required
def create():
    amount = float(request.form.get('amount', '0') or 0.0)
    payer_id = int(request.form.get('payer_id'))
    recipient_id = int(request.form.get('recipient_id'))
    note = request.form.get('note') or None

    s = Settlement(amount=amount, payer_id=payer_id, recipient_id=recipient_id, note=note)
    db.session.add(s)
    db.session.commit()

    notify_settlement_recipient(s)

    flash(
        f"Payment recorded. {s.payer.name} paid ${amount:.2f} to you. "
        f"<a href='{url_for('settlements.detail', settlement_id=s.id)}'>View details</a>",
        "success"
    )
    return redirect(url_for('expenses.expense_splitter'))

@settlements_bp.route('/<int:settlement_id>')
@login_required
def detail(settlement_id):
    s = Settlement.query.get_or_404(settlement_id)
    return render_template('settlements/details.html', settlement=s)
