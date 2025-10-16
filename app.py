import os
import random
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for
from flask_mail import Message

from extensions import db, mail

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email configuration (for development, we'll print to console)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "your-email@gmail.com")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "your-password")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME", "your-email@gmail.com")
app.config["MAIL_SUPPRESS_SEND"] = True  # Don't actually send emails in development

db.init_app(app)
mail.init_app(app)

from models import Expense, User  # noqa: E402


# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home():
    return render_template("home/index.html", page_id="home")


# Authentication routes
@app.route("/auth/login")
def login():
    """Display login page."""
    # If user is already logged in, redirect to expense splitter
    if "user_id" in session:
        return redirect(url_for("expense_splitter"))
    return render_template("auth/login.html", page_id="login")


@app.route("/auth/request-otp", methods=["POST"])
def request_otp():
    """Generate and send OTP to user's email."""
    email = request.form.get("email", "").strip()

    if not email:
        return "Email is required", 400

    # Generate 6-digit OTP
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

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


@app.route("/auth/verify-otp", methods=["POST"])
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

    return redirect(url_for("expense_splitter"))


@app.route("/auth/logout")
def logout():
    """Log out user by clearing session."""
    session.clear()
    return redirect(url_for("home"))


@app.route("/expense-splitter", methods=["GET", "POST"])
@login_required
def expense_splitter():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        amount_raw = request.form.get("amount", "").strip()
        payer = request.form.get("payer", "").strip()
        participants = request.form.get("participants", "").strip()

        try:
            amount = float(amount_raw)
        except ValueError:
            amount = None

        if description and amount is not None and payer:
            expense = Expense(
                description=description,
                amount=amount,
                payer=payer,
                participants=participants or None,
            )
            db.session.add(expense)
            db.session.commit()

        return redirect(url_for("expense_splitter"))

    expenses = Expense.query.order_by(Expense.created_at.desc()).all()
    expense_views = []
    for expense in expenses:
        people = [p.strip() for p in (expense.participants or "").split(",") if p.strip()]
        share = expense.amount / len(people) if people else None
        expense_views.append({"model": expense, "participants": people, "share": share})

    return render_template(
        "apps/expense_splitter/index.html", page_id="expense-splitter", expenses=expense_views
    )


def init_db():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    init_db()  # Always ensure tables exist on startup
    app.run(debug=True)
