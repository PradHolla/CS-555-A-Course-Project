"""Authentication routes blueprint."""

import logging
import sys

from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_mail import Message

from extensions import db, mail
from models import GroupInvitation, User
from services.auth_service import AuthService
from utils.validators import is_valid_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Configure logger for OTP output
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@auth_bp.route("/login")
def login():
    """Display login page."""
    # If user is already logged in, redirect to groups page
    if "user_id" in session:
        return redirect(url_for("groups.list_groups"))
    return render_template("auth/login.html", page_id="login")


@auth_bp.route("/request-otp", methods=["POST"])
def request_otp():
    """Generate and send OTP to user's email."""
    email = request.form.get("email", "").strip()

    if not email:
        return "Email is required", 400

    # Validate email format
    if not is_valid_email(email):
        return "Invalid email format", 400

    # Generate OTP using service
    otp = AuthService.generate_otp()
    otp_expiry = AuthService.get_otp_expiry()

    # Find or create user
    user = User.query.filter_by(email=email).first()
    if user:
        # Update existing user's OTP
        user.otp = otp
        user.otp_expiry = otp_expiry
    else:
        # Create new user
        user = User(email=email, otp=otp, otp_expiry=otp_expiry)
        db.session.add(user)

    db.session.commit()

    # Log OTP to terminal and file with enhanced visibility
    otp_message = (
        f"\n\n"
        f"{'=' * 70}\n"
        f"{'=' * 70}\n"
        f"🔐 OTP REQUESTED\n"
        f"{'=' * 70}\n"
        f"   Email: {email}\n"
        f"   OTP Code: {otp}\n"
        f"   Valid for: 10 minutes\n"
        f"{'=' * 70}\n"
        f"{'=' * 70}\n\n"
    )
    
    # Print to terminal with multiple methods for maximum visibility
    print(otp_message, flush=True)
    sys.stdout.flush()
    
    # Also write to stderr for guaranteed visibility
    sys.stderr.write(otp_message)
    sys.stderr.flush()
    
    # Print a simple version for easy copying
    print(f">>> COPY THIS OTP: {otp} <<<\n", flush=True)
    
    # Write to file as backup
    try:
        from datetime import datetime
        with open("otp_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} - Email: {email}, OTP: {otp}\n")
            f.flush()
    except Exception as log_error:
        logger.error(f"Failed to write OTP to file: {log_error}")

    # Send OTP email
    try:
        msg = Message(
            subject="Your Login Code - Expense Splitter",
            recipients=[email],
            body=f"Your verification code is: {otp}\n\nThis code expires in 10 minutes.",
        )
        mail.send(msg)
        logger.info(f"OTP email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Email sending failed for {email}: {e}")

    return render_template("auth/verify.html", email=email, page_id="verify")


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP and log in user."""
    email = request.form.get("email", "").strip()
    entered_otp = request.form.get("otp", "").strip()

    if not email or not entered_otp:
        return "Email and OTP are required", 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.is_otp_valid(entered_otp):
        return "Invalid or expired OTP", 400

    # Clear OTP after successful verification
    user.otp = None
    user.otp_expiry = None

    # Auto-accept any pending group invitations for this email
    pending_invitations = GroupInvitation.query.filter_by(email=user.email, status="pending").all()
    for invitation in pending_invitations:
        # Add user to the group
        if user not in invitation.group.members:
            invitation.group.members.append(user)
        # Mark invitation as accepted
        invitation.status = "accepted"

    db.session.commit()

    # Create session
    session["user_id"] = user.id
    session["user_email"] = user.email

    return redirect(url_for("groups.list_groups"))


@auth_bp.route("/logout")
def logout():
    """Log out user by clearing session."""
    session.clear()
    return redirect(url_for("home.index"))
