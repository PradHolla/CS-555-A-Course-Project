# Payment Confirmation Email Notification

## User Story
As a user, I want to receive an email notification when someone records a payment to me, so I can verify the transaction immediately.

## Acceptance Criteria
✔ Given a member settles a payment to me  
✔ When the transaction is saved  
✔ Then an email is sent with the message: "Neha has paid $500 to you."  
✔ Given I click the link in the email  
✔ Then I am redirected to the payment details page  

## Definition of Done
- ✅ Email notification sent successfully on payment settlement
- ✅ Email includes payer name, amount, and timestamp
- ✅ Redirection link works and opens correct transaction
- ✅ Feature tested with multiple group members

## Configuration

### Email Sending Control

The application uses an `EMAIL_ENABLED` flag to control whether **payment notification emails** are actually sent or just logged to the terminal.

**Important:** OTP (login) emails are ALWAYS sent regardless of this setting, so users can log in.

**In `.env` file:**
```env
# Set to 'true' to send payment notification emails, 'false' to print to terminal/log
# Note: OTP (login) emails are always sent regardless of this setting
EMAIL_ENABLED=false
```

### Email Service Configuration

For production email sending, configure your SMTP settings in `.env`:

```env
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
EMAIL_ENABLED=true
```

**Note:** For Gmail, you need to use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

## Usage

### Local Development / Testing

When `EMAIL_ENABLED=false` (default):
- Email content is printed to the terminal
- No actual emails are sent
- You can verify the email format and content in the console output

**Example terminal output:**
```
============================================================
EMAIL NOTIFICATION
============================================================
To: john@example.com
Subject: Neha has paid $500.00 to you
Timestamp: 2025-11-03 14:30:45

Neha has paid $500.00 to you.

Payment Details:
- Amount: $500.00
- Timestamp: 2025-11-03 14:30:45
- Note: Rent payment

View full payment details: http://localhost:5000/settlements/1
============================================================
```

### Production

When `EMAIL_ENABLED=true`:
- Actual emails are sent via the configured SMTP server
- Success/failure messages are logged
- Email content is also logged for debugging

## Email Content

### Plain Text Version
The email includes:
- Payer name (display name or email)
- Payment amount
- Timestamp of the transaction
- Optional note
- Link to payment details page

### HTML Version
The email also includes a formatted HTML version with:
- Styled header and content
- Highlighted payment details in a box
- Clickable button to view payment details
- Professional formatting

## Testing

Run the payment email notification tests:

```bash
pytest tests/test_payment_email_notification.py -v
```

Run all settlement-related tests:

```bash
pytest tests/test_settlement_notifications.py tests/test_payment_email_notification.py -v
```

## Implementation Details

### Files Modified/Created

1. **`.env`** - Added `EMAIL_ENABLED` configuration flag
2. **`app.py`** - Updated email configuration to read `EMAIL_ENABLED` flag
3. **`services/notification_service.py`** - Complete rewrite with:
   - `_send_or_log_email()` helper function
   - Email sending via Flask-Mail
   - Terminal logging for development
   - HTML email templates
   - Timestamp inclusion
4. **`tests/test_payment_email_notification.py`** - Comprehensive test suite
5. **`docs/PAYMENT_EMAIL_NOTIFICATION.md`** - This documentation

### Key Functions

**`notify_settlement_recipient(settlement)`**
- Called when a settlement is created
- Sends email to the payment recipient
- Includes all required information
- Handles both email sending and logging

**`_send_or_log_email(to_email, subject, body, html_body=None)`**
- Helper function that checks `EMAIL_ENABLED` flag
- Sends actual email if enabled
- Logs to terminal if disabled
- Handles errors gracefully

## Dependencies

The feature relies on:
- Flask-Mail for email sending
- SMTP server configuration (Gmail in this case)
- Environment variables for configuration

## Troubleshooting

### Emails not being sent in production

1. Check `EMAIL_ENABLED` is set to `true` in `.env`
2. Verify SMTP credentials are correct
3. For Gmail, ensure you're using an App Password
4. Check application logs for error messages

### Testing email format

1. Set `EMAIL_ENABLED=false`
2. Create a test settlement
3. Check terminal output for formatted email content
4. Verify all required fields are present

### Link not working

1. Ensure `_external=True` is used in `url_for()` calls
2. Check that the application is running on the expected domain
3. Verify settlement ID is correct in the URL

## Future Enhancements

Potential improvements:
- Email templates stored in separate files
- Support for multiple email providers
- Email queuing for better performance
- Unsubscribe functionality
- Email preferences per user
- Batch notifications for multiple payments
