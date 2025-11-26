"""Business logic for expense report generation."""

import csv
import io
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from extensions import db
from models import Expense, User

logger = logging.getLogger(__name__)


class ExpenseReportService:
    """Service for generating expense reports in various formats."""

    @staticmethod
    def get_monthly_expenses(user_id: int, year: int, month: int, group_ids: Optional[List[int]] = None, category: Optional[str] = None) -> Dict:
        """Fetch expenses for a specific month filtered by user's groups."""
        try:
            user = db.session.get(User, user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return {"expenses": [], "summary": {}, "user": None, "filters": {}, "error": "User not found"}
            
            user_groups = user.groups.all()
            user_group_ids = [g.id for g in user_groups]
            
            if not user_group_ids:
                logger.info(f"User {user_id} has no groups")
                return {"expenses": [], "summary": {"total_expenses": 0, "total_amount": 0.0, "by_category": {}, "by_group": {}}, "user": user, "filters": {"year": year, "month": month, "group_ids": group_ids, "category": category}}
            
            query = Expense.query.filter(db.extract("year", Expense.expense_date) == year, db.extract("month", Expense.expense_date) == month, Expense.group_id.in_(user_group_ids))
            
            if group_ids:
                filtered_group_ids = [gid for gid in group_ids if gid in user_group_ids]
                if filtered_group_ids:
                    query = query.filter(Expense.group_id.in_(filtered_group_ids))
                else:
                    logger.warning(f"User {user_id} requested groups {group_ids} but has no access")
                    return {"expenses": [], "summary": {"total_expenses": 0, "total_amount": 0.0, "by_category": {}, "by_group": {}}, "user": user, "filters": {"year": year, "month": month, "group_ids": group_ids, "category": category}}
            
            if category:
                query = query.filter(Expense.category == category)
            
            expenses = query.order_by(Expense.expense_date.desc()).all()
            
            expense_list = []
            for expense in expenses:
                expense_list.append({"id": expense.id, "date": expense.expense_date.strftime("%Y-%m-%d"), "description": expense.description, "amount": expense.amount, "category": expense.category or "Uncategorized", "payer": expense.payer, "group_name": expense.group.name if expense.group else "No Group", "group_id": expense.group_id})
            
            summary = ExpenseReportService._calculate_summary(expense_list)
            return {"expenses": expense_list, "summary": summary, "user": user, "filters": {"year": year, "month": month, "group_ids": group_ids, "category": category}}
        
        except Exception as e:
            logger.error(f"Error fetching monthly expenses: {str(e)}", exc_info=True)
            return {"expenses": [], "summary": {}, "user": None, "filters": {}, "error": str(e)}
    
    @staticmethod
    def _calculate_summary(expenses: List[Dict]) -> Dict:
        """Calculate summary statistics from expense list."""
        total_amount = sum(exp["amount"] for exp in expenses)
        total_expenses = len(expenses)
        by_category = defaultdict(lambda: {"count": 0, "total": 0.0})
        for exp in expenses:
            category = exp["category"]
            by_category[category]["count"] += 1
            by_category[category]["total"] += exp["amount"]
        by_group = defaultdict(lambda: {"count": 0, "total": 0.0})
        for exp in expenses:
            group_name = exp["group_name"]
            by_group[group_name]["count"] += 1
            by_group[group_name]["total"] += exp["amount"]
        return {"total_expenses": total_expenses, "total_amount": round(total_amount, 2), "by_category": dict(by_category), "by_group": dict(by_group)}
    
    @staticmethod
    def generate_csv(report_data: Dict) -> bytes:
        """Generate CSV report from expense data."""
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            filters = report_data.get("filters", {})
            year = filters.get("year", "")
            month = filters.get("month", "")
            writer.writerow(["Monthly Expense Report"])
            writer.writerow([f"Period: {year}-{month:02d}"])
            if filters.get("category"):
                writer.writerow([f"Category Filter: {filters['category']}"])
            if filters.get("group_ids"):
                writer.writerow([f"Group Filter: {', '.join(map(str, filters['group_ids']))}"])
            writer.writerow([])
            summary = report_data.get("summary", {})
            writer.writerow(["Summary"])
            writer.writerow(["Total Expenses", summary.get("total_expenses", 0)])
            writer.writerow(["Total Amount", f"${summary.get('total_amount', 0):.2f}"])
            writer.writerow([])
            if summary.get("by_category"):
                writer.writerow(["Category Breakdown"])
                writer.writerow(["Category", "Count", "Total Amount"])
                for category, data in summary["by_category"].items():
                    writer.writerow([category, data["count"], f"${data['total']:.2f}"])
                writer.writerow([])
            if summary.get("by_group"):
                writer.writerow(["Group Breakdown"])
                writer.writerow(["Group", "Count", "Total Amount"])
                for group, data in summary["by_group"].items():
                    writer.writerow([group, data["count"], f"${data['total']:.2f}"])
                writer.writerow([])
            writer.writerow(["Expense Details"])
            writer.writerow(["Date", "Description", "Amount", "Category", "Payer", "Group"])
            expenses = report_data.get("expenses", [])
            for expense in expenses:
                writer.writerow([expense["date"], expense["description"], f"${expense['amount']:.2f}", expense["category"], expense["payer"], expense["group_name"]])
            csv_content = output.getvalue()
            output.close()
            return csv_content.encode("utf-8")
        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def generate_pdf(report_data: Dict) -> bytes:
        """Generate PDF report from expense data."""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("CustomTitle", parent=styles["Heading1"], fontSize=24, textColor=colors.HexColor("#2c3e50"), spaceAfter=30, alignment=1)
            heading_style = ParagraphStyle("CustomHeading", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#34495e"), spaceAfter=12)
            story.append(Paragraph("Monthly Expense Report", title_style))
            story.append(Spacer(1, 0.2 * inch))
            filters = report_data.get("filters", {})
            year = filters.get("year", "")
            month = filters.get("month", "")
            month_name = datetime(year, month, 1).strftime("%B %Y")
            metadata = [["Report Period:", month_name], ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M")]]
            if filters.get("category"):
                metadata.append(["Category Filter:", filters["category"]])
            if filters.get("group_ids"):
                metadata.append(["Group Filter:", ", ".join(map(str, filters["group_ids"]))])
            metadata_table = Table(metadata, colWidths=[2 * inch, 4 * inch])
            metadata_table.setStyle(TableStyle([("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10), ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(metadata_table)
            story.append(Spacer(1, 0.3 * inch))
            summary = report_data.get("summary", {})
            story.append(Paragraph("Summary", heading_style))
            summary_data = [["Total Expenses:", str(summary.get("total_expenses", 0))], ["Total Amount:", f"${summary.get('total_amount', 0):.2f}"]]
            summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10), ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecf0f1")), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
            story.append(summary_table)
            story.append(Spacer(1, 0.2 * inch))
            if summary.get("by_category"):
                story.append(Paragraph("Category Breakdown", heading_style))
                category_data = [["Category", "Count", "Total Amount"]]
                for category, data in summary["by_category"].items():
                    category_data.append([category, str(data["count"]), f"${data['total']:.2f}"])
                category_table = Table(category_data, colWidths=[2.5 * inch, 1 * inch, 1.5 * inch])
                category_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
                story.append(category_table)
                story.append(Spacer(1, 0.2 * inch))
            expenses = report_data.get("expenses", [])
            if expenses:
                story.append(Paragraph("Expense Details", heading_style))
                expense_data = [["Date", "Description", "Amount", "Category", "Payer", "Group"]]
                for expense in expenses:
                    expense_data.append([expense["date"], expense["description"][:30], f"${expense['amount']:.2f}", expense["category"][:15], expense["payer"][:20], expense["group_name"][:15]])
                expense_table = Table(expense_data, colWidths=[0.8 * inch, 1.8 * inch, 0.8 * inch, 1 * inch, 1.2 * inch, 1 * inch])
                expense_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ecc71")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("ALIGN", (2, 0), (2, -1), "RIGHT"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
                story.append(expense_table)
            else:
                story.append(Paragraph("No expenses found for this period.", styles["Normal"]))
            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()
            return pdf_content
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def validate_date_range(year: int, month: int) -> tuple:
        """Validate year and month parameters."""
        current_year = datetime.now().year
        if year < 2000 or year > current_year + 1:
            return False, f"Year must be between 2000 and {current_year + 1}"
        if month < 1 or month > 12:
            return False, "Month must be between 1 and 12"
        return True, None
    
    @staticmethod
    def get_available_categories(user_id: int) -> List[str]:
        """Get list of categories used in user's expenses."""
        try:
            user = db.session.get(User, user_id)
            if not user:
                return []
            user_group_ids = [g.id for g in user.groups.all()]
            if not user_group_ids:
                return []
            categories = db.session.query(Expense.category).filter(Expense.group_id.in_(user_group_ids), Expense.category.isnot(None)).distinct().all()
            return sorted([cat[0] for cat in categories if cat[0]])
        except Exception as e:
            logger.error(f"Error fetching categories: {str(e)}", exc_info=True)
            return []
