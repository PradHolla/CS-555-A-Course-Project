"""
Tests for Payment Confirmation Email Notification feature.

User Story: As a user, I want to receive an email notification when someone
records a payment to me, so I can verify the transaction immediately.

Acceptance Criteria:
✔ Given a member settles a payment to me
✔ When the transaction is saved
✔ Then an email is sent with the message: "Neha has paid $500 to you."
✔ Given I click the link in the email
✔ Then I am redirected to the payment details page
"""

from unittest.mock import patch

from extensions import db
from models import Settlement, User


def test_payment_email_includes_all_required_fields(client, app):
    """
    Test that payment confirmation email includes payer name, amount,
    timestamp, and link to payment details.

    Definition of Done:
    - Email includes payer name, amount, and timestamp
    - Redirection link works and opens correct transaction
    """
    with app.app_context():
        from models import Expense

        payer = User(email="neha@example.com", display_name="Neha")
        recipient = User(email="john@example.com", display_name="John")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

        # Create an expense so there's a debt to settle
        expense = Expense(
            description="Shared expense",
            amount=1000.00,
            payer=recipient.email,
            participants=f"{payer.email}, {recipient.email}",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    with patch("services.notification_service._send_or_log_email") as mock_send:
        client.post(
            "/settlements",
            data={
                "amount": "500.00",
                "payer_id": payer_id,
                "recipient_id": recipient_id,
                "note": "Rent payment",
            },
        )

        # Assert email was sent
        assert mock_send.called
        call_args = mock_send.call_args

        # Verify recipient
        assert call_args[0][0] == "john@example.com"

        # Verify subject contains payer name and amount
        subject = call_args[0][1]
        assert "Neha" in subject
        assert "$500.00" in subject

        # Verify body contains all required fields
        body = call_args[0][2]
        assert "Neha" in body
        assert "$500.00" in body
        assert "Timestamp:" in body
        assert "/settlements/" in body
        assert "Rent payment" in body


def test_email_enabled_flag_controls_actual_sending(app):
    """
    Test that EMAIL_ENABLED config flag controls whether emails are
    actually sent or just logged.
    """
    with app.app_context():
        with app.test_request_context():
            payer = User(email="alice@example.com")
            recipient = User(email="bob@example.com")
            db.session.add_all([payer, recipient])
            db.session.commit()

            settlement = Settlement(
                amount=250.00, payer_id=payer.id, recipient_id=recipient.id, note="Test payment"
            )
            db.session.add(settlement)
            db.session.commit()

            from services.notification_service import notify_settlement_recipient

            # Test with EMAIL_ENABLED = False (should log to terminal)
            app.config["EMAIL_ENABLED"] = False
            with patch("builtins.print") as mock_print:
                notify_settlement_recipient(settlement)
                assert mock_print.called
                printed_output = " ".join(str(call) for call in mock_print.call_args_list)
                assert "EMAIL NOTIFICATION" in printed_output
                assert "bob@example.com" in printed_output


def test_email_enabled_true_sends_actual_email(app):
    """
    Test that when EMAIL_ENABLED is true, actual email is sent via Flask-Mail.
    """
    with app.app_context():
        with app.test_request_context():
            payer = User(email="charlie@example.com", display_name="Charlie")
            recipient = User(email="diana@example.com")
            db.session.add_all([payer, recipient])
            db.session.commit()

            settlement = Settlement(amount=100.00, payer_id=payer.id, recipient_id=recipient.id)
            db.session.add(settlement)
            db.session.commit()

            from services.notification_service import notify_settlement_recipient

            # Test with EMAIL_ENABLED = True (should send email)
            app.config["EMAIL_ENABLED"] = True
            with patch("services.notification_service.mail.send") as mock_mail_send:
                notify_settlement_recipient(settlement)
                assert mock_mail_send.called

                # Verify Message object was created correctly
                msg = mock_mail_send.call_args[0][0]
                assert msg.recipients == ["diana@example.com"]
                assert "Charlie" in msg.subject
                assert "$100.00" in msg.subject


def test_email_html_body_formatted_correctly(app):
    """
    Test that HTML email body is properly formatted with all details.
    """
    with app.app_context():
        with app.test_request_context():
            payer = User(email="eve@example.com", display_name="Eve")
            recipient = User(email="frank@example.com")
            db.session.add_all([payer, recipient])
            db.session.commit()

            settlement = Settlement(
                amount=750.50, payer_id=payer.id, recipient_id=recipient.id, note="Utilities split"
            )
            db.session.add(settlement)
            db.session.commit()

            from services.notification_service import notify_settlement_recipient

            app.config["EMAIL_ENABLED"] = True
            with patch("services.notification_service.mail.send") as mock_mail_send:
                notify_settlement_recipient(settlement)

                msg = mock_mail_send.call_args[0][0]
                html_body = msg.html

                # Verify HTML contains all required elements
                assert "Eve" in html_body
                assert "$750.50" in html_body
                assert "Utilities split" in html_body
                assert "View Payment Details" in html_body
                assert "/settlements/" in html_body
                assert "href=" in html_body  # Link is present


def test_email_link_redirects_to_correct_payment_details(client, app):
    """
    Test that clicking the email link redirects to the correct payment details page.

    Acceptance Criteria:
    ✔ Given I click the link in the email
    ✔ Then I am redirected to the payment details page
    """
    with app.app_context():
        payer = User(email="grace@example.com")
        recipient = User(email="henry@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()

        settlement = Settlement(amount=300.00, payer_id=payer.id, recipient_id=recipient.id)
        db.session.add(settlement)
        db.session.commit()
        settlement_id = settlement.id
        recipient_id = recipient.id

    # Simulate clicking the link from email
    with client.session_transaction() as sess:
        sess["user_id"] = recipient_id

    response = client.get(f"/settlements/{settlement_id}")

    # Assert page loads successfully
    assert response.status_code == 200
    assert b"grace@example.com" in response.data
    assert b"300.00" in response.data


def test_email_sent_on_settlement_creation(client, app):
    """
    Test that email notification is triggered when settlement is saved.

    Acceptance Criteria:
    ✔ Given a member settles a payment to me
    ✔ When the transaction is saved
    ✔ Then an email is sent
    """
    with app.app_context():
        from models import Expense

        payer = User(email="iris@example.com")
        recipient = User(email="jack@example.com")
        db.session.add_all([payer, recipient])
        db.session.commit()
        payer_id = payer.id
        recipient_id = recipient.id

        # Create an expense so there's a debt to settle
        expense = Expense(
            description="Shared expense",
            amount=900.00,
            payer=recipient.email,
            participants=f"{payer.email}, {recipient.email}",
            split_type="equal",
        )
        db.session.add(expense)
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    with patch("services.notification_service._send_or_log_email") as mock_send:
        response = client.post(
            "/settlements",
            data={
                "amount": "450.00",
                "payer_id": payer_id,
                "recipient_id": recipient_id,
            },
        )

        # Assert settlement was created
        assert response.status_code == 302

        # Assert email was sent
        assert mock_send.called
        assert mock_send.call_args[0][0] == "jack@example.com"


def test_terminal_output_format_when_email_disabled(app):
    """
    Test that terminal output is properly formatted when EMAIL_ENABLED is false.

    During local testing, email content should be printed to terminal
    with clear formatting.
    """
    with app.app_context():
        with app.test_request_context():
            payer = User(email="kate@example.com", display_name="Kate")
            recipient = User(email="leo@example.com")
            db.session.add_all([payer, recipient])
            db.session.commit()

            settlement = Settlement(
                amount=125.75, payer_id=payer.id, recipient_id=recipient.id, note="Lunch"
            )
            db.session.add(settlement)
            db.session.commit()

            from services.notification_service import notify_settlement_recipient

            app.config["EMAIL_ENABLED"] = False
            with patch("builtins.print") as mock_print:
                notify_settlement_recipient(settlement)

                # Verify terminal output is formatted
                printed_calls = [str(call) for call in mock_print.call_args_list]
                printed_output = " ".join(printed_calls)

                assert "EMAIL NOTIFICATION" in printed_output
                assert "To: leo@example.com" in printed_output
                assert "Subject:" in printed_output
                assert "Kate" in printed_output
                assert "$125.75" in printed_output
                assert "Timestamp:" in printed_output
                assert "Lunch" in printed_output


def test_email_error_handling(app):
    """
    Test that email sending errors are handled gracefully and logged.
    """
    with app.app_context():
        with app.test_request_context():
            payer = User(email="mary@example.com")
            recipient = User(email="nathan@example.com")
            db.session.add_all([payer, recipient])
            db.session.commit()

            settlement = Settlement(amount=200.00, payer_id=payer.id, recipient_id=recipient.id)
            db.session.add(settlement)
            db.session.commit()

            from services.notification_service import notify_settlement_recipient

            app.config["EMAIL_ENABLED"] = True

            # Simulate email sending failure
            with patch("services.notification_service.mail.send") as mock_mail_send:
                mock_mail_send.side_effect = Exception("SMTP connection failed")

                with patch("builtins.print") as mock_print:
                    # Should not raise exception
                    notify_settlement_recipient(settlement)

                    # Should log error
                    printed_output = " ".join(str(call) for call in mock_print.call_args_list)
                    assert (
                        "Failed to send email" in printed_output
                        or "SMTP connection failed" in printed_output
                    )


def test_multiple_payments_send_separate_emails(client, app):
    """
    Test that multiple settlements send separate email notifications.

    Definition of Done:
    - Feature tested with multiple group members
    """
    with app.app_context():
        from models import Expense

        payer = User(email="olivia@example.com")
        recipient1 = User(email="paul@example.com")
        recipient2 = User(email="quinn@example.com")
        db.session.add_all([payer, recipient1, recipient2])
        db.session.commit()
        payer_id = payer.id
        recipient1_id = recipient1.id
        recipient2_id = recipient2.id

        # Create expenses so there are debts to settle
        expense1 = Expense(
            description="Expense 1",
            amount=200.00,
            payer=recipient1.email,
            participants=f"{payer.email}, {recipient1.email}",
            split_type="equal",
        )
        expense2 = Expense(
            description="Expense 2",
            amount=400.00,
            payer=recipient2.email,
            participants=f"{payer.email}, {recipient2.email}",
            split_type="equal",
        )
        db.session.add_all([expense1, expense2])
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer_id

    with patch("services.notification_service._send_or_log_email") as mock_send:
        # Create first settlement
        client.post(
            "/settlements",
            data={
                "amount": "100.00",
                "payer_id": payer_id,
                "recipient_id": recipient1_id,
            },
        )

        # Create second settlement
        client.post(
            "/settlements",
            data={
                "amount": "200.00",
                "payer_id": payer_id,
                "recipient_id": recipient2_id,
            },
        )

        # Assert two separate emails were sent
        assert mock_send.call_count == 2

        # Verify each email went to correct recipient
        call_args_list = [call[0] for call in mock_send.call_args_list]
        recipients = [args[0] for args in call_args_list]
        assert "paul@example.com" in recipients
        assert "quinn@example.com" in recipients
