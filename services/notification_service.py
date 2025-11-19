import logging
from datetime import datetime

from flask import current_app, url_for
from flask_mail import Message

from extensions import mail

# Configure logging for email notifications
logger = logging.getLogger(__name__)


def _send_or_log_email(to_email, subject, body, html_body=None):
    """
    Send email if EMAIL_ENABLED is true, otherwise log to terminal and file.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: Optional HTML email body
    """
    email_enabled = current_app.config.get("EMAIL_ENABLED", False)

    # Format email content for logging
    log_content = (
        "\n" + "=" * 60 + "\n"
        f"EMAIL NOTIFICATION\n"
        f"{'=' * 60}\n"
        f"To: {to_email}\n"
        f"Subject: {subject}\n"
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"\n{body}\n"
        f"{'=' * 60}\n"
    )

    if email_enabled:
        # Send actual email
        try:
            msg = Message(subject=subject, recipients=[to_email], body=body, html=html_body)
            mail.send(msg)
            logger.info(f"Email sent successfully to {to_email}")
            print(f"✓ Email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            print(f"✗ Failed to send email to {to_email}: {str(e)}")
            # Log the content anyway for debugging
            print(log_content)
    else:
        # Log to terminal and file
        print(log_content)
        logger.info(f"Email notification logged (not sent): {to_email} - {subject}")


def notify_settlement_recipient(settlement):
    """
    Send payment confirmation email to the recipient when a settlement is recorded.

    Email includes:
    - Payer name
    - Amount paid
    - Timestamp
    - Link to payment details page
    - Optional note
    """
    payer, recipient = settlement.payer, settlement.recipient
    payer_name = payer.display_name or payer.email
    amount = settlement.amount
    timestamp = settlement.created_at.strftime("%Y-%m-%d %H:%M:%S")
    
    # Try to generate URL, fallback if not in request context
    try:
        detail_url = url_for("settlements.detail", settlement_id=settlement.id, _external=True)
    except RuntimeError:
        # Not in request context, use placeholder
        detail_url = f"/settlements/{settlement.id}"

    # Email subject
    subject = f"{payer_name} has paid ${amount:.2f} to you"

    # Plain text body
    body = (
        f"{payer_name} has paid ${amount:.2f} to you.\n\n"
        f"Payment Details:\n"
        f"- Amount: ${amount:.2f}\n"
        f"- Timestamp: {timestamp}\n"
        f"- Note: {settlement.note or 'No note provided'}\n\n"
        f"View full payment details: {detail_url}\n"
    )

    # HTML body for better formatting
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #4CAF50;">Payment Received</h2>
            <p><strong>{payer_name}</strong> has paid <strong>${amount:.2f}</strong> to you.</p>

            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Payment Details</h3>
                <p><strong>Amount:</strong> ${amount:.2f}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
                <p><strong>Note:</strong> {settlement.note or "No note provided"}</p>
            </div>

            <p>
                <a href="{detail_url}"
                   style="background-color: #4CAF50; color: white; padding: 10px 20px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Payment Details
                </a>
            </p>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This is an automated notification from your expense splitting application.
            </p>
        </body>
    </html>
    """

    _send_or_log_email(recipient.email, subject, body, html_body)


def notify_debtor_reminder(creditor, debtor, amount, breakdown=None):
    """
    Send payment reminder email to debtor from creditor.

    Args:
        creditor: User object who is owed money
        debtor: User object who owes money
        amount: Total amount owed (positive number)
        breakdown: Optional list of dicts with expense details
                   [{'description': str, 'amount': float, 'date': str}, ...]
    """
    creditor_name = creditor.display_name or creditor.email
    debtor_name = debtor.display_name or debtor.email
    balance_url = url_for("expenses.balance_summary", _external=True)

    # Email subject
    subject = f"Payment Reminder from {creditor_name}"

    # Build plain text body
    body_lines = [
        f"Hi {debtor_name},\n",
        f"This is a friendly reminder that you have an outstanding balance with {creditor_name}.\n",
        f"Amount Owed: ${abs(amount):.2f}\n",
    ]

    # Add expense breakdown if provided
    if breakdown and len(breakdown) > 0:
        body_lines.append("Expense Details:")
        for item in breakdown:
            expense_desc = item.get("description", "Expense")
            expense_amount = item.get("amount", 0)
            body_lines.append(f"  - {expense_desc}: ${expense_amount:.2f}")
        body_lines.append("")

    body_lines.extend([
        f"You can view your full balance and make a payment here:",
        f"{balance_url}\n",
        f"Thanks!",
        f"{creditor_name}",
    ])

    body = "\n".join(body_lines)

    # Build HTML body
    breakdown_html = ""
    if breakdown and len(breakdown) > 0:
        breakdown_items = ""
        for item in breakdown:
            expense_desc = item.get("description", "Expense")
            expense_amount = item.get("amount", 0)
            breakdown_items += f"<li><strong>{expense_desc}</strong>: ${expense_amount:.2f}</li>"
        
        breakdown_html = f"""
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; 
                        border-left: 4px solid #ffc107; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #856404;">Expense Details</h3>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    {breakdown_items}
                </ul>
            </div>
        """

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #FF9800;">Payment Reminder</h2>
            <p>Hi <strong>{debtor_name}</strong>,</p>
            <p>This is a friendly reminder that you have an outstanding balance with <strong>{creditor_name}</strong>.</p>

            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #FF9800;">Amount Owed</h3>
                <p style="font-size: 24px; font-weight: bold; color: #FF5722; margin: 10px 0;">
                    ${abs(amount):.2f}
                </p>
            </div>

            {breakdown_html}

            <p>
                <a href="{balance_url}"
                   style="background-color: #FF9800; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 5px; display: inline-block;
                          font-weight: bold;">
                    View Balance & Make Payment
                </a>
            </p>

            <p style="margin-top: 30px;">Thanks!<br><strong>{creditor_name}</strong></p>

            <p style="color: #666; font-size: 12px; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 15px;">
                This is a payment reminder sent through your expense splitting application.
            </p>
        </body>
    </html>
    """

    _send_or_log_email(debtor.email, subject, body, html_body)


def notify_expense_participants(expense, participant_emails):
    """Send notification to all participants when an expense is added."""
    subject = f"New expense added: {expense.description}"
    timestamp = expense.created_at.strftime("%Y-%m-%d %H:%M:%S")

    body = (
        f"A new expense has been added:\n\n"
        f"Description: {expense.description}\n"
        f"Amount: ${expense.amount:.2f}\n"
        f"Paid by: {expense.payer}\n"
        f"Participants: {expense.participants or 'Not specified'}\n"
        f"Timestamp: {timestamp}\n"
    )

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2196F3;">New Expense Added</h2>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Description:</strong> {expense.description}</p>
                <p><strong>Amount:</strong> ${expense.amount:.2f}</p>
                <p><strong>Paid by:</strong> {expense.payer}</p>
                <p><strong>Participants:</strong> {expense.participants or "Not specified"}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
            </div>
        </body>
    </html>
    """

    for email in participant_emails:
        _send_or_log_email(email, subject, body, html_body)


def notify_group_invitation(inviter_email, invitee_email, group_name):
    """Send notification when a user is invited to a group."""
    subject = f"You've been invited to join '{group_name}'"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    body = (
        f"{inviter_email} has invited you to join the group '{group_name}'.\n\n"
        f"When you sign up or log in, you'll automatically be added to this group.\n"
        f"Timestamp: {timestamp}\n"
    )

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #FF9800;">Group Invitation</h2>
            <p><strong>{inviter_email}</strong> has invited you to join the group <strong>'{group_name}'</strong>.</p>
            <p>When you sign up or log in, you'll automatically be added to this group.</p>
            <p style="color: #666; font-size: 12px;">Timestamp: {timestamp}</p>
        </body>
    </html>
    """

    _send_or_log_email(invitee_email, subject, body, html_body)


def notify_expense_deletion(expense, deleter_email, group_members):
    """Send notification to group members when an expense is deleted."""
    subject = f"Expense deleted: {expense.description}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    body = (
        f"An expense has been deleted from your group:\n\n"
        f"Description: {expense.description}\n"
        f"Amount: ${expense.amount:.2f}\n"
        f"Paid by: {expense.payer}\n"
        f"Deleted by: {deleter_email}\n"
        f"Timestamp: {timestamp}\n"
    )

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #f44336;">Expense Deleted</h2>
            <p>An expense has been deleted from your group:</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Description:</strong> {expense.description}</p>
                <p><strong>Amount:</strong> ${expense.amount:.2f}</p>
                <p><strong>Paid by:</strong> {expense.payer}</p>
                <p><strong>Deleted by:</strong> {deleter_email}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
            </div>
        </body>
    </html>
    """

    for member in group_members:
        if member.email != deleter_email:
            _send_or_log_email(member.email, subject, body, html_body)


def notify_expense_edited(expense, editor_email, group_members):
    """Send notification to group members when an expense is edited."""
    subject = f"Expense edited: {expense.description}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    body = (
        f"An expense has been edited in your group:\n\n"
        f"Description: {expense.description}\n"
        f"Amount: ${expense.amount:.2f}\n"
        f"Paid by: {expense.payer}\n"
        f"Participants: {expense.participants or 'Not specified'}\n"
        f"Edited by: {editor_email}\n"
        f"Timestamp: {timestamp}\n"
    )

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #FF9800;">Expense Edited</h2>
            <p>An expense has been edited in your group:</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Description:</strong> {expense.description}</p>
                <p><strong>Amount:</strong> ${expense.amount:.2f}</p>
                <p><strong>Paid by:</strong> {expense.payer}</p>
                <p><strong>Participants:</strong> {expense.participants or "Not specified"}</p>
                <p><strong>Edited by:</strong> {editor_email}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
            </div>
        </body>
    </html>
    """

    for member in group_members:
        if member.email != editor_email:
            _send_or_log_email(member.email, subject, body, html_body)


