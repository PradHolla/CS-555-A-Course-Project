from flask import url_for, current_app
from flask_mail import Message
from extensions import mail

def notify_settlement_recipient(settlement):
    payer, recipient = settlement.payer, settlement.recipient
    subject = f"{payer.name} has paid ${settlement.amount:.2f} to you"
    detail_url = url_for('settlements.detail', settlement_id=settlement.id, _external=True)
    body = (
        f"{payer.name} has paid ${settlement.amount:.2f} to you.\n\n"
        f"Note: {settlement.note or '-'}\n"
        f"View details: {detail_url}\n"
    )
    msg = Message(
        subject=subject,
        recipients=[recipient.email],
        body=body,
        sender=current_app.config.get("MAIL_DEFAULT_SENDER", "no-reply@sprintpay.local"),
    )
    mail.send(msg)


def notify_expense_participants(expense, participant_emails):
    """Send email notification to all participants when an expense is added."""
    subject = f"New expense added: {expense.description}"
    body = (
        f"A new expense has been added:\n\n"
        f"Description: {expense.description}\n"
        f"Amount: ${expense.amount:.2f}\n"
        f"Paid by: {expense.payer}\n"
        f"Participants: {expense.participants or 'Not specified'}\n"
    )
    
    for email in participant_emails:
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body,
            sender=current_app.config.get("MAIL_DEFAULT_SENDER", "no-reply@sprintpay.local"),
        )
        mail.send(msg)
