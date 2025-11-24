"""Service for managing user points in groups."""

from extensions import db
from models import Expense, UserGroupPoints
from services.expense_service import ExpenseService


class PointsService:
    """Service class for points-related business logic."""

    POINTS_PER_EXPENSE = 10  # Points awarded per expense where payer covers multiple participants

    @staticmethod
    def should_award_points(expense):
        """
        Determine if points should be awarded for an expense.

        Points are awarded only when:
        1. The payer is paying for more than one participant (including themselves)

        Args:
            expense: Expense model object

        Returns:
            bool: True if points should be awarded, False otherwise
        """
        split_details = ExpenseService._parse_split_details(expense)

        if not split_details:
            return False

        # Count unique participants (excluding the payer if they're the only participant)
        participants = set(split_details.keys())

        # If there's more than one participant, award points
        # (This includes cases where payer pays for themselves + others)
        return len(participants) > 1

    @staticmethod
    def get_or_create_user_group_points(user_id, group_id):
        """
        Get or create a UserGroupPoints record for a user in a group.

        Args:
            user_id: User ID
            group_id: Group ID

        Returns:
            UserGroupPoints: The points record
        """
        points_record = UserGroupPoints.query.filter_by(user_id=user_id, group_id=group_id).first()

        if not points_record:
            points_record = UserGroupPoints(user_id=user_id, group_id=group_id, points=0)
            db.session.add(points_record)

        return points_record

    @staticmethod
    def calculate_points_for_group(group_id):
        """
        Recalculate points for all users in a group based on all expenses.

        This method:
        1. Gets all expenses for the group
        2. For each expense, checks if points should be awarded
        3. Awards points to the payer if conditions are met
        4. Updates or creates UserGroupPoints records

        Args:
            group_id: Group ID
        """
        try:
            # Get all expenses for this group
            expenses = Expense.query.filter_by(group_id=group_id).all()

            # Track points per user (user_id -> points count)
            user_points = {}

            # Get all group members to map emails to user IDs
            from models import Group

            group = db.session.get(Group, group_id)
            if not group:
                return

            # Create email to user_id mapping (check both email and display_name)
            email_to_user_id = {}
            for member in group.members:
                email_to_user_id[member.email] = member.id
                # Also check display_name if it exists and is different from email
                if member.display_name and member.display_name != member.email:
                    email_to_user_id[member.display_name] = member.id

            # Calculate points for each expense
            for expense in expenses:
                if PointsService.should_award_points(expense):
                    payer_identifier = expense.payer  # This could be email or display_name
                    payer_user_id = email_to_user_id.get(payer_identifier)

                    if payer_user_id:
                        user_points[payer_user_id] = (
                            user_points.get(payer_user_id, 0) + PointsService.POINTS_PER_EXPENSE
                        )
                    else:
                        # Debug: log if we can't find the payer
                        print(
                            f"Warning: Could not find user_id for payer '{payer_identifier}' in group {group_id}"
                        )

            # Update or create UserGroupPoints records for all group members
            for member in group.members:
                points_record = PointsService.get_or_create_user_group_points(member.id, group_id)
                points_record.points = user_points.get(member.id, 0)

            db.session.commit()
        except Exception as e:
            print(f"Error calculating points for group {group_id}: {e}")
            db.session.rollback()
            raise

    @staticmethod
    def get_user_points_in_group(user_id, group_id):
        """
        Get points for a user in a specific group.

        Args:
            user_id: User ID
            group_id: Group ID

        Returns:
            int: Points for the user in the group (0 if no record exists)
        """
        points_record = UserGroupPoints.query.filter_by(user_id=user_id, group_id=group_id).first()

        return points_record.points if points_record else 0

    @staticmethod
    def get_all_points_for_group(group_id):
        """
        Get points for all users in a group.

        Args:
            group_id: Group ID

        Returns:
            dict: Mapping of user_id to points
        """
        points_records = UserGroupPoints.query.filter_by(group_id=group_id).all()

        return {record.user_id: record.points for record in points_records}
