import logging
import os
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
            msg = Message(
                subject=subject,
                recipients=[to_email],
                body=body,
                html=html_body
            )
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
    timestamp = settlement.created_at.strftime('%Y-%m-%d %H:%M:%S')
    detail_url = url_for("settlements.detail", settlement_id=settlement.id, _external=True)
    
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
                <p><strong>Note:</strong> {settlement.note or 'No note provided'}</p>
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


def notify_expense_participants(expense, participant_emails):
    """Send notification to all participants when an expense is added."""
    subject = f"New expense added: {expense.description}"
    timestamp = expense.created_at.strftime('%Y-%m-%d %H:%M:%S')
    
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
                <p><strong>Participants:</strong> {expense.participants or 'Not specified'}</p>
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
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
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
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
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
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
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
                <p><strong>Participants:</strong> {expense.participants or 'Not specified'}</p>
                <p><strong>Edited by:</strong> {editor_email}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
            </div>
        </body>
    </html>
    """

    for member in group_members:
        if member.email != editor_email:
            _send_or_log_email(member.email, subject, body, html_body)