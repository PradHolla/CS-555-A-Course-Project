# Weekly Group Activity Summary Email

## Overview
Automated system that sends weekly email summaries of group activity (expenses and settlements) to all group members.

## Features
- ✅ Sends weekly summary emails every Monday
- ✅ Includes all expenses added during the week
- ✅ Includes all settlements/payments made during the week
- ✅ Only sends if there's activity (no spam for inactive groups)
- ✅ Beautiful HTML email templates
- ✅ Handles multiple groups and multiple members
- ✅ Idempotent and safe for production

## Architecture

### Components

**1. GroupActivityService** (`services/group_activity_service.py`)
- Fetches weekly activity data for groups
- Calculates date ranges
- Formats activity summaries

**2. NotificationService** (`services/notification_service.py`)
- Sends formatted emails to users
- Handles HTML and plain text formats
- Integrates with existing email infrastructure

**3. CLI Command** (`commands/send_weekly_summaries.py`)
- Entry point for scheduled execution
- Processes all active groups
- Logs statistics and errors

### Data Flow
```
Cron Job → send_weekly_summaries.py
    ↓
GroupActivityService.get_all_active_groups()
    ↓
For each group:
    GroupActivityService.get_weekly_activity()
        ↓
    GroupActivityService.format_activity_summary()
        ↓
    For each member:
        send_group_activity_summary()
```

## Usage

### Manual Execution
```bash
python commands/send_weekly_summaries.py
```

### Scheduled Execution (Cron)

**Linux/Mac:**
```bash
# Edit crontab
crontab -e

# Add this line (runs every Monday at 9 AM)
0 9 * * 1 cd /path/to/project && /path/to/python commands/send_weekly_summaries.py >> /var/log/weekly_summaries.log 2>&1
```

**Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Weekly, Monday, 9:00 AM
4. Action: Start a program
   - Program: `python`
   - Arguments: `commands/send_weekly_summaries.py`
   - Start in: `C:\path\to\project`

### Cloud Schedulers

**AWS CloudWatch Events:**
```yaml
ScheduleExpression: cron(0 9 ? * MON *)
Target: Lambda function or ECS task
```

**Google Cloud Scheduler:**
```bash
gcloud scheduler jobs create http weekly-summary \
  --schedule="0 9 * * 1" \
  --uri="https://your-app.com/api/send-weekly-summaries" \
  --http-method=POST
```

**Heroku Scheduler:**
```bash
# Add-on: Heroku Scheduler
# Command: python commands/send_weekly_summaries.py
# Frequency: Weekly (Monday 9:00 AM)
```

## Configuration

### Environment Variables
```bash
# Email settings (already configured)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
EMAIL_ENABLED=true  # Set to true for production

# Optional: Custom week start day (default: Monday)
WEEK_START_DAY=0  # 0=Monday, 6=Sunday
```

## Email Template

### Subject
```
Weekly Summary: [Group Name] ([Start Date] - [End Date])
```

### Content Sections
1. **Header**: Group name and date range
2. **Expenses Section**: List of new expenses with amounts and payers
3. **Settlements Section**: List of payments made
4. **Totals**: Summary of total expenses and settlements

### Example Email
```
Hi John Doe,

Here's your weekly activity summary for Weekend Trip Group:

Week: January 1, 2024 - January 7, 2024

💰 NEW EXPENSES (3)
Total: $250.00

  • Dinner at Restaurant - $100.00
    Paid by: Alice | 2024-01-05 18:30
    Category: Food

  • Gas for Road Trip - $80.00
    Paid by: Bob | 2024-01-06 10:15
    Category: Transportation

  • Hotel Booking - $70.00
    Paid by: Alice | 2024-01-07 14:00
    Category: Accommodation

💳 PAYMENTS (1)
Total: $50.00

  • Bob paid Alice $50.00
    2024-01-07 20:00
    Note: Paying back for dinner
```

## Testing

### Run Tests
```bash
# Run all weekly summary tests
python -m pytest tests/test_group_activity_service.py -v
python -m pytest tests/test_weekly_summary_email.py -v

# Run with coverage
python -m pytest tests/test_group_activity_service.py tests/test_weekly_summary_email.py --cov=services.group_activity_service --cov-report=term-missing
```

### Test Coverage
- ✅ Date range calculation
- ✅ Activity fetching (expenses and settlements)
- ✅ Empty activity handling (no spam)
- ✅ Multiple groups and members
- ✅ Email formatting
- ✅ Error handling

## Monitoring

### Logs
The command logs to stdout/stderr:
```
2024-01-08 09:00:00 - INFO - Starting Weekly Group Activity Summary Process
2024-01-08 09:00:01 - INFO - Processing 5 active groups
2024-01-08 09:00:02 - INFO - Processing group: Weekend Trip (ID: 1)
2024-01-08 09:00:03 - INFO - Sending summary to 3 members
2024-01-08 09:00:04 - INFO -   ✓ Sent to user1@example.com
2024-01-08 09:00:05 - INFO -   ✓ Sent to user2@example.com
2024-01-08 09:00:06 - INFO -   ✓ Sent to user3@example.com
2024-01-08 09:00:10 - INFO - Weekly Summary Process Complete
2024-01-08 09:00:10 - INFO - Groups processed: 5
2024-01-08 09:00:10 - INFO - Groups with activity: 3
2024-01-08 09:00:10 - INFO - Emails sent: 12
2024-01-08 09:00:10 - INFO - Errors: 0
```

### Metrics to Monitor
- Number of groups processed
- Number of emails sent
- Error rate
- Execution time

## Troubleshooting

### No Emails Sent
1. Check `EMAIL_ENABLED=true` in `.env`
2. Verify SMTP credentials
3. Check if groups have activity
4. Review logs for errors

### Duplicate Emails
- Command is idempotent - safe to run multiple times
- Check cron schedule isn't running too frequently
- Verify only one scheduler is active

### Missing Activity
- Verify date range calculation
- Check timezone settings
- Ensure expenses/settlements have correct `created_at` timestamps

## Performance

### Optimization
- Processes groups in batches
- Uses database indexes on `created_at` fields
- Minimal memory footprint
- Scales to thousands of groups

### Expected Performance
- ~100ms per group
- ~50ms per email
- Can process 1000 groups in ~2 minutes

## Security

### Best Practices
- ✅ No sensitive data in logs
- ✅ Email credentials stored in environment variables
- ✅ SQL injection protection (ORM)
- ✅ Input validation
- ✅ Error handling prevents data leaks

## Future Enhancements

### Potential Features
- [ ] User preference to opt-out of weekly summaries
- [ ] Customizable email frequency (daily, bi-weekly, monthly)
- [ ] Summary statistics (charts, graphs)
- [ ] Mobile push notifications
- [ ] Digest of top spenders/categories
- [ ] Year-end summary reports

## Support

For issues or questions:
1. Check logs: `/var/log/weekly_summaries.log`
2. Run manual test: `python commands/send_weekly_summaries.py`
3. Review test output: `pytest tests/test_group_activity_service.py -v`
