#!/usr/bin/env python3
"""
CLI command to process recurring expenses.

Usage:
    python commands/process_recurring.py
    python commands/process_recurring.py --dry-run

Examples:
    # Process all due recurring expenses
    python commands/process_recurring.py

    # Preview what would be processed (no expenses created)
    python commands/process_recurring.py --dry-run
"""

import sys
from pathlib import Path

import click

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app  # noqa: E402
from services.recurring_expense_service import RecurringExpenseService  # noqa: E402


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview without creating expenses")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def process_recurring(dry_run, verbose):
    """
    Process all due recurring expenses and generate new expense records.

    This command finds all recurring expenses that have a next_occurrence date
    on or before today, creates new expense records for them, and updates the
    next occurrence date for future processing.
    """
    # Create Flask app context
    app = create_app()

    with app.app_context():
        try:
            if dry_run:
                click.echo("🔍 DRY RUN: Checking for due recurring expenses...")
                click.echo()

                due_expenses = RecurringExpenseService.get_due_recurring_expenses()

                if not due_expenses:
                    click.echo("✅ No recurring expenses are due at this time.")
                    return

                click.echo(f"📋 Would process {len(due_expenses)} recurring expense(s):")
                click.echo()

                for expense in due_expenses:
                    click.echo(f"  📝 {expense.description}")
                    click.echo(f"     💰 Amount: ${expense.amount:.2f} {expense.currency}")
                    click.echo(f"     🔄 Frequency: {expense.recurrence_frequency}")
                    click.echo(f"     📅 Due date: {expense.next_occurrence}")

                    if expense.recurrence_end_date:
                        click.echo(f"     🏁 End date: {expense.recurrence_end_date}")

                    if verbose:
                        click.echo(f"     👤 Payer: {expense.payer}")
                        click.echo(f"     📂 Category: {expense.category or 'N/A'}")

                    # Calculate next occurrence that would be set
                    next_date = RecurringExpenseService.calculate_next_occurrence(
                        expense.next_occurrence,
                        expense.recurrence_frequency,
                        expense.recurrence_end_date,
                    )
                    if next_date:
                        click.echo(f"     ➡️  Next occurrence would be: {next_date}")
                    else:
                        click.echo("     ⏹️  Would be final occurrence (no more after this)")

                    click.echo()

                click.echo("ℹ️  Run without --dry-run to process these expenses.")

            else:
                click.echo("📧 Processing recurring expenses...")
                click.echo()

                successful, failed = RecurringExpenseService.process_all_due_expenses()

                if successful > 0:
                    click.echo(f"✅ Successfully generated {successful} recurring expense(s)")

                if failed > 0:
                    click.echo(f"⚠️  Failed to generate {failed} recurring expense(s)")

                if successful == 0 and failed == 0:
                    click.echo("ℹ️  No recurring expenses were due for processing")

                click.echo()
                click.echo("✨ Recurring expense processing completed.")

        except Exception as e:
            click.echo(f"❌ Error: {str(e)}", err=True)
            sys.exit(1)


if __name__ == "__main__":
    process_recurring()
