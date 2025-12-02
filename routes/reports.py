"""Routes for expense report generation and download."""

import logging
from datetime import datetime

from flask import Blueprint, Response, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import User
from services.expense_report_service import ExpenseReportService
from utils.decorators import login_required

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")
logger = logging.getLogger(__name__)


@reports_bp.route("/monthly-expense", methods=["GET"])
@login_required
def monthly_expense_form():
    """Display form for selecting month/year and filters for expense report."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("home.index"))
    user_groups = user.groups.all()
    categories = ExpenseReportService.get_available_categories(user_id)
    now = datetime.now()
    return render_template("reports/monthly_expense.html", page_id="monthly-expense-report", user_groups=user_groups, categories=categories, default_year=now.year, default_month=now.month, current_year=now.year)


@reports_bp.route("/monthly-expense/pdf", methods=["POST"])
@login_required
def download_pdf():
    """Generate and download PDF expense report."""
    user_id = session.get("user_id")
    try:
        year = int(request.form.get("year", datetime.now().year))
        month = int(request.form.get("month", datetime.now().month))
        group_ids = request.form.getlist("group_ids")
        category = request.form.get("category", "").strip() or None
        group_ids = [int(gid) for gid in group_ids if gid] if group_ids else None
        is_valid, error_msg = ExpenseReportService.validate_date_range(year, month)
        if not is_valid:
            flash(error_msg, "error")
            return redirect(url_for("reports.monthly_expense_form"))
        report_data = ExpenseReportService.get_monthly_expenses(user_id=user_id, year=year, month=month, group_ids=group_ids, category=category)
        if report_data.get("error"):
            flash(f"Error generating report: {report_data['error']}", "error")
            return redirect(url_for("reports.monthly_expense_form"))
        pdf_content = ExpenseReportService.generate_pdf(report_data)
        month_name = datetime(year, month, 1).strftime("%B")
        filename = f"expense-report-{year}-{month:02d}-{month_name}.pdf"
        return Response(pdf_content, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except ValueError as e:
        flash(f"Invalid input: {str(e)}", "error")
        return redirect(url_for("reports.monthly_expense_form"))
    except Exception as e:
        logger.error(f"Error generating PDF report: {str(e)}", exc_info=True)
        flash("An error occurred while generating the report. Please try again.", "error")
        return redirect(url_for("reports.monthly_expense_form"))


@reports_bp.route("/monthly-expense/csv", methods=["POST"])
@login_required
def download_csv():
    """Generate and download CSV expense report."""
    user_id = session.get("user_id")
    try:
        year = int(request.form.get("year", datetime.now().year))
        month = int(request.form.get("month", datetime.now().month))
        group_ids = request.form.getlist("group_ids")
        category = request.form.get("category", "").strip() or None
        group_ids = [int(gid) for gid in group_ids if gid] if group_ids else None
        is_valid, error_msg = ExpenseReportService.validate_date_range(year, month)
        if not is_valid:
            flash(error_msg, "error")
            return redirect(url_for("reports.monthly_expense_form"))
        report_data = ExpenseReportService.get_monthly_expenses(user_id=user_id, year=year, month=month, group_ids=group_ids, category=category)
        if report_data.get("error"):
            flash(f"Error generating report: {report_data['error']}", "error")
            return redirect(url_for("reports.monthly_expense_form"))
        csv_content = ExpenseReportService.generate_csv(report_data)
        month_name = datetime(year, month, 1).strftime("%B")
        filename = f"expense-report-{year}-{month:02d}-{month_name}.csv"
        return Response(csv_content, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except ValueError as e:
        flash(f"Invalid input: {str(e)}", "error")
        return redirect(url_for("reports.monthly_expense_form"))
    except Exception as e:
        logger.error(f"Error generating CSV report: {str(e)}", exc_info=True)
        flash("An error occurred while generating the report. Please try again.", "error")
        return redirect(url_for("reports.monthly_expense_form"))


# Group Summary Report Routes (Admin Only)

@reports_bp.route("/group/<int:group_id>/monthly", methods=["GET"])
@login_required
def group_monthly_report_form(group_id):
    """Display form for group admin to generate monthly summary report."""
    from models import Group
    from services.group_report_service import GroupReportService
    
    user_id = session.get("user_id")
    
    # Check if user is group admin
    if not GroupReportService.is_group_admin(user_id, group_id):
        flash("Unauthorized: Only group admins can access this report.", "error")
        return redirect(url_for("groups.list_groups"))
    
    group = db.session.get(Group, group_id)
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("groups.list_groups"))
    
    now = datetime.now()
    return render_template(
        "reports/group_monthly.html",
        page_id="group-monthly-report",
        group=group,
        default_year=now.year,
        default_month=now.month,
        current_year=now.year,
    )


@reports_bp.route("/group/<int:group_id>/monthly/pdf", methods=["POST"])
@login_required
def download_group_pdf(group_id):
    """Generate and download PDF group summary report."""
    from services.group_report_service import GroupReportService
    
    user_id = session.get("user_id")
    
    try:
        # Check admin permission
        if not GroupReportService.is_group_admin(user_id, group_id):
            flash("Unauthorized: Only group admins can generate reports.", "error")
            return redirect(url_for("groups.list_groups"))
        
        year = int(request.form.get("year", datetime.now().year))
        month = int(request.form.get("month", datetime.now().month))
        
        # Validate date range
        is_valid, error_msg = GroupReportService.validate_date_range(year, month)
        if not is_valid:
            flash(error_msg, "error")
            return redirect(url_for("reports.group_monthly_report_form", group_id=group_id))
        
        # Generate report
        report_data = GroupReportService.get_group_monthly_summary(group_id, year, month, user_id)
        
        if report_data.get("error"):
            flash(f"Error generating report: {report_data['error']}", "error")
            return redirect(url_for("reports.group_monthly_report_form", group_id=group_id))
        
        # Generate PDF
        pdf_content = GroupReportService.generate_pdf(report_data)
        
        # Create filename
        group_name = report_data["group"]["name"].replace(" ", "-")
        month_name = datetime(year, month, 1).strftime("%B")
        filename = f"group-summary-{group_name}-{year}-{month:02d}-{month_name}.pdf"
        
        return Response(
            pdf_content,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    
    except ValueError as e:
        flash(f"Invalid input: {str(e)}", "error")
        return redirect(url_for("reports.group_monthly_report_form", group_id=group_id))
    except Exception as e:
        logger.error(f"Error generating group PDF report: {str(e)}", exc_info=True)
        flash("An error occurred while generating the report. Please try again.", "error")
        return redirect(url_for("reports.group_monthly_report_form", group_id=group_id))


@reports_bp.route("/group/<int:group_id>/monthly/csv", methods=["POST"])
@login_required
def download_group_csv(group_id):
    """Generate and download CSV group summary report."""
    from services.group_report_service import GroupReportService
    
    user_id = session.get("user_id")
    
    try:
        # Check admin permission
        if not GroupReportService.is_group_admin(user_id, group_id):
            flash("Unauthorized: Only group admins can generate reports.", "error")
            return redirect(url_for("groups.list_groups"))
        
        year = int(request.form.get("year", datetime.now().year))
        month = int(request.form.get("month", datetime.now().month))
        
        # Validate date range
        is_valid, error_msg = GroupReportService.validate_date_range(year, month)
        if not is_valid:
            flash(error_msg, "error")
            return redirect(url_for("reports.group_monthly_report_form", group_id=group_id))
        
        # Generate report
        report_data = GroupReportService.get_group_monthly_summary(group_id, year, month, user_id)
        
        if report_data.get("error"):
            flash(f"Error generating report: {report_data['error']}", "error")
            return redirect(url_for("reports.group_monthly_report_form", group_id=group_id))
        
        # Generate CSV
        csv_content = GroupReportService.generate_csv(report_data)
        
        # Create filename
        group_name = report_data["group"]["name"].replace(" ", "-")
        month_name = datetime(year, month, 1).strftime("%B")
        filename = f"group-summary-{group_name}-{year}-{month:02d}-{month_name}.csv"
        
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    
    except ValueError as e:
        flash(f"Invalid input: {str(e)}", "error")
        return redirect(url_for("reports.group_monthly_report_form", group_id=group_id))
    except Exception as e:
        logger.error(f"Error generating group CSV report: {str(e)}", exc_info=True)
        flash("An error occurred while generating the report. Please try again.", "error")
        return redirect(url_for("reports.group_monthly_report_form", group_id=group_id))
