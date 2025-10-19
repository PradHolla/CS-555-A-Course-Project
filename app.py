"""Main Flask application with blueprint registration."""

import os
from dotenv import load_dotenv

from flask import Flask

from extensions import db, mail

# Import models to ensure they're registered with SQLAlchemy
from models import Expense, User, Settlement  # noqa: F401

# Load environment variables from .env file
load_dotenv()


def create_app():
    """Application factory pattern."""
    app = Flask(__name__)

    # Configuration
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
    app.config["MAIL_SUPPRESS_SEND"] = False  # Enable actual email sending

    # Initialize extensions
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

    return app



def init_db(app):
    """Initialize database tables."""
    with app.app_context():
        db.create_all()


# Create app instance
app = create_app()

if __name__ == "__main__":
    init_db(app)  # Always ensure tables exist on startup
    app.run(debug=True)