def send_payment_reminder(user, balance_amount, days_outstanding, balance_breakdown):
    """
    Send payment reminder email to user with outstanding balance.

    Args:
        user: User object with email and display_name
        balance_amount: Negative balance amount (how much user owes)
        days_outstanding: Number of days balance has been outstanding
        balance_breakdown: List of dicts with creditor and amount
    """
    try:
        # Validate inputs
        if not user or not user.email:
            raise ValueError("Invalid user object")
        if not balance_breakdown:
            raise ValueError("Balance breakdown is required")
        if days_outstanding < 0:
            raise ValueError("Days outstanding must be non-negative")

        user_name = user.display_name or user.email
        total_amount = abs(balance_amount)  # Convert negative to positive for display
        
        # Generate balance page URL (works without request context)
        balance_url = current_app.config.get("APP_URL", "http://localhost:5000") + "/balance-summary"

        # Create subject line
        subject = f"Payment Reminder: Outstanding Balance of ${total_amount:.2f}"

        # Create balance summary text
        breakdown_text = "\n".join(
            [f"  • {debt['creditor']}: ${debt['amount']:.2f}" for debt in balance_breakdown]
        )

        # Create plain text email body
        plain_body = f"""Hi {user_name},

This is a friendly reminder that you have an outstanding balance of ${total_amount:.2f}.

This balance has been outstanding for {days_outstanding} days.

Balance Breakdown:
{breakdown_text}

Please settle your balance at your earliest convenience.

You can view your detailed balance and make payments at: {balance_url}

This is an automated reminder from your expense splitting application.
"""

        # Create HTML email body
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .content {{ background: #f9f9f9; padding: 25px; margin: 20px 0; border-radius: 8px; }}
        .amount {{ font-size: 28px; font-weight: bold; color: #e53e3e; text-align: center; margin: 20px 0; }}
        .breakdown {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px;
                     border-left: 4px solid #667eea; }}
        .breakdown-item {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
        .breakdown-item:last-child {{ border-bottom: none; }}
        .button {{ background: #667eea; color: white; padding: 15px 30px;
                  text-decoration: none; border-radius: 8px; display: inline-block;
                  font-weight: bold; margin: 20px 0; }}
        .footer {{ color: #666; font-size: 12px; text-align: center; margin-top: 30px; }}
        .days-badge {{ background: #fed7d7; color: #c53030; padding: 5px 10px;
                      border-radius: 15px; font-size: 14px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>💰 Payment Reminder</h2>
        </div>

        <div class="content">
            <p>Hi <strong>{user_name}</strong>,</p>

            <p>This is a friendly reminder that you have an outstanding balance:</p>

            <div class="amount">${total_amount:.2f}</div>

            <p style="text-align: center;">
                <span class="days-badge">{days_outstanding} days outstanding</span>
            </p>

            <div class="breakdown">
                <h3 style="margin-top: 0; color: #667eea;">💳 Balance Breakdown:</h3>
                {''.join([f'<div class="breakdown-item"><strong>{debt["creditor"]}</strong>: ${debt["amount"]:.2f}</div>' for debt in balance_breakdown])}
            </div>

            <p>Please settle your balance at your earliest convenience to keep your account in good standing.</p>

            <div style="text-align: center;">
                <a href="{balance_url}" class="button">
                    📊 View Balance Details & Pay
                </a>
            </div>
        </div>

        <div class="footer">
            <p>This is an automated reminder from your expense splitting application.</p>
            <p>If you have questions, please contact your group administrator.</p>
        </div>
    </div>
</body>
</html>"""

        # Send email using existing notification infrastructure
        _send_or_log_email(
            to_email=user.email, subject=subject, body=plain_body, html_body=html_body
        )

        logger.info(f"Payment reminder sent to {user.email} for ${total_amount:.2f}")

    except Exception as e:
        user_email = user.email if user and hasattr(user, 'email') else 'unknown'
        logger.error(f"Failed to send payment reminder to {user_email}: {str(e)}")
        raise
