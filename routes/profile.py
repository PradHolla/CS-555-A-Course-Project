"""Profile management routes."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import User
from utils.decorators import login_required

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/", methods=["GET"])
@login_required
def view_profile():
    """Display the user's profile page."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("home.index"))

    return render_template("profile/index.html", user=user)


@profile_bp.route("/", methods=["POST"])
@login_required
def update_profile():
    """Update the user's display name."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("home.index"))

    display_name = request.form.get("display_name", "").strip()

    # Validate display name
    if not display_name:
        flash("Display name cannot be empty", "error")
        return redirect(url_for("profile.view_profile"))

    if len(display_name) > 100:
        flash("Display name must be 100 characters or less", "error")
        return redirect(url_for("profile.view_profile"))

    try:
        user.display_name = display_name
        db.session.commit()
        flash("Profile updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update profile: {str(e)}", "error")

    return redirect(url_for("profile.view_profile"))
