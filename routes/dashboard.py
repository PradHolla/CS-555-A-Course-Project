"""Dashboard routes blueprint."""

from flask import Blueprint, render_template, session

from services.dashboard_service import DashboardService
from utils.decorators import login_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    """Display user dashboard with financial summary."""
    user_id = session.get("user_id")
    
    # Get financial summary
    summary = DashboardService.get_user_summary(user_id)
    
    return render_template(
        "dashboard/index.html",
        page_id="dashboard",
        summary=summary
    )
