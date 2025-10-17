"""Authentication and authorization decorators."""

from functools import wraps

from flask import redirect, session, url_for


def login_required(f):
    """Decorator to require login for a route."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function
