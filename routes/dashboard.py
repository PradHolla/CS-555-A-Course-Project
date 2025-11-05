"""Dashboard routes blueprint."""

import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from models import User
from services.dashboard_service import DashboardService
from utils.decorators import login_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

logger = logging.getLogger(__name__)


@dashboard_bp.route("", methods=["GET"])
@login_required
def index():
    """
    Display dashboard with financial summary.

    Returns JSON if Accept header is application/json,
    otherwise returns HTML template.
    """
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    # Handle missing user case
    if not user:
        session.clear()
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    try:
        # Get financial summary
        summary = DashboardService.get_user_summary(user_id)

        # Return JSON for API requests
        if request.accept_mimetypes.best == "application/json":
            return jsonify(summary), 200

        # Return HTML for browser requests
        return render_template(
            "dashboard/index.html", user=user, summary=summary, page_id="dashboard"
        )
    except Exception as e:
        logger.error(f"Dashboard error for user {user_id}: {str(e)}")
        # Return error response with empty summary
        summary = {
            "total_expenses": 0.0,
            "total_payments": 0.0,
            "outstanding_balance": 0.0,
            "has_data": False,
        }

        if request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Failed to load dashboard data", "summary": summary}), 500

        flash("Unable to load dashboard data. Please try again later.", "error")
        return render_template(
            "dashboard/index.html", user=user, summary=summary, page_id="dashboard"
        )
