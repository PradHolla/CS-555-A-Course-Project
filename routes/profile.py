"""Profile management routes."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from models import User
from services.profile_service import delete_profile_picture, save_profile_picture
from utils.decorators import login_required

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/", methods=["GET"])
@login_required
def view_profile():
    """Display the user's profile page."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    # User existence is guaranteed by @login_required decorator
    from services.profile_service import get_profile_picture_url

    return render_template(
        "profile/index.html", user=user, get_profile_picture_url=get_profile_picture_url
    )


@profile_bp.route("/", methods=["POST"])
@login_required
def update_profile():
    """Update the user's display name."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    # User existence is guaranteed by @login_required decorator

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


@profile_bp.route("/upload-picture", methods=["POST"])
@login_required
def upload_picture():
    """Upload a profile picture."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    # User existence is guaranteed by @login_required decorator

    # Check if file was uploaded
    if "profile_picture" not in request.files:
        flash("No file selected", "error")
        return redirect(url_for("profile.view_profile"))

    file = request.files["profile_picture"]

    # Check if filename is empty
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("profile.view_profile"))

    # Save the profile picture
    success, message = save_profile_picture(user, file)

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("profile.view_profile"))


@profile_bp.route("/delete-picture", methods=["POST"])
@login_required
def delete_picture():
    """Delete the user's profile picture."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    # User existence is guaranteed by @login_required decorator

    success, message = delete_profile_picture(user)

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("profile.view_profile"))



@profile_bp.route("/notification-preferences", methods=["PATCH", "POST"])
@login_required
def update_notification_preferences():
    """Update user's notification preferences."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    
    # Support both JSON and form data
    if request.is_json:
        data = request.get_json()
        daily_enabled = data.get("dailyExpenseNotificationsEnabled")
        is_ajax = True
    else:
        daily_enabled = request.form.get("daily_reminder_enabled")
        if daily_enabled is not None:
            daily_enabled = daily_enabled.lower() in ["true", "1", "on", "yes"]
        is_ajax = False
    
    # Validate input
    if daily_enabled is None:
        if is_ajax:
            return jsonify({"error": "Missing dailyExpenseNotificationsEnabled field"}), 400
        flash("Invalid notification preference", "error")
        return redirect(url_for("profile.view_profile"))
    
    # Update preference
    try:
        user.daily_reminder_enabled = daily_enabled
        db.session.commit()
        
        status = "enabled" if daily_enabled else "disabled"
        message = f"Daily notifications {status} successfully"
        
        if is_ajax:
            return jsonify({
                "message": message,
                "data": {
                    "user_id": user.id,
                    "email": user.email,
                    "daily_reminder_enabled": user.daily_reminder_enabled
                }
            }), 200
        else:
            flash(message, "success")
            return redirect(url_for("profile.view_profile"))
            
    except Exception as e:
        db.session.rollback()
        error_msg = f"Failed to update notification preference: {str(e)}"
        
        if is_ajax:
            return jsonify({"error": error_msg}), 500
        else:
            flash(error_msg, "error")
            return redirect(url_for("profile.view_profile"))
