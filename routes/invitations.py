"""Invitation management routes."""

from flask import Blueprint, flash, redirect, render_template, session, url_for

from extensions import db
from models import GroupInvitation, User
from utils.decorators import login_required

invitations_bp = Blueprint("invitations", __name__, url_prefix="/invitations")


@invitations_bp.route("/")
@login_required
def list_invitations():
    """Display all pending invitations for the current user."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("home.index"))

    # Get pending invitations for this user's email
    pending_invitations = (
        GroupInvitation.query.filter_by(email=user.email, status="pending")
        .order_by(GroupInvitation.created_at.desc())
        .all()
    )

    return render_template("invitations/index.html", invitations=pending_invitations)


@invitations_bp.route("/<int:invitation_id>/accept", methods=["POST"])
@login_required
def accept_invitation(invitation_id):
    """Accept a group invitation."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("invitations.list_invitations"))

    # Get the invitation
    invitation = db.session.get(GroupInvitation, invitation_id)

    if not invitation:
        flash("Invitation not found", "error")
        return redirect(url_for("invitations.list_invitations"))

    # Verify the invitation is for this user
    if invitation.email != user.email:
        flash("You are not authorized to accept this invitation", "error")
        return redirect(url_for("invitations.list_invitations"))

    # Verify invitation is still pending
    if invitation.status != "pending":
        flash("This invitation has already been processed", "info")
        return redirect(url_for("invitations.list_invitations"))

    try:
        # Add user to the group
        if user not in invitation.group.members:
            invitation.group.members.append(user)

        # Mark invitation as accepted
        invitation.status = "accepted"

        db.session.commit()
        flash(f"Successfully joined '{invitation.group.name}'!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to accept invitation: {str(e)}", "error")

    return redirect(url_for("invitations.list_invitations"))


@invitations_bp.route("/<int:invitation_id>/decline", methods=["POST"])
@login_required
def decline_invitation(invitation_id):
    """Decline a group invitation."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("invitations.list_invitations"))

    # Get the invitation
    invitation = db.session.get(GroupInvitation, invitation_id)

    if not invitation:
        flash("Invitation not found", "error")
        return redirect(url_for("invitations.list_invitations"))

    # Verify the invitation is for this user
    if invitation.email != user.email:
        flash("You are not authorized to decline this invitation", "error")
        return redirect(url_for("invitations.list_invitations"))

    # Verify invitation is still pending
    if invitation.status != "pending":
        flash("This invitation has already been processed", "info")
        return redirect(url_for("invitations.list_invitations"))

    try:
        # Mark invitation as declined
        invitation.status = "declined"

        db.session.commit()
        flash(f"Declined invitation to '{invitation.group.name}'", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to decline invitation: {str(e)}", "error")

    return redirect(url_for("invitations.list_invitations"))
