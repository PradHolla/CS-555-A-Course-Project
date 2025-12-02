"""Tests for group report service."""
from datetime import datetime, timedelta, date
from extensions import db
from models import User, Group, Expense
from services.group_report_service import GroupReportService


def test_is_group_admin_creator(app):
    """Test that group creator is recognized as admin."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        is_admin = GroupReportService.is_group_admin(creator.id, group.id)
        assert is_admin is True


def test_is_group_admin_non_creator(app):
    """Test that non-creator is not recognized as admin."""
    with app.app_context():
        creator = User(email='creator@test.com')
        regular = User(email='regular@test.com')
        db.session.add_all([creator, regular])
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(regular)
        db.session.add(group)
        db.session.commit()
        
        is_admin = GroupReportService.is_group_admin(regular.id, group.id)
        assert is_admin is False


def test_get_group_monthly_summary(app):
    """Test getting group monthly summary."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.flush()
        
        # Add expenses
        now = datetime.now()
        expense = Expense(
            description='Test Expense',
            amount=100.00,
            group_id=group.id,
            payer=creator.email,
            expense_date=now.date(),
            category='Food'
        )
        db.session.add(expense)
        db.session.commit()
        
        summary = GroupReportService.get_group_monthly_summary(
            group.id, now.year, now.month, creator.id
        )
        
        assert summary is not None
        assert 'group' in summary
        assert summary['group']['name'] == 'Test Group'
        assert 'expenses' in summary
        assert len(summary['expenses']) > 0


def test_get_group_monthly_summary_no_expenses(app):
    """Test getting group summary with no expenses."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        # Use a future month with no expenses
        summary = GroupReportService.get_group_monthly_summary(
            group.id, 2099, 12, creator.id
        )
        
        assert summary is not None
        assert 'expenses' in summary
        assert len(summary['expenses']) == 0


def test_generate_pdf(app):
    """Test PDF report generation."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.flush()
        
        now = datetime.now()
        expense = Expense(
            description='Test Expense',
            amount=100.00,
            group_id=group.id,
            payer=creator.email,
            expense_date=now.date(),
            category='Food'
        )
        db.session.add(expense)
        db.session.commit()
        
        # Get report data first
        report_data = GroupReportService.get_group_monthly_summary(
            group.id, now.year, now.month, creator.id
        )
        
        # Generate PDF
        pdf_content = GroupReportService.generate_pdf(report_data)
        
        assert pdf_content is not None
        assert isinstance(pdf_content, bytes)
        assert len(pdf_content) > 0
        assert pdf_content[:4] == b'%PDF'


def test_generate_csv(app):
    """Test CSV report generation."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.flush()
        
        now = datetime.now()
        expense = Expense(
            description='Test Expense',
            amount=100.00,
            group_id=group.id,
            payer=creator.email,
            expense_date=now.date(),
            category='Food'
        )
        db.session.add(expense)
        db.session.commit()
        
        # Get report data first
        report_data = GroupReportService.get_group_monthly_summary(
            group.id, now.year, now.month, creator.id
        )
        
        # Generate CSV
        csv_content = GroupReportService.generate_csv(report_data)
        
        assert csv_content is not None
        assert isinstance(csv_content, bytes)
        csv_text = csv_content.decode('utf-8')
        assert 'Test Group' in csv_text
        assert 'Test Expense' in csv_text


def test_generate_pdf_empty_month(app):
    """Test PDF generation for month with no expenses."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        report_data = GroupReportService.get_group_monthly_summary(
            group.id, 2099, 12, creator.id
        )
        pdf_content = GroupReportService.generate_pdf(report_data)
        
        assert pdf_content is not None
        assert isinstance(pdf_content, bytes)
        assert pdf_content[:4] == b'%PDF'


def test_generate_csv_empty_month(app):
    """Test CSV generation for month with no expenses."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        report_data = GroupReportService.get_group_monthly_summary(
            group.id, 2099, 12, creator.id
        )
        csv_content = GroupReportService.generate_csv(report_data)
        
        assert csv_content is not None
        csv_text = csv_content.decode('utf-8')
        assert 'Test Group' in csv_text


def test_validate_date_range_valid(app):
    """Test date range validation with valid dates."""
    with app.app_context():
        is_valid, msg = GroupReportService.validate_date_range(2024, 6)
        assert is_valid is True
        assert msg is None


def test_validate_date_range_invalid_month(app):
    """Test date range validation with invalid month."""
    with app.app_context():
        is_valid, msg = GroupReportService.validate_date_range(2024, 13)
        assert is_valid is False
        assert 'Month must be between' in msg


def test_validate_date_range_future_date(app):
    """Test date range validation with future date."""
    with app.app_context():
        is_valid, msg = GroupReportService.validate_date_range(2099, 12)
        assert is_valid is False
        assert 'Year must be between' in msg
