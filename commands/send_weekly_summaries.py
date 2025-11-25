"""
CLI command to send weekly group activity summary emails.

This script should be run weekly via cron job or task scheduler.
Example cron: 0 9 * * 1 (Every Monday at 9 AM)

Usage:
    python commands/send_weekly_summaries.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from extensions import db
from services.group_activity_service import GroupActivityService
from services.notification_service import send_group_activity_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def send_weekly_summaries():
    """
    Main function to send weekly activity summaries to all group members.

    Returns:
        Dictionary with summary statistics
    """
    app = create_app()

    with app.app_context():
        logger.info("="*60)
        logger.info("Starting Weekly Group Activity Summary Process")
        logger.info("="*60)

        # Statistics
        stats = {
            "groups_processed": 0,
            "groups_with_activity": 0,
            "emails_sent": 0,
            "errors": []
        }

        try:
            # Get all active groups
            groups = GroupActivityService.get_all_active_groups()

            if not groups:
                logger.info("No active groups found")
                return stats

            logger.info(f"Processing {len(groups)} active groups")

            # Process each group
            for group in groups:
                try:
                    stats["groups_processed"] += 1
                    logger.info(f"\nProcessing group: {group.name} (ID: {group.id})")

                    # Fetch weekly activity
                    activity_data = GroupActivityService.get_weekly_activity(group.id)

                    if not activity_data:
                        logger.warning(f"Could not fetch activity for group {group.id}")
                        continue

                    # Check if there's any activity
                    if not activity_data["has_activity"]:
                        logger.info(f"No activity for group {group.name}, skipping email")
                        continue

                    stats["groups_with_activity"] += 1

                    # Format activity summary
                    summary_data = GroupActivityService.format_activity_summary(activity_data)

                    if not summary_data:
                        logger.warning(f"Could not format summary for group {group.id}")
                        continue

                    # Send email to each group member
                    members = group.members
                    logger.info(f"Sending summary to {len(members)} members")

                    for member in members:
                        try:
                            send_group_activity_summary(member, summary_data)
                            stats["emails_sent"] += 1
                            logger.info(f"  ✓ Sent to {member.email}")

                        except Exception as e:
                            error_msg = f"Failed to send to {member.email}: {str(e)}"
                            logger.error(f"  ✗ {error_msg}")
                            stats["errors"].append({
                                "group": group.name,
                                "user": member.email,
                                "error": str(e)
                            })

                except Exception as e:
                    error_msg = f"Error processing group {group.name}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append({
                        "group": group.name,
                        "error": str(e)
                    })
                    continue

            # Print summary
            logger.info("\n" + "="*60)
            logger.info("Weekly Summary Process Complete")
            logger.info("="*60)
            logger.info(f"Groups processed: {stats['groups_processed']}")
            logger.info(f"Groups with activity: {stats['groups_with_activity']}")
            logger.info(f"Emails sent: {stats['emails_sent']}")
            logger.info(f"Errors: {len(stats['errors'])}")

            if stats["errors"]:
                logger.error("\nErrors encountered:")
                for error in stats["errors"]:
                    logger.error(f"  - {error}")

            return stats

        except Exception as e:
            logger.error(f"Critical error in weekly summary process: {str(e)}")
            stats["errors"].append({"error": str(e)})
            return stats


if __name__ == "__main__":
    try:
        result = send_weekly_summaries()

        # Exit with error code if there were errors
        if result["errors"]:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
