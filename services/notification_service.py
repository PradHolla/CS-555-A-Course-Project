from flask import url_for


def notify_settlement_recipient(settlement):
    payer, recipient = settlement.payer, settlement.recipient
    payer_name = payer.display_name or payer.email
    subject = f"{payer_name} has paid ${settlement.amount:.2f} to you"
    detail_url = url_for("settlements.detail", settlement_id=settlement.id, _external=True)
    body = (
        f"{payer_name} has paid ${settlement.amount:.2f} to you.\n\n"
        f"Note: {settlement.note or '-'}\n"
        f"View details: {detail_url}\n"
    )

    # Print notification to terminal instead of sending email
    print("\n" + "=" * 60)
    print("SETTLEMENT NOTIFICATION")
    print("=" * 60)
    print(f"To: {recipient.email}")
    print(f"Subject: {subject}")
    print(f"\n{body}")
    print("=" * 60 + "\n")


def notify_expense_participants(expense, participant_emails):
    """Print notification to terminal for all participants when an expense is added."""
    subject = f"New expense added: {expense.description}"
    body = (
        f"A new expense has been added:\n\n"
        f"Description: {expense.description}\n"
        f"Amount: ${expense.amount:.2f}\n"
        f"Paid by: {expense.payer}\n"
        f"Participants: {expense.participants or 'Not specified'}\n"
    )

    # Print notification to terminal instead of sending email
    for email in participant_emails:
        print("\n" + "=" * 60)
        print("EXPENSE NOTIFICATION")
        print("=" * 60)
        print(f"To: {email}")
        print(f"Subject: {subject}")
        print(f"\n{body}")
        print("=" * 60 + "\n")
