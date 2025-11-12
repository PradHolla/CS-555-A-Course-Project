"""Main Flask application with blueprint registration."""

import os
import sqlite3

from dotenv import load_dotenv
from flask import Flask

from extensions import db, mail
from sqlalchemy import text

# Import models to ensure they're registered with SQLAlchemy
from models import Expense, Settlement, User  # noqa: F401

# Load environment variables from .env file
load_dotenv()


def create_app(test_config=None):
    """Application factory pattern."""
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # File upload configuration
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads", "profile_pics")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max file size
    app.config["ALLOWED_EXTENSIONS"] = {"jpg", "jpeg", "png", "gif", "webp"}

    # Email configuration
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "your-email@gmail.com")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "your-password")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME", "your-email@gmail.com")
    app.config["MAIL_SUPPRESS_SEND"] = False  # Always allow email sending (OTP needs this)

    # Payment notification email control: Set EMAIL_ENABLED=true in .env to send actual payment emails
    # When false, payment notifications are logged to terminal instead
    # Note: OTP emails are always sent regardless of this setting
    email_enabled = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"
    app.config["EMAIL_ENABLED"] = email_enabled

    # Initialize extensions
    # Apply test overrides when provided (used by tests to change DB URI etc.)
    if test_config:
        app.config.update(test_config)

    # Initialize extensions after config is finalized
    db.init_app(app)
    mail.init_app(app)

    # ✅ Register blueprints (cleaned up)
    from routes.auth import auth_bp
    from routes.expenses import expenses_bp
    from routes.home import home_bp
    from routes.settlements import settlements_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(settlements_bp)

    from routes.dashboard import dashboard_bp
    from routes.groups import groups_bp
    from routes.invitations import invitations_bp
    from routes.profile import profile_bp

    app.register_blueprint(groups_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(invitations_bp)

    # Context processor to make current_user available in all templates
    @app.context_processor
    def inject_current_user():
        from flask import session as flask_session

        user_id = flask_session.get("user_id")
        current_user = None
        if user_id:
            current_user = db.session.get(User, user_id)
        return dict(current_user=current_user)

    return app


def init_db(app):
    """Initialize database tables."""
    with app.app_context():
        db.create_all()
        # Ensure new nullable columns exist on legacy sqlite DBs (no-op if already present)
        try:
            uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            # Only attempt sqlite-file adjustments
            if uri and uri.startswith("sqlite:///"):
                db_file = uri.replace("sqlite:///", "", 1)
                # Use sqlite3 directly to avoid SQLAlchemy connection/transaction nuances
                conn = sqlite3.connect(db_file)
                cur = conn.cursor()

                cur.execute("PRAGMA table_info('user')")
                user_cols = [row[1] for row in cur.fetchall()]
                if 'profile_picture' not in user_cols:
                    cur.execute('ALTER TABLE user ADD COLUMN profile_picture VARCHAR(200)')

                cur.execute("PRAGMA table_info('group')")
                group_cols = [row[1] for row in cur.fetchall()]
                if 'profile_picture' not in group_cols:
                    # group is a reserved word; quote it with double quotes for SQLite
                    cur.execute('ALTER TABLE "group" ADD COLUMN profile_picture VARCHAR(200)')

                conn.commit()
                conn.close()
        except Exception as e:
            # If the DB engine doesn't support ALTER or PRAGMA for some reason, don't crash startup.
            print(f"Schema adjustment skipped: {e}")


# Create app instance
app = create_app()

if __name__ == "__main__":
    init_db(app)  # Always ensure tables exist on startup
    app.run(debug=True)
