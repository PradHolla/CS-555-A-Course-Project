from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import Group, GroupInvitation, User
from services.notification_service import notify_group_invitation
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


@groups_bp.route("/create", methods=["POST"])
@login_required
def create_group():
    """Create a new group and add the creator as the first member."""
    name = request.form.get("name", "").strip()
    member_emails = request.form.get("members", "").strip()

    # Validate inputs
    if not name:
        flash("Group name is required.", "error")
        return redirect(url_for("groups.list_groups"))

    user_id = session.get("user_id")
    creator = db.session.get(User, user_id)

    if not creator:
        flash("User not found", "error")
        return redirect(url_for("groups.list_groups"))

    # Validate all email formats BEFORE any DB operations
    if member_emails:
        emails = [email.strip() for email in member_emails.split(",") if email.strip()]
        for email in emails:
            if not is_valid_email(email):
                flash(f"Invalid email format: {email}", "error")
                return redirect(url_for("groups.list_groups"))

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
        return redirect(url_for("groups.list_groups"))

    return redirect(url_for("groups.list_groups"))
