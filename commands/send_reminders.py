#!/usr/bin/env python3
"""
CLI command to send payment reminders.

Usage:
    python commands/send_reminders.py
    python commands/send_reminders.py --days 7
    python commands/send_reminders.py --dry-run
    python commands/send_reminders.py --days 14 --dry-run

Examples:
    # Send reminders to users with 7+ day old balances
    python commands/send_reminders.py

    # Preview who would get reminders (no emails sent)
    python commands/send_reminders.py --dry-run

    # Send reminders for 14+ day old balances
    python commands/send_reminders.py --days 14
"""

import sys
from pathlib import Path

import click

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app  # noqa: E402
from services.reminder_service import ReminderService  # noqa: E402


@click.command()
@click.option(
    "--days",
    default=7,
    type=click.IntRange(min=1, max=365),
    help="Days threshold for reminders (default: 7, range: 1-365)",
)
@click.option("--dry-run", is_flag=True, help="Preview without sending emails")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def send_reminders(days, dry_run, verbose):
    """
    Send payment reminder notifications to users with unpaid balances.

    This command identifies users who have outstanding balances for more than
    the specified number of days and sends them email reminders.
    """
    # Create Flask app context
    app = create_app()

    with app.app_context():
        try:
            if dry_run:
                click.echo(f"🔍 DRY RUN: Checking for users needing reminders (>{days} days)...")
                click.echo()

                users = ReminderService.get_users_needing_reminders(days)

                if not users:
                    click.echo("✅ No users need reminders at this time.")
                    return

                click.echo(f"📧 Would send reminders to {len(users)} users:")
                click.echo()

                total_owed = 0
                for user, balance, oldest_date in users:
                    amount_owed = abs(balance)
                    total_owed += amount_owed

                    # Calculate days outstanding
                    days_outstanding, _ = ReminderService.calculate_balance_age(user.id)

                    click.echo(f"  👤 {user.email}")
                    click.echo(f"     💰 Owes: ${amount_owed:.2f}")
                    click.echo(
                        f"     📅 Outstanding: {days_outstanding} days (since {oldest_date.date()})"
                    )

                    if verbose:
                        # Show balance breakdown
                        breakdown = ReminderService.get_balance_breakdown(user.id)
                        if breakdown:
                            click.echo("     📋 Breakdown:")
                            for debt in breakdown:
                                click.echo(f"        • {debt['creditor']}: ${debt['amount']:.2f}")

                    click.echo()

                click.echo(f"💵 Total outstanding: ${total_owed:.2f}")
                click.echo()
                click.echo("ℹ️  Run without --dry-run to send actual reminders.")

            else:
                click.echo(f"📧 Sending payment reminders (>{days} days outstanding)...")
                click.echo()

                result = ReminderService.send_reminders(days)

                # Display results
                if result["reminders_sent"] > 0:
                    click.echo(f"✅ Successfully sent {result['reminders_sent']} reminders")

                    if verbose:
                        click.echo("📧 Notified users:")
                        for email in result["users_notified"]:
                            click.echo(f"  • {email}")
                else:
                    click.echo("ℹ️  No reminders sent (no eligible users found)")

                # Display errors if any
                if result["errors"]:
                    click.echo()
                    click.echo(f"⚠️  {len(result['errors'])} errors occurred:")
                    for error in result["errors"]:
                        if "user" in error:
                            click.echo(f"  ❌ {error['user']}: {error['error']}")
                        else:
                            click.echo(f"  ❌ {error['error']}")

                click.echo()
                click.echo("✨ Reminder process completed.")

        except Exception as e:
            click.echo(f"❌ Error: {str(e)}", err=True)
            sys.exit(1)


if __name__ == "__main__":
    send_reminders()
