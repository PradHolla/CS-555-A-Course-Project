# Quick Start: Payment Email Notification

## What's New?
When someone records a payment to you, you'll receive an email notification with:
- Payer name
- Amount paid
- Timestamp
- Link to view payment details

**Important:** OTP (login) emails work normally and are not affected by this feature.

## Setup (5 minutes)

### For Local Testing (Default - No Setup Needed!)
The feature is already configured to print emails to your terminal. Just run the app:

```bash
python app.py
```

When a payment is created, you'll see the email content in your terminal like this:

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

### For Production (Actual Email Sending)

1. **Get Gmail App Password** (if using Gmail):
   - Go to Google Account → Security
   - Enable 2-Step Verification
   - Generate an App Password
   - Copy the 16-character password

2. **Update `.env` file**:
   ```env
   EMAIL_ENABLED=true
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-16-char-app-password
   ```

3. **Restart the app**:
   ```bash
   python app.py
   ```

That's it! Emails will now be sent for real.

## Try It Out

### Run the Demo
```bash
python demo_payment_notification.py
```

This creates a test payment and shows you the email that would be sent.

### Create a Test Payment
1. Start the app: `python app.py`
2. Log in to the application
3. Go to settlements/payments
4. Record a payment
5. Check your terminal (or email if enabled)

## Testing

Run the tests to verify everything works:

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run tests
python -m pytest tests/test_payment_email_notification.py -v
```

All 9 tests should pass ✅

## Switching Between Modes

### Switch to Terminal Mode (Development)
In `.env`:
```env
EMAIL_ENABLED=false
```

### Switch to Email Mode (Production)
In `.env`:
```env
EMAIL_ENABLED=true
```

No code changes needed - just update the config!

## Troubleshooting

### Emails not showing in terminal?
- Check that `EMAIL_ENABLED=false` in `.env`
- Look for the "EMAIL NOTIFICATION" header in your terminal output

### Emails not being sent in production?
- Verify `EMAIL_ENABLED=true` in `.env`
- Check your Gmail credentials are correct
- Make sure you're using an App Password, not your regular password
- Check the terminal for error messages

### Link in email not working?
- The link uses `localhost` in development
- In production, configure `SERVER_NAME` in Flask config

## What Happens When?

| Action | EMAIL_ENABLED=false | EMAIL_ENABLED=true |
|--------|-------------------|-------------------|
| Payment created | Prints to terminal | Sends actual email |
| Email fails | Shows in terminal | Logs error + shows in terminal |
| Testing | Perfect for dev | Use for production |

## Need Help?

- Read full docs: `docs/PAYMENT_EMAIL_NOTIFICATION.md`
- Check implementation: `IMPLEMENTATION_SUMMARY.md`
- Run demo: `python demo_payment_notification.py`
- Run tests: `pytest tests/test_payment_email_notification.py -v`

## Summary

✅ Feature is ready to use  
✅ Works in development (terminal) and production (email)  
✅ All tests passing  
✅ Easy to configure  
✅ No code changes needed to switch modes  

Just set `EMAIL_ENABLED` in your `.env` file and you're good to go!
