"""Service for fetching and processing group activity data."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from extensions import db
from models import Expense, Group, Settlement, User

logger = logging.getLogger(__name__)


class GroupActivityService:
    """Service class for group activity operations."""

    @staticmethod
    def get_week_date_range() -> Tuple[datetime, datetime]:
        """
        Get the start and end datetime for the previous week.

        Returns:
            Tuple of (start_of_week, end_of_week) as timezone-aware datetimes
        """
        now = datetime.now(timezone.utc)
        # Get last Monday (start of previous week)
        days_since_monday = (now.weekday() + 7) % 7  # 0 = Monday
        start_of_week = (now - timedelta(days=days_since_monday + 7)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Get last Sunday (end of previous week)
        end_of_week = start_of_week + timedelta(days=7, seconds=-1)

        logger.debug(f"Week range: {start_of_week} to {end_of_week}")
        return start_of_week, end_of_week

    @staticmethod
    def get_weekly_activity(
        group_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Fetch all activity (expenses and settlements) for a group within a date range.

        Args:
            group_id: The group's ID
            start_date: Start of date range (defaults to last week start)
            end_date: End of date range (defaults to last week end)

        Returns:
            Dictionary with 'expenses' and 'settlements' lists, or None if group not found
        """
        try:
            # Validate group exists
            group = db.session.get(Group, group_id)
            if not group:
                logger.warning(f"Group {group_id} not found")
                return None

            # Use default date range if not provided
            if start_date is None or end_date is None:
                start_date, end_date = GroupActivityService.get_week_date_range()

            # Ensure dates are timezone-aware
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            # Fetch expenses for the group within date range
            expenses = (
                Expense.query.filter(
                    Expense.group_id == group_id,
                    Expense.created_at >= start_date,
                    Expense.created_at <= end_date,
                )
                .order_by(Expense.created_at.desc())
                .all()
            )

            # Fetch settlements involving group members within date range
            member_ids = [member.id for member in group.members]
            settlements = []

            if member_ids:
                settlements = (
                    Settlement.query.filter(
                        db.or_(
                            Settlement.payer_id.in_(member_ids),
                            Settlement.recipient_id.in_(member_ids),
                        ),
                        Settlement.created_at >= start_date,
                        Settlement.created_at <= end_date,
                    )
                    .order_by(Settlement.created_at.desc())
                    .all()
                )

            logger.info(
                f"Group {group_id} ({group.name}): "
                f"{len(expenses)} expenses, {len(settlements)} settlements"
            )

            return {
                "group": group,
                "expenses": expenses,
                "settlements": settlements,
                "start_date": start_date,
                "end_date": end_date,
                "has_activity": len(expenses) > 0 or len(settlements) > 0,
            }

        except Exception as e:
            logger.error(f"Error fetching activity for group {group_id}: {str(e)}")
            raise

    @staticmethod
    def get_all_active_groups() -> List[Group]:
        """
        Get all groups that have at least one member.

        Returns:
            List of Group objects
        """
        try:
            groups = Group.query.all()
            active_groups = [g for g in groups if len(g.members) > 0]

            logger.info(f"Found {len(active_groups)} active groups")
            return active_groups

        except Exception as e:
            logger.error(f"Error fetching active groups: {str(e)}")
            raise

    @staticmethod
    def format_activity_summary(activity_data: Dict) -> Dict[str, any]:
        """
        Format activity data into a structured summary for email.

        Args:
            activity_data: Dictionary from get_weekly_activity()

        Returns:
            Dictionary with formatted summary data
        """
        if not activity_data or not activity_data.get("has_activity"):
            return None

        group = activity_data["group"]
        expenses = activity_data["expenses"]
        settlements = activity_data["settlements"]

        # Calculate totals
        total_expenses = sum(e.amount for e in expenses)
        total_settlements = sum(s.amount for s in settlements)

        # Format expenses
        formatted_expenses = [
            {
                "description": e.description,
                "amount": e.amount,
                "payer": e.payer,
                "date": e.created_at.strftime("%Y-%m-%d %H:%M"),
                "category": e.category or "Uncategorized",
            }
            for e in expenses
        ]

        # Format settlements
        formatted_settlements = [
            {
                "payer": s.payer.display_name or s.payer.email,
                "recipient": s.recipient.display_name or s.recipient.email,
                "amount": s.amount,
                "date": s.created_at.strftime("%Y-%m-%d %H:%M"),
                "note": s.note or "",
            }
            for s in settlements
        ]

        return {
            "group_name": group.name,
            "group_id": group.id,
            "week_start": activity_data["start_date"].strftime("%B %d, %Y"),
            "week_end": activity_data["end_date"].strftime("%B %d, %Y"),
            "expenses": formatted_expenses,
            "settlements": formatted_settlements,
            "total_expenses": total_expenses,
            "total_settlements": total_settlements,
            "expense_count": len(expenses),
            "settlement_count": len(settlements),
        }
