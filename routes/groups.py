import json

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import Expense, Group, GroupInvitation, User
from services.expense_service import ExpenseService
from services.notification_service import notify_expense_participants, notify_group_invitation
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
    return render_template("groups/index.html", groups=groups)


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

                # Find existing user
                user = User.query.filter_by(email=email).first()

                if user:
                    # User exists - add them to the group
                    if user not in group.members:
                        group.members.append(user)
                else:
                    # User doesn't exist - create invitation
                    # Check if invitation already exists
                    existing_invitation = GroupInvitation.query.filter_by(
                        email=email, group_id=group.id, status="pending"
                    ).first()

                    if not existing_invitation:
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
        )
        db.session.add(expense)
        db.session.commit()

        # Send email notifications to participants (excluding the payer)
        participant_list = [email for email in split_details.keys() if email != payer]
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
        expense_views.append(
            {
                "model": expense,
                "participants": participants,
                "share": share,
                "split_details": split_details,
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

    return render_template(
        "groups/expenses.html",
        group=group,
        expenses=expense_views,
        groups_data=groups_data,
        email_to_name=email_to_name,
    )
