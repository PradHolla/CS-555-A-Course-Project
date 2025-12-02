"""Business logic for group summary report generation."""

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
from models import Expense, Group, Settlement, User

logger = logging.getLogger(__name__)


class GroupReportService:
    """Service for generating group summary reports for admins."""

    @staticmethod
    def is_group_admin(user_id: int, group_id: int) -> bool:
        """Check if user is the admin (creator) of the group."""
        try:
            group = db.session.get(Group, group_id)
            if not group:
                return False
            return group.created_by_id == user_id
        except Exception as e:
            logger.error(f"Error checking admin status: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def get_group_monthly_summary(
        group_id: int, year: int, month: int, user_id: Optional[int] = None
    ) -> Dict:
        """
        Generate monthly summary report for a group.

        Args:
            group_id: ID of the group
            year: Year for the report
            month: Month for the report (1-12)
            user_id: Optional user ID for permission check

        Returns:
            Dictionary containing expenses, settlements, summary, and metadata
        """
        try:
            group = db.session.get(Group, group_id)
            if not group:
                logger.error(f"Group {group_id} not found")
                return {"error": "Group not found", "expenses": [], "settlements": [], "summary": {}}

            # Permission check if user_id provided
            if user_id and not GroupReportService.is_group_admin(user_id, group_id):
                logger.warning(f"User {user_id} attempted to access group {group_id} report without admin rights")
                return {"error": "Unauthorized: Only group admins can generate reports", "expenses": [], "settlements": [], "summary": {}}

            # Fetch expenses for the month
            expenses = Expense.query.filter(
                Expense.group_id == group_id,
                db.extract("year", Expense.expense_date) == year,
                db.extract("month", Expense.expense_date) == month,
            ).order_by(Expense.expense_date.desc()).all()

            # Fetch settlements for the month
            # Note: Settlements don't have group_id, so we filter by payer/recipient being group members
            member_ids = [m.id for m in group.members]
            settlements = Settlement.query.filter(
                Settlement.payer_id.in_(member_ids),
                Settlement.recipient_id.in_(member_ids),
                db.extract("year", Settlement.created_at) == year,
                db.extract("month", Settlement.created_at) == month,
            ).all()

            # Format data
            expense_list = []
            for expense in expenses:
                expense_list.append({
                    "id": expense.id,
                    "date": expense.expense_date.strftime("%Y-%m-%d"),
                    "description": expense.description,
                    "amount": expense.amount,
                    "category": expense.category or "Uncategorized",
                    "payer": expense.payer,
                })

            settlement_list = []
            for settlement in settlements:
                settlement_list.append({
                    "id": settlement.id,
                    "date": settlement.created_at.strftime("%Y-%m-%d"),
                    "amount": settlement.amount,
                    "payer": settlement.payer.display_name or settlement.payer.email,
                    "recipient": settlement.recipient.display_name or settlement.recipient.email,
                    "note": settlement.note or "",
                })

            # Calculate summary
            summary = GroupReportService._calculate_group_summary(expense_list, settlement_list, group)

            return {
                "group": {"id": group.id, "name": group.name},
                "expenses": expense_list,
                "settlements": settlement_list,
                "summary": summary,
                "filters": {"year": year, "month": month},
            }

        except Exception as e:
            logger.error(f"Error generating group summary: {str(e)}", exc_info=True)
            return {"error": str(e), "expenses": [], "settlements": [], "summary": {}}

    @staticmethod
    def _calculate_group_summary(expenses: List[Dict], settlements: List[Dict], group: Group) -> Dict:
        """Calculate summary statistics for group report."""
        total_expenses = len(expenses)
        total_expense_amount = sum(exp["amount"] for exp in expenses)

        total_settlements = len(settlements)
        total_settlement_amount = sum(set["amount"] for set in settlements)

        # Group by category
        by_category = defaultdict(lambda: {"count": 0, "total": 0.0})
        for exp in expenses:
            category = exp["category"]
            by_category[category]["count"] += 1
            by_category[category]["total"] += exp["amount"]

        # Group by payer (who paid expenses)
        by_payer = defaultdict(lambda: {"count": 0, "total": 0.0})
        for exp in expenses:
            payer = exp["payer"]
            by_payer[payer]["count"] += 1
            by_payer[payer]["total"] += exp["amount"]

        # Group settlements by payer (who made settlements)
        settlements_by_payer = defaultdict(lambda: {"count": 0, "total": 0.0})
        for settlement in settlements:
            payer = settlement["payer"]
            settlements_by_payer[payer]["count"] += 1
            settlements_by_payer[payer]["total"] += settlement["amount"]

        return {
            "total_expenses": total_expenses,
            "total_expense_amount": round(total_expense_amount, 2),
            "total_settlements": total_settlements,
            "total_settlement_amount": round(total_settlement_amount, 2),
            "by_category": dict(by_category),
            "by_payer": dict(by_payer),
            "settlements_by_payer": dict(settlements_by_payer),
            "member_count": len(group.members),
        }

    @staticmethod
    def generate_csv(report_data: Dict) -> bytes:
        """Generate CSV report for group summary."""
        try:
            output = io.StringIO()
            writer = csv.writer(output)

            group = report_data.get("group", {})
            filters = report_data.get("filters", {})
            summary = report_data.get("summary", {})

            # Header
            writer.writerow(["Group Monthly Summary Report"])
            writer.writerow([f"Group: {group.get('name', 'Unknown')}"])
            writer.writerow([f"Period: {filters.get('year', '')}-{filters.get('month', ''):02d}"])
            writer.writerow([])

            # Summary
            writer.writerow(["Summary"])
            writer.writerow(["Total Expenses", summary.get("total_expenses", 0)])
            writer.writerow(["Total Expense Amount", f"${summary.get('total_expense_amount', 0):.2f}"])
            writer.writerow(["Total Settlements", summary.get("total_settlements", 0)])
            writer.writerow(["Total Settlement Amount", f"${summary.get('total_settlement_amount', 0):.2f}"])
            writer.writerow(["Group Members", summary.get("member_count", 0)])
            writer.writerow([])

            # Category breakdown
            if summary.get("by_category"):
                writer.writerow(["Expenses by Category"])
                writer.writerow(["Category", "Count", "Total Amount"])
                for category, data in summary["by_category"].items():
                    writer.writerow([category, data["count"], f"${data['total']:.2f}"])
                writer.writerow([])

            # Payer breakdown
            if summary.get("by_payer"):
                writer.writerow(["Expenses by Payer"])
                writer.writerow(["Payer", "Count", "Total Paid"])
                for payer, data in summary["by_payer"].items():
                    writer.writerow([payer, data["count"], f"${data['total']:.2f}"])
                writer.writerow([])

            # Settlements breakdown
            if summary.get("settlements_by_payer"):
                writer.writerow(["Settlements by Payer"])
                writer.writerow(["Payer", "Count", "Total Settled"])
                for payer, data in summary["settlements_by_payer"].items():
                    writer.writerow([payer, data["count"], f"${data['total']:.2f}"])
                writer.writerow([])

            # Expense details
            writer.writerow(["Expense Details"])
            writer.writerow(["Date", "Description", "Amount", "Category", "Payer"])
            for expense in report_data.get("expenses", []):
                writer.writerow([
                    expense["date"],
                    expense["description"],
                    f"${expense['amount']:.2f}",
                    expense["category"],
                    expense["payer"],
                ])
            writer.writerow([])

            # Settlement details
            if report_data.get("settlements"):
                writer.writerow(["Settlement Details"])
                writer.writerow(["Date", "Amount", "From", "To", "Note"])
                for settlement in report_data.get("settlements", []):
                    writer.writerow([
                        settlement["date"],
                        f"${settlement['amount']:.2f}",
                        settlement["payer"],
                        settlement["recipient"],
                        settlement["note"],
                    ])

            csv_content = output.getvalue()
            output.close()
            return csv_content.encode("utf-8")

        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def generate_pdf(report_data: Dict) -> bytes:
        """Generate PDF report for group summary."""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#2c3e50"),
                spaceAfter=30,
                alignment=1,
            )
            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#34495e"),
                spaceAfter=12,
            )

            group = report_data.get("group", {})
            filters = report_data.get("filters", {})
            summary = report_data.get("summary", {})

            # Title
            story.append(Paragraph("Group Monthly Summary Report", title_style))
            story.append(Spacer(1, 0.2 * inch))

            # Metadata
            year = filters.get("year", "")
            month = filters.get("month", "")
            month_name = datetime(year, month, 1).strftime("%B %Y")

            metadata = [
                ["Group:", group.get("name", "Unknown")],
                ["Report Period:", month_name],
                ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M")],
                ["Members:", str(summary.get("member_count", 0))],
            ]

            metadata_table = Table(metadata, colWidths=[2 * inch, 4 * inch])
            metadata_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(metadata_table)
            story.append(Spacer(1, 0.3 * inch))

            # Summary
            story.append(Paragraph("Summary", heading_style))
            summary_data = [
                ["Total Expenses:", str(summary.get("total_expenses", 0))],
                ["Total Expense Amount:", f"${summary.get('total_expense_amount', 0):.2f}"],
                ["Total Settlements:", str(summary.get("total_settlements", 0))],
                ["Total Settlement Amount:", f"${summary.get('total_settlement_amount', 0):.2f}"],
            ]

            summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
            summary_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecf0f1")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.2 * inch))

            # Category breakdown
            if summary.get("by_category"):
                story.append(Paragraph("Expenses by Category", heading_style))
                category_data = [["Category", "Count", "Total Amount"]]
                for category, data in summary["by_category"].items():
                    category_data.append([category, str(data["count"]), f"${data['total']:.2f}"])

                category_table = Table(category_data, colWidths=[2.5 * inch, 1 * inch, 1.5 * inch])
                category_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ]))
                story.append(category_table)
                story.append(Spacer(1, 0.2 * inch))

            # Payer breakdown
            if summary.get("by_payer"):
                story.append(Paragraph("Expenses by Member", heading_style))
                payer_data = [["Member", "Expenses", "Total Paid"]]
                for payer, data in summary["by_payer"].items():
                    payer_data.append([payer[:25], str(data["count"]), f"${data['total']:.2f}"])

                payer_table = Table(payer_data, colWidths=[2.5 * inch, 1 * inch, 1.5 * inch])
                payer_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e74c3c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ]))
                story.append(payer_table)
                story.append(Spacer(1, 0.2 * inch))

            # Expense details
            expenses = report_data.get("expenses", [])
            if expenses:
                story.append(Paragraph("Expense Details", heading_style))
                expense_data = [["Date", "Description", "Amount", "Category", "Payer"]]
                for expense in expenses[:20]:  # Limit to first 20 for PDF
                    expense_data.append([
                        expense["date"],
                        expense["description"][:25],
                        f"${expense['amount']:.2f}",
                        expense["category"][:15],
                        expense["payer"][:20],
                    ])

                expense_table = Table(expense_data, colWidths=[0.9 * inch, 2 * inch, 0.9 * inch, 1.1 * inch, 1.6 * inch])
                expense_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ecc71")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ]))
                story.append(expense_table)

                if len(expenses) > 20:
                    story.append(Spacer(1, 0.1 * inch))
                    story.append(Paragraph(f"<i>Showing first 20 of {len(expenses)} expenses. Download CSV for complete list.</i>", styles["Normal"]))
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
