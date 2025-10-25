"""Authentication and authorization decorators."""

from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(f):
    """Decorator to require login for a route."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))

        # Validate that the user actually exists in the database
        from extensions import db
        from models import User

        user = db.session.get(User, session["user_id"])
        if not user:
            # Session is stale (user deleted or database reset)
            session.clear()
            flash("Your session has expired. Please log in again.", "error")
            return redirect(url_for("auth.login"))

        return f(*args, **kwargs)

    return decorated_function
