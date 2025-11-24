import json
from datetime import date, datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func

from extensions import db
from models import Comment, Expense, Group, GroupInvitation, User
from services.expense_service import ExpenseService
from services.notification_service import (
    notify_expense_deletion,
    notify_expense_edited,
    notify_expense_participants,
    notify_group_invitation,
)
from utils.decorators import login_required
from utils.validators import is_valid_email

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


@groups_bp.route("/")
@login_required
def list_groups():
    """Display all groups that the current user is a member of."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("home.index"))

    # Get groups the user is a member of
    groups = user.groups.order_by(Group.created_at.desc()).all()

    # Calculate points for all groups (this ensures existing expenses are counted)
    from services.points_service import PointsService

    # Dictionary: group_id -> list of {user_id, user_name, points}
    groups_points_data = {}
    for group in groups:
        # Recalculate points for this group to ensure all expenses are counted
        try:
            PointsService.calculate_points_for_group(group.id)
        except Exception as e:
            print(f"Failed to calculate points for group {group.id}: {e}")

        # Get all points for this group
        all_points = PointsService.get_all_points_for_group(group.id)

        # Create list of members with their points
        members_with_points = []
        for member in group.members:
            points = all_points.get(member.id, 0)
            if points > 0:  # Only show members who have points
                members_with_points.append(
                    {
                        "user_id": member.id,
                        "name": member.display_name or member.email,
                        "email": member.email,
                        "points": points,
                        "is_current_user": member.id == user_id,
                    }
                )

        # Sort by points descending
        members_with_points.sort(key=lambda x: x["points"], reverse=True)
        groups_points_data[group.id] = members_with_points

    return render_template(
        "groups/index.html",
        groups=groups,
        groups_points_data=groups_points_data,
        current_user_id=user_id,
    )


@groups_bp.route("/trend")
@login_required
def trend():
    """Show a simple expense trend per payer across the user's groups.

    This aggregates expenses by payer and month for the last 6 months and
    renders a small table showing monthly totals and a row total per payer.
    """
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("dashboard.index"))

    # Get the groups the user belongs to (IDs)
    group_ids = [g.id for g in user.groups]

    # Build last N months labels (YYYY-MM), include current month
    months_to_show = 6
    today = date.today()
    months = []
    y = today.year
    m = today.month
    for i in range(months_to_show):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    # Reverse to chronological order
    months = list(reversed(months))
    month_labels = [f"{y:04d}-{m:02d}" for (y, m) in months]

    # If user is not member of any groups, show empty data
    rows = []

    # Prepare month totals (summing across payers) and category aggregates
    month_totals_map = {lbl: 0.0 for lbl in month_labels}
    category_map = {}  # category -> {count, amount}

    if group_ids:
        # Query sums grouped by payer and month (for per-payer table)
        month_label = func.strftime("%Y-%m", Expense.expense_date)
        per_payer_q = (
            db.session.query(
                Expense.payer.label("payer"),
                month_label.label("month"),
                func.sum(Expense.amount).label("total"),
            )
            .filter(Expense.group_id.in_(group_ids))
            .group_by(Expense.payer, month_label)
            .all()
        )

        # Transform into nested dict payer -> {month: total}
        data = {}
        for payer, month, total in per_payer_q:
            if payer not in data:
                data[payer] = {lbl: 0.0 for lbl in month_labels}
            data[payer][month] = float(total or 0.0)
            # also add to month_totals_map
            if month in month_totals_map:
                month_totals_map[month] += float(total or 0.0)

        # Build per-payer rows
        payers = list(data.keys())
        users = User.query.filter(User.email.in_(payers)).all() if payers else []
        name_map = {u.email: (u.display_name or u.email) for u in users}

        for payer, month_map in data.items():
            total = sum(month_map.get(lbl, 0.0) for lbl in month_labels)
            rows.append(
                {
                    "payer": payer,
                    "display_name": name_map.get(payer, payer),
                    "months": month_map,
                    "total": total,
                }
            )

        rows.sort(key=lambda r: r["total"], reverse=True)

        # Category aggregates: count and sum per category
        cat_q = (
            db.session.query(
                Expense.category.label("category"),
                func.count(Expense.id).label("count"),
                func.sum(Expense.amount).label("amount"),
            )
            .filter(Expense.group_id.in_(group_ids))
            .group_by(Expense.category)
            .all()
        )

        for category, cnt, amt in cat_q:
            label = category if category else "Uncategorized"
            category_map[label] = {"count": int(cnt or 0), "amount": float(amt or 0.0)}

    # Compute highest and lowest months (based on month_totals_map)
    month_totals = [month_totals_map.get(lbl, 0.0) for lbl in month_labels]
    if month_totals:
        # Highest - pick the month with the maximum total; if tie, first occurance
        max_val = max(month_totals)
        min_val = min(month_totals)
        max_index = month_totals.index(max_val)
        min_index = month_totals.index(min_val)
        month_highest_label = month_labels[max_index]
        month_highest_total = max_val
        month_lowest_label = month_labels[min_index]
        month_lowest_total = min_val
    else:
        month_highest_label = None
        month_highest_total = 0.0
        month_lowest_label = None
        month_lowest_total = 0.0

    # Determine category most frequent and category with highest total amount
    category_labels = []
    category_counts = []
    category_amounts = []
    category_most_freq = None
    category_highest_amount = None

    if category_map:
        for lbl, info in category_map.items():
            category_labels.append(lbl)
            category_counts.append(info["count"])
            category_amounts.append(info["amount"])

        # most frequent = max by count
        most_freq_idx = category_counts.index(max(category_counts))
        category_most_freq = category_labels[most_freq_idx]
        # highest amount
        highest_amt_idx = category_amounts.index(max(category_amounts))
        category_highest_amount = category_labels[highest_amt_idx]

    return render_template(
        "groups/trend.html",
        months=month_labels,
        rows=rows,
        month_totals=month_totals,
        month_highest_label=month_highest_label,
        month_highest_total=month_highest_total,
        month_lowest_label=month_lowest_label,
        month_lowest_total=month_lowest_total,
        category_labels=category_labels,
        category_counts=category_counts,
        category_amounts=category_amounts,
        category_most_freq=category_most_freq,
        category_highest_amount=category_highest_amount,
    )


@groups_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_group():
    """Display create group form (GET) or create a new group (POST)."""
    user_id = session.get("user_id")
    creator = db.session.get(User, user_id)

    if not creator:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    if request.method == "GET":
        """Display the create group form."""
        return render_template("groups/create.html")

    # POST - Create a new group
    name = request.form.get("name", "").strip()
    member_emails = request.form.get("members", "").strip()

    # Validate inputs
    if not name:
        flash("Group name is required.", "error")
        return redirect(url_for("groups.create_group"))

    # Validate all email formats BEFORE any DB operations
    if member_emails:
        emails = [email.strip() for email in member_emails.split(",") if email.strip()]
        for email in emails:
            if not is_valid_email(email):
                flash(f"Invalid email format: {email}", "error")
                return redirect(url_for("groups.create_group"))

    try:
        # Create the group
        group = Group(name=name, created_by_id=user_id)
        db.session.add(group)

        # Add creator as first member
        group.members.append(creator)

        # Flush to assign group.id before checking for existing invitations
        # The duplicate check query (lines 84-86) requires group.id to be set
        db.session.flush()

        # Add other members if emails provided
        if member_emails:
            emails = [email.strip() for email in member_emails.split(",") if email.strip()]

            for email in emails:
                if email == creator.email:
                    continue  # Skip creator (already added)

                # Check if invitation already exists (whether user exists or not)
                existing_invitation = GroupInvitation.query.filter_by(
                    email=email, group_id=group.id, status="pending"
                ).first()

                if not existing_invitation:
                    # Create invitation for all users (existing or not)
                    invitation = GroupInvitation(
                        email=email, group_id=group.id, invited_by_id=user_id
                    )
                    db.session.add(invitation)

                    # Send invitation notification
                    try:
                        notify_group_invitation(creator.email, email, name)
                    except Exception as e:
                        print(f"Failed to send invitation notification: {e}")

        db.session.commit()
        flash(f"Group '{name}' created successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create group: {str(e)}", "error")
        return redirect(url_for("groups.create_group"))

    return redirect(url_for("groups.list_groups"))


@groups_bp.route("/<int:group_id>", methods=["GET", "POST"])
@login_required
def group_expenses(group_id):
    """Display or create expenses for a specific group."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the group and verify user is a member
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # POST - Create expense
    if request.method == "POST":
        # Extract form data
        description = request.form.get("description", "").strip()
        amount_raw = request.form.get("amount", "").strip()
        payer = request.form.get("payer", "").strip()
        split_type = request.form.get("split_type", "equal").strip()
        category = request.form.get("category", "").strip() or None

        # Validate required fields
        if not description:
            flash("Description is required", "error")
            return redirect(url_for("groups.group_expenses", group_id=group_id))

        if not payer:
            flash("Payer is required", "error")
            return redirect(url_for("groups.group_expenses", group_id=group_id))

        # Validate amount
        try:
            amount = float(amount_raw)
            if amount <= 0:
                flash("Amount must be greater than zero", "error")
                return redirect(url_for("groups.group_expenses", group_id=group_id))
        except (ValueError, TypeError):
            flash("Please enter a valid amount", "error")
            return redirect(url_for("groups.group_expenses", group_id=group_id))

        # Get group member emails for validation
        group_member_emails = [member.email for member in group.members]

        # Validate payer is in group
        if payer not in group_member_emails:
            flash("Payer must be a member of the group", "error")
            return redirect(url_for("groups.group_expenses", group_id=group_id))

        # Handle participants and split details
        if split_type == "equal":
            # Get selected participants for equal split
            selected_participants = request.form.getlist("participants")
            if not selected_participants:
                flash("Please select at least one participant", "error")
                return redirect(url_for("groups.group_expenses", group_id=group_id))

            # Validate all participants are in group
            for participant in selected_participants:
                if participant not in group_member_emails:
                    flash(f"Participant '{participant}' is not in the group", "error")
                    return redirect(url_for("groups.group_expenses", group_id=group_id))

            # Calculate equal split
            split_details = ExpenseService.calculate_equal_split(selected_participants, amount)

        elif split_type == "percentage":
            # Get percentage split
            percentages = {}
            for member_email in group_member_emails:
                percentage_key = f"percentage_{member_email}"
                percentage_value = request.form.get(percentage_key, "").strip()
                if percentage_value:
                    try:
                        percentages[member_email] = float(percentage_value)
                    except ValueError:
                        flash(f"Invalid percentage for {member_email}", "error")
                        return redirect(url_for("groups.group_expenses", group_id=group_id))

            if not percentages:
                flash("Please specify percentages for at least one participant", "error")
                return redirect(url_for("groups.group_expenses", group_id=group_id))

            # Validate percentage split
            is_valid, error_msg = ExpenseService.validate_percentage_split(percentages)
            if not is_valid:
                flash(error_msg, "error")
                return redirect(url_for("groups.group_expenses", group_id=group_id))

            # Calculate amounts from percentages
            split_details = ExpenseService.calculate_percentage_split(percentages, amount)

        elif split_type == "shares":
            # Get shares split
            shares = {}
            for member_email in group_member_emails:
                shares_key = f"shares_{member_email}"
                shares_value = request.form.get(shares_key, "").strip()
                if shares_value:
                    try:
                        shares[member_email] = int(shares_value)
                    except ValueError:
                        flash(f"Invalid shares count for {member_email}", "error")
                        return redirect(url_for("groups.group_expenses", group_id=group_id))

            if not shares:
                flash("Please specify shares for at least one participant", "error")
                return redirect(url_for("groups.group_expenses", group_id=group_id))

            # Validate shares split
            is_valid, error_msg = ExpenseService.validate_shares_split(shares)
            if not is_valid:
                flash(error_msg, "error")
                return redirect(url_for("groups.group_expenses", group_id=group_id))

            # Calculate amounts from shares
            split_details = ExpenseService.calculate_shares_split(shares, amount)

        else:  # custom split (by amount)
            # Get custom split amounts
            split_details = {}
            for member_email in group_member_emails:
                amount_key = f"custom_amount_{member_email}"
                custom_amount = request.form.get(amount_key, "").strip()
                if custom_amount:
                    try:
                        split_details[member_email] = float(custom_amount)
                    except ValueError:
                        flash(f"Invalid amount for {member_email}", "error")
                        return redirect(url_for("groups.group_expenses", group_id=group_id))

            if not split_details:
                flash("Please specify amounts for at least one participant", "error")
                return redirect(url_for("groups.group_expenses", group_id=group_id))

            # Validate custom split
            is_valid, error_msg = ExpenseService.validate_custom_split(split_details, amount)
            if not is_valid:
                flash(error_msg, "error")
                return redirect(url_for("groups.group_expenses", group_id=group_id))

        # Create expense
        expense = Expense(
            description=description,
            amount=amount,
            payer=payer,
            group_id=group_id,
            split_type=split_type,
            split_details=json.dumps(split_details),
            participants=", ".join(split_details.keys()),  # Keep for backward compatibility
            category=category,
            expense_date=date.today(),  # Automatically set to today's date
        )
        db.session.add(expense)
        db.session.commit()

        # Recalculate points for the group after adding expense
        from services.points_service import PointsService

        try:
            PointsService.calculate_points_for_group(group_id)
        except Exception as e:
            print(f"Failed to recalculate points: {e}")

        # Send email notifications to ALL participants (including the payer)
        participant_list = list(split_details.keys())
        if participant_list:
            try:
                notify_expense_participants(expense, participant_list)
                print(f"Sent notifications to: {participant_list}")
            except Exception as e:
                print(f"Failed to send notifications: {e}")

        flash("Expense added successfully!", "success")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # GET request - show expenses for this group
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.created_at.desc()).all()

    # Get all expense IDs for bulk comment count query
    expense_ids = [expense.id for expense in expenses]

    # Bulk fetch comment counts for all expenses to avoid N+1 queries
    from sqlalchemy import func

    comment_counts = {}
    if expense_ids:
        comment_count_results = (
            db.session.query(Comment.expense_id, func.count(Comment.id).label("count"))
            .filter(Comment.expense_id.in_(expense_ids))
            .group_by(Comment.expense_id)
            .all()
        )

        comment_counts = {expense_id: count for expense_id, count in comment_count_results}

    # Process expenses for display
    expense_views = []
    all_emails = set()
    for expense in expenses:
        split_details = ExpenseService._parse_split_details(expense)
        participants = list(split_details.keys())
        share = (
            list(split_details.values())[0]
            if len(split_details) == 1 and expense.split_type == "equal"
            else None
        )
        comment_count = comment_counts.get(expense.id, 0)
        expense_views.append(
            {
                "model": expense,
                "participants": participants,
                "share": share,
                "split_details": split_details,
                "comment_count": comment_count,
            }
        )
        # Collect all emails for display name lookup
        all_emails.add(expense.payer)
        all_emails.update(participants)

    # Bulk fetch all users for the emails to avoid N+1 queries
    if all_emails:
        users = User.query.filter(User.email.in_(all_emails)).all()
        user_map = {user.email: user for user in users}
    else:
        users = []
        user_map = {}

    email_to_name = {}
    for email in all_emails:
        user = user_map.get(email)
        if user:
            email_to_name[email] = user.display_name or user.email
        else:
            email_to_name[email] = email  # Fallback to email if user not found

    # Create expense payers map for profile pictures
    expense_payers = {}
    for expense in expenses:
        payer_user = user_map.get(expense.payer)
        if payer_user:
            expense_payers[expense.id] = payer_user

    # Convert group members to JSON-serializable format
    groups_data = [
        {
            "id": group.id,
            "name": group.name,
            "members": [
                {
                    "email": m.email,
                    "display_name": m.display_name or m.email,
                }
                for m in group.members
            ],
        }
    ]

    # Check for expense deletion and edit notifications
    deletion_info = None
    edit_info = None
    from models import GroupNotification

    # Get unread deletion notifications for this group
    deletion_notifications = (
        GroupNotification.query.filter_by(group_id=group_id, notification_type="expense_deleted")
        .order_by(GroupNotification.created_at.desc())
        .all()
    )

    # Find deletion notifications the current user hasn't seen
    for notification in deletion_notifications:
        read_by_ids = json.loads(notification.read_by) if notification.read_by else []
        if user.id not in read_by_ids:
            deletion_info = {
                "description": notification.description,
                "amount": str(notification.amount) if notification.amount else "",
                "payer": notification.payer or "",
                "deleted_by": notification.deleted_by or "",
                "notification_id": notification.id,
            }
            break  # Show the most recent unread notification

    # Get unread edit notifications for this group
    edit_notifications = (
        GroupNotification.query.filter_by(group_id=group_id, notification_type="expense_edited")
        .order_by(GroupNotification.created_at.desc())
        .all()
    )

    # Find edit notifications the current user hasn't seen
    for notification in edit_notifications:
        read_by_ids = json.loads(notification.read_by) if notification.read_by else []
        if user.id not in read_by_ids:
            edit_info = {
                "description": notification.description,
                "amount": str(notification.amount) if notification.amount else "",
                "payer": notification.payer or "",
                "edited_by": notification.edited_by or "",
                "notification_id": notification.id,
            }
            break  # Show the most recent unread notification

    # Count total transactions
    transaction_count = len(expenses)

    # Calculate points for this group (ensures all expenses are counted)
    from services.points_service import PointsService

    try:
        PointsService.calculate_points_for_group(group_id)
    except Exception as e:
        print(f"Failed to calculate points for group {group_id}: {e}")

    # Get points for all users in this group
    all_group_points = PointsService.get_all_points_for_group(group_id)

    # Create list of members with their points
    members_with_points = []
    for member in group.members:
        points = all_group_points.get(member.id, 0)
        if points > 0:  # Only show members who have points
            members_with_points.append(
                {
                    "user_id": member.id,
                    "name": member.display_name or member.email,
                    "email": member.email,
                    "points": points,
                    "is_current_user": member.id == user_id,
                }
            )

    # Sort by points descending
    members_with_points.sort(key=lambda x: x["points"], reverse=True)

    # Get points for current user (for backward compatibility)
    current_user_points = PointsService.get_user_points_in_group(user_id, group_id)

    return render_template(
        "groups/expenses.html",
        group=group,
        expenses=expense_views,
        groups_data=groups_data,
        email_to_name=email_to_name,
        expense_payers=expense_payers,
        deletion_info=deletion_info,
        edit_info=edit_info,
        transaction_count=transaction_count,
        current_user_id=user_id,
        all_group_points=all_group_points,
        current_user_points=current_user_points,
        members_with_points=members_with_points,
    )


