"""Authentication routes blueprint."""

from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_mail import Message

from extensions import db, mail
from models import User
from services.auth_service import AuthService
from utils.validators import is_valid_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


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

    # Send OTP email (in development, just print it)
    try:
        msg = Message(
            subject="Your Login Code - Expense Splitter",
            recipients=[email],
            body=f"Your verification code is: {otp}\n\nThis code expires in 10 minutes.",
        )
        mail.send(msg)
        print(f"OTP for {email}: {otp}")  # For development/testing
    except Exception as e:
        print(f"Email sending failed: {e}. OTP: {otp}")  # Fallback for development

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