@groups_bp.route("/<int:group_id>/expense/<int:expense_id>")
@login_required
def expense_detail(group_id, expense_id):
    """Display expense detail page with comments."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the group and verify user is a member
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the expense and verify it belongs to the group
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    if expense.group_id != group_id:
        flash("Expense does not belong to this group", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Fetch comments ordered by created_at (chronological)
    comments = (
        Comment.query.filter_by(expense_id=expense_id).order_by(Comment.created_at.asc()).all()
    )

    # Process expense for display
    split_details = ExpenseService._parse_split_details(expense)
    participants = list(split_details.keys())

    # Collect all emails for display name lookup
    all_emails = set()
    all_emails.add(expense.payer)
    all_emails.update(participants)
    # Add comment authors
    for comment in comments:
        comment_user = db.session.get(User, comment.user_id)
        if comment_user:
            all_emails.add(comment_user.email)

    # Bulk fetch all users for the emails to avoid N+1 queries
    if all_emails:
        users = User.query.filter(User.email.in_(all_emails)).all()
        user_map = {user.email: user for user in users}
    else:
        users = []
        user_map = {}

    email_to_name = {}
    for email in all_emails:
        user_obj = user_map.get(email)
        if user_obj:
            email_to_name[email] = user_obj.display_name or user_obj.email
        else:
            email_to_name[email] = email  # Fallback to email if user not found

    return render_template(
        "groups/expense_detail.html",
        group=group,
        expense=expense,
        split_details=split_details,
        participants=participants,
        comments=comments,
        email_to_name=email_to_name,
        current_user_id=user_id,
    )


@groups_bp.route("/<int:group_id>/expense/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense(group_id, expense_id):
    """Delete an expense from a group."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the group and verify user is a member
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the expense and verify it belongs to the group
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    if expense.group_id != group_id:
        flash("Expense does not belong to this group", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Store expense details for notification before deletion
    expense_description = expense.description
    expense_amount = expense.amount
    expense_payer = expense.payer
    expense_participants = expense.participants
    deleter_name = user.display_name or user.email

    # Create a simple object for notification (expense will be deleted)
    class ExpenseInfo:
        def __init__(self, description, amount, payer, participants):
            self.description = description
            self.amount = amount
            self.payer = payer
            self.participants = participants

    expense_info = ExpenseInfo(
        expense_description, expense_amount, expense_payer, expense_participants
    )

    # Delete the expense
    db.session.delete(expense)
    db.session.commit()

    # Recalculate points for the group after deleting expense
    from services.points_service import PointsService

    try:
        PointsService.calculate_points_for_group(group_id)
    except Exception as e:
        print(f"Failed to recalculate points: {e}")

    # Send notifications to other group members (excluding the deleter)
    try:
        notify_expense_deletion(expense_info, user.email, group.members)
    except Exception as e:
        print(f"Failed to send deletion notifications: {e}")

    # Create database notification for all group members to see
    from models import GroupNotification

    notification = GroupNotification(
        group_id=group_id,
        notification_type="expense_deleted",
        description=expense_description,
        amount=expense_amount,
        payer=expense_payer,
        deleted_by=deleter_name,
        read_by="[]",  # Empty JSON array - no one has read it yet
    )
    db.session.add(notification)
    db.session.commit()

    flash("Expense deleted successfully!", "success")
    return redirect(url_for("groups.group_expenses", group_id=group_id))


@groups_bp.route("/<int:group_id>/expense/<int:expense_id>/edit", methods=["POST"])
@login_required
def edit_expense(group_id, expense_id):
    """Edit an expense in a group."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the group and verify user is a member
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the expense and verify it belongs to the group
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    if expense.group_id != group_id:
        flash("Expense does not belong to this group", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Extract form data
    description = request.form.get("description", "").strip()
    amount_raw = request.form.get("amount", "").strip()
    payer = request.form.get("payer", "").strip()
    split_type = request.form.get("split_type", "equal").strip()
    category = request.form.get("category", "").strip() or None

    # Validate required fields
    if not description:
        flash("Description is required", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    if not payer:
        flash("Payer is required", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    # Validate amount (must be > 0)
    try:
        amount = float(amount_raw)
        if amount <= 0:
            flash("Amount must be greater than zero", "error")
            return redirect(
                url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
            )
    except (ValueError, TypeError):
        flash("Please enter a valid amount", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    # Get group member emails for validation
    group_member_emails = [member.email for member in group.members]

    # Validate payer is in group
    if payer not in group_member_emails:
        flash("Payer must be a member of the group", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    # Handle participants and split details
    if split_type == "equal":
        # Get selected participants for equal split
        selected_participants = request.form.getlist("participants")
        if not selected_participants:
            flash("Please select at least one participant", "error")
            return redirect(
                url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
            )

        # Validate all participants are in group
        for participant in selected_participants:
            if participant not in group_member_emails:
                flash(f"Participant '{participant}' is not in the group", "error")
                return redirect(
                    url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
                )

        # Calculate equal split
        split_details = ExpenseService.calculate_equal_split(selected_participants, amount)

    elif split_type == "percentage":
        # Get percentage split
        split_details = {}
        for member_email in group_member_emails:
            percentage_key = f"percentage_{member_email}"
            percentage_value = request.form.get(percentage_key, "").strip()
            if percentage_value:
                try:
                    split_details[member_email] = float(percentage_value)
                except ValueError:
                    flash(f"Invalid percentage for {member_email}", "error")
                    return redirect(
                        url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
                    )

        if not split_details:
            flash("Please specify percentages for at least one participant", "error")
            return redirect(
                url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
            )

        # Validate percentage split
        is_valid, error_msg = ExpenseService.validate_percentage_split(split_details)
        if not is_valid:
            flash(error_msg, "error")
            return redirect(
                url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
            )

        # Calculate amounts from percentages
        split_details = ExpenseService.calculate_percentage_split(split_details, amount)

    elif split_type == "shares":
        # Get shares split
        split_details = {}
        for member_email in group_member_emails:
            shares_key = f"shares_{member_email}"
            shares_value = request.form.get(shares_key, "").strip()
            if shares_value:
                try:
                    split_details[member_email] = float(shares_value)
                except ValueError:
                    flash(f"Invalid shares for {member_email}", "error")
                    return redirect(
                        url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
                    )

        if not split_details:
            flash("Please specify shares for at least one participant", "error")
            return redirect(
                url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
            )

        # Validate shares split
        is_valid, error_msg = ExpenseService.validate_shares_split(split_details)
        if not is_valid:
            flash(error_msg, "error")
            return redirect(
                url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
            )

        # Calculate amounts from shares
        split_details = ExpenseService.calculate_shares_split(split_details, amount)

    else:  # custom split
        # Get custom split amounts
        split_details = {}
        for member_email in group_member_emails:
            amount_key = f"custom_amount_{member_email}"
            custom_amount = request.form.get(amount_key, "").strip()
            if custom_amount:
                try:
                    split_details[member_email] = float(custom_amount)
                except ValueError:
                    flash(f"Invalid amount for {member_email}", "error")
                    return redirect(
                        url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
                    )

        if not split_details:
            flash("Please specify amounts for at least one participant", "error")
            return redirect(
                url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
            )

        # Validate custom split
        is_valid, error_msg = ExpenseService.validate_custom_split(split_details, amount)
        if not is_valid:
            flash(error_msg, "error")
            return redirect(
                url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id)
            )

    # Store editor name for notification
    editor_name = user.display_name or user.email

    # Create a simple object for notification
    class ExpenseInfo:
        def __init__(self, description, amount, payer, participants):
            self.description = description
            self.amount = amount
            self.payer = payer
            self.participants = participants

    expense_info = ExpenseInfo(description, amount, payer, ", ".join(split_details.keys()))

    # Update expense
    expense.description = description
    expense.amount = amount
    expense.payer = payer
    expense.split_type = split_type
    expense.split_details = json.dumps(split_details)
    expense.participants = ", ".join(split_details.keys())  # Keep for backward compatibility
    expense.category = category  # Update category (expense_date remains unchanged)
    db.session.commit()

    # Recalculate points for the group after editing expense
    from services.points_service import PointsService

    try:
        PointsService.calculate_points_for_group(group_id)
    except Exception as e:
        print(f"Failed to recalculate points: {e}")

    # Send notifications to other group members (excluding the editor)
    try:
        notify_expense_edited(expense_info, user.email, group.members)
    except Exception as e:
        print(f"Failed to send edit notifications: {e}")

    # Create database notification for all group members to see
    from models import GroupNotification

    notification = GroupNotification(
        group_id=group_id,
        notification_type="expense_edited",
        description=description,
        amount=amount,
        payer=payer,
        edited_by=editor_name,
        read_by="[]",  # Empty JSON array - no one has read it yet
    )
    db.session.add(notification)
    db.session.commit()

    flash("Expense updated successfully!", "success")
    return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))


@groups_bp.route("/<int:group_id>/expense/<int:expense_id>/comment", methods=["POST"])
@login_required
def create_comment(group_id, expense_id):
    """Create a comment on an expense."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the group and verify user is a member
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the expense and verify it belongs to the group
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    if expense.group_id != group_id:
        flash("Expense does not belong to this group", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Get comment content
    content = request.form.get("content", "").strip()

    # Validate comment content
    if not content:
        flash("Comment cannot be empty", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    # Create comment
    comment = Comment(
        expense_id=expense_id,
        user_id=user_id,
        content=content,
    )
    db.session.add(comment)
    db.session.commit()

    flash("Comment posted successfully!", "success")
    return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))


@groups_bp.route(
    "/<int:group_id>/expense/<int:expense_id>/comment/<int:comment_id>/edit", methods=["POST"]
)
@login_required
def edit_comment(group_id, expense_id, comment_id):
    """Edit a comment on an expense."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the group and verify user is a member
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the expense and verify it belongs to the group
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    if expense.group_id != group_id:
        flash("Expense does not belong to this group", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Get the comment and verify it belongs to the expense and user
    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash("Comment not found", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    if comment.expense_id != expense_id:
        flash("Comment does not belong to this expense", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    if comment.user_id != user_id:
        flash("You can only edit your own comments", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    # Get updated comment content
    content = request.form.get("content", "").strip()

    # Validate comment content
    if not content:
        flash("Comment cannot be empty", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    # Update comment
    comment.content = content
    db.session.commit()

    flash("Comment updated successfully!", "success")
    return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))


@groups_bp.route(
    "/<int:group_id>/expense/<int:expense_id>/comment/<int:comment_id>/delete", methods=["POST"]
)
@login_required
def delete_comment(group_id, expense_id, comment_id):
    """Delete a comment on an expense."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the group and verify user is a member
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Get the expense and verify it belongs to the group
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    if expense.group_id != group_id:
        flash("Expense does not belong to this group", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Get the comment and verify it belongs to the expense and user
    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash("Comment not found", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    if comment.expense_id != expense_id:
        flash("Comment does not belong to this expense", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    if comment.user_id != user_id:
        flash("You can only delete your own comments", "error")
        return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))

    # Delete comment
    db.session.delete(comment)
    db.session.commit()

    flash("Comment deleted successfully!", "success")
    return redirect(url_for("groups.expense_detail", group_id=group_id, expense_id=expense_id))


@groups_bp.route("/<int:group_id>/notification/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(group_id, notification_id):
    """Mark a notification as read by the current user."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        return redirect(url_for("groups.list_groups"))

    from models import GroupNotification

    notification = db.session.get(GroupNotification, notification_id)
    if not notification or notification.group_id != group_id:
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Verify user is a member of the group
    group = db.session.get(Group, group_id)
    if not group or user not in group.members:
        return redirect(url_for("groups.list_groups"))

    # Mark as read by this user
    read_by_ids = json.loads(notification.read_by) if notification.read_by else []
    if user.id not in read_by_ids:
        read_by_ids.append(user.id)
        notification.read_by = json.dumps(read_by_ids)
        db.session.commit()

    return redirect(url_for("groups.group_expenses", group_id=group_id))


@groups_bp.route("/<int:group_id>/leave", methods=["POST"])
@login_required
def leave_group(group_id):
    """Remove the current user from the group."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Load the group
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Must be a member
    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Prevent the *creator* from leaving (optional – you can remove this block if you want to allow it)
    if group.created_by_id == user.id:
        flash("The group creator cannot leave the group.", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Remove the relationship
    group.members.remove(user)

    # If the group ends up with **zero** members, delete it (optional)
    if len(group.members) == 0:
        db.session.delete(group)
        flash("You left the group and it was removed (no members left).", "info")
    else:
        flash(f"You have left the group “{group.name}”.", "success")

    db.session.commit()
    return redirect(url_for("groups.list_groups"))


@groups_bp.route("/<int:group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    """Delete the group — only the creator may delete the group."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Verify membership
    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Only creator can delete
    if group.created_by_id != user.id:
        flash("Only the group creator can delete this group.", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    # Delete group and redirect to groups list
    # Delete related child objects first to avoid FK NOT NULL issues (invitations, notifications, expenses)
    # Invitations have group_id non-nullable so they must be removed before deleting the group.
    try:
        # Delete invitations
        for inv in list(group.invitations):
            db.session.delete(inv)

        # Delete notifications

        for note in list(group.notifications):
            db.session.delete(note)

        # Delete expenses (and their comments via cascade defined on Comment)
        for exp in list(group.expenses):
            db.session.delete(exp)

        db.session.delete(group)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to delete group due to related data constraints.", "error")
        return redirect(url_for("groups.group_expenses", group_id=group_id))

    flash(f"Group '{group.name}' deleted successfully.", "success")
    return redirect(url_for("groups.list_groups"))


@groups_bp.route("/<int:group_id>/settings")
@login_required
def group_settings(group_id):
    """Display group settings page."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Verify membership
    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    return render_template("groups/settings.html", group=group)


@groups_bp.route("/<int:group_id>/upload-picture", methods=["POST"])
@login_required
def upload_group_picture(group_id):
    """Upload a profile picture for a group."""
    import os

    from PIL import Image
    from werkzeug.utils import secure_filename

    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Verify membership
    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Check if file was uploaded
    if "profile_picture" not in request.files:
        flash("No file uploaded", "error")
        return redirect(url_for("groups.group_settings", group_id=group_id))

    file = request.files["profile_picture"]

    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("groups.group_settings", group_id=group_id))

    # Validate file type
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    file_ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""

    if file_ext not in allowed_extensions:
        flash("Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF, or WEBP).", "error")
        return redirect(url_for("groups.group_settings", group_id=group_id))

    # Generate unique filename
    filename = secure_filename(
        f"group_{group_id}_{datetime.now(timezone.utc).timestamp()}.{file_ext}"
    )
    upload_folder = os.path.join("static", "uploads", "group_pics")
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)

    try:
        # Open and resize image
        img = Image.open(file.stream)

        # Convert RGBA to RGB if necessary
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background

        # Resize to max 500x500 while maintaining aspect ratio
        img.thumbnail((500, 500), Image.Resampling.LANCZOS)

        # Save as JPEG with optimization
        img.save(filepath, "JPEG", quality=85, optimize=True)

        # Delete old profile picture if exists
        if group.profile_picture:
            old_filepath = os.path.join(upload_folder, group.profile_picture)
            if os.path.exists(old_filepath):
                os.remove(old_filepath)

        # Update group record
        group.profile_picture = filename
        db.session.commit()

        flash("Group picture updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to upload picture: {str(e)}", "error")

    return redirect(url_for("groups.group_settings", group_id=group_id))


@groups_bp.route("/<int:group_id>/delete-picture", methods=["POST"])
@login_required
def delete_group_picture(group_id):
    """Delete a group's profile picture."""
    import os

    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Verify membership
    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    if not group.profile_picture:
        flash("No picture to delete", "error")
        return redirect(url_for("groups.group_settings", group_id=group_id))

    try:
        # Delete file from filesystem
        filepath = os.path.join("static", "uploads", "group_pics", group.profile_picture)
        if os.path.exists(filepath):
            os.remove(filepath)

        # Update database
        group.profile_picture = None
        db.session.commit()

        flash("Group picture deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete picture: {str(e)}", "error")

    return redirect(url_for("groups.group_settings", group_id=group_id))


@groups_bp.route("/<int:group_id>/edit-name", methods=["POST"])
@login_required
def edit_group_name(group_id):
    """Edit group name."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Verify membership
    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Get new group name from form
    new_name = request.form.get("group_name", "").strip()

    if not new_name:
        flash("Group name cannot be empty", "error")
        return redirect(url_for("groups.group_settings", group_id=group_id))

    if len(new_name) > 100:
        flash("Group name must be 100 characters or less", "error")
        return redirect(url_for("groups.group_settings", group_id=group_id))

    try:
        old_name = group.name
        group.name = new_name
        db.session.commit()
        flash(f"Group renamed from '{old_name}' to '{new_name}'", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to rename group: {str(e)}", "error")

    return redirect(url_for("groups.group_settings", group_id=group_id))


@groups_bp.route("/<int:group_id>/invite-members", methods=["POST"])
@login_required
def invite_members(group_id):
    """Invite members to group by email address.

    Similar to group creation flow - sends invitations to provided emails.
    """
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Verify membership
    if user not in group.members:
        flash("You are not a member of this group", "error")
        return redirect(url_for("groups.list_groups"))

    # Get email addresses from form
    member_emails = request.form.get("member_emails", "").strip()

    if not member_emails:
        flash("Please enter at least one email address", "error")
        return redirect(url_for("groups.group_settings", group_id=group_id))

    # Parse and validate emails
    emails = [email.strip() for email in member_emails.split(",") if email.strip()]

    # Validate all email formats first
    for email in emails:
        if not is_valid_email(email):
            flash(f"Invalid email format: {email}", "error")
            return redirect(url_for("groups.group_settings", group_id=group_id))

    try:
        invitations_sent = 0
        already_members = []
        already_invited = []

        for email in emails:
            # Check if user is already a member
            existing_member = User.query.filter_by(email=email).first()
            if existing_member and existing_member in group.members:
                already_members.append(email)
                continue

            # Check if invitation already exists
            existing_invitation = GroupInvitation.query.filter_by(
                email=email, group_id=group_id, status="pending"
            ).first()

            if existing_invitation:
                already_invited.append(email)
                continue

            # Create new invitation
            invitation = GroupInvitation(email=email, group_id=group_id, invited_by_id=user_id)
            db.session.add(invitation)
            invitations_sent += 1

            # Send invitation notification
            try:
                notify_group_invitation(user.email, email, group.name)
            except Exception as e:
                print(f"Failed to send invitation notification to {email}: {e}")

        db.session.commit()

        # Build success message
        messages = []
        if invitations_sent > 0:
            messages.append(f"{invitations_sent} invitation(s) sent successfully!")
        if already_members:
            messages.append(f"Already members: {', '.join(already_members)}")
        if already_invited:
            messages.append(f"Already invited: {', '.join(already_invited)}")

        if invitations_sent > 0:
            flash(" | ".join(messages), "success")
        else:
            flash(" | ".join(messages), "info")

    except Exception as e:
        db.session.rollback()
        flash(f"Failed to send invitations: {str(e)}", "error")

    return redirect(url_for("groups.group_settings", group_id=group_id))
