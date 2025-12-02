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



def test_is_group_admin_invalid_group(app):
    """Test admin check with non-existent group."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.commit()
        
        # Check with non-existent group ID
        is_admin = GroupReportService.is_group_admin(creator.id, 99999)
        assert is_admin is False


def test_get_group_monthly_summary_invalid_group(app):
    """Test getting summary for non-existent group."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.commit()
        
        summary = GroupReportService.get_group_monthly_summary(99999, 2024, 6, creator.id)
        
        assert 'error' in summary
        assert 'not found' in summary['error'].lower()


def test_get_group_monthly_summary_unauthorized_user(app):
    """Test that unauthorized user gets error."""
    with app.app_context():
        creator = User(email='creator@test.com')
        unauthorized = User(email='unauthorized@test.com')
        db.session.add_all([creator, unauthorized])
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        # Try to access as unauthorized user
        summary = GroupReportService.get_group_monthly_summary(
            group.id, 2024, 6, unauthorized.id
        )
        
        assert 'error' in summary
        assert 'Unauthorized' in summary['error']


def test_get_group_monthly_summary_with_settlements(app):
    """Test summary includes settlements."""
    with app.app_context():
        from models import Settlement
        
        creator = User(email='creator@test.com')
        member = User(email='member@test.com')
        db.session.add_all([creator, member])
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(member)
        db.session.add(group)
        db.session.flush()
        
        now = datetime.now()
        
        # Add expense
        expense = Expense(
            description='Test Expense',
            amount=100.00,
            group_id=group.id,
            payer=creator.email,
            expense_date=now.date(),
            category='Food'
        )
        db.session.add(expense)
        
        # Add settlement
        settlement = Settlement(
            amount=50.00,
            payer_id=member.id,
            recipient_id=creator.id,
            note='Test settlement'
        )
        db.session.add(settlement)
        db.session.commit()
        
        summary = GroupReportService.get_group_monthly_summary(
            group.id, now.year, now.month, creator.id
        )
        
        assert 'settlements' in summary
        assert 'summary' in summary
        assert summary['summary']['total_settlements'] >= 0


def test_validate_date_range_invalid_month_zero(app):
    """Test validation with month 0."""
    with app.app_context():
        is_valid, msg = GroupReportService.validate_date_range(2024, 0)
        assert is_valid is False
        assert 'Month must be between' in msg


def test_validate_date_range_invalid_year_low(app):
    """Test validation with year too low."""
    with app.app_context():
        is_valid, msg = GroupReportService.validate_date_range(1999, 6)
        assert is_valid is False
        assert 'Year must be between' in msg


def test_generate_pdf_with_multiple_expenses(app):
    """Test PDF generation with multiple expenses and categories."""
    with app.app_context():
        creator = User(email='creator@test.com')
        member = User(email='member@test.com')
        db.session.add_all([creator, member])
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(member)
        db.session.add(group)
        db.session.flush()
        
        now = datetime.now()
        
        # Add multiple expenses with different categories
        expenses = [
            Expense(
                description='Groceries',
                amount=150.00,
                group_id=group.id,
                payer=creator.email,
                expense_date=now.date(),
                category='Food'
            ),
            Expense(
                description='Gas',
                amount=50.00,
                group_id=group.id,
                payer=member.email,
                expense_date=now.date(),
                category='Transport'
            ),
            Expense(
                description='Movie tickets',
                amount=30.00,
                group_id=group.id,
                payer=creator.email,
                expense_date=now.date(),
                category='Entertainment'
            )
        ]
        db.session.add_all(expenses)
        db.session.commit()
        
        report_data = GroupReportService.get_group_monthly_summary(
            group.id, now.year, now.month, creator.id
        )
        pdf_content = GroupReportService.generate_pdf(report_data)
        
        assert pdf_content is not None
        assert len(pdf_content) > 0
        assert pdf_content[:4] == b'%PDF'


def test_generate_csv_with_multiple_expenses(app):
    """Test CSV generation with multiple expenses."""
    with app.app_context():
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.flush()
        
        now = datetime.now()
        
        expenses = [
            Expense(
                description='Expense 1',
                amount=100.00,
                group_id=group.id,
                payer=creator.email,
                expense_date=now.date(),
                category='Food'
            ),
            Expense(
                description='Expense 2',
                amount=200.00,
                group_id=group.id,
                payer=creator.email,
                expense_date=now.date(),
                category='Transport'
            )
        ]
        db.session.add_all(expenses)
        db.session.commit()
        
        report_data = GroupReportService.get_group_monthly_summary(
            group.id, now.year, now.month, creator.id
        )
        csv_content = GroupReportService.generate_csv(report_data)
        
        csv_text = csv_content.decode('utf-8')
        assert 'Expense 1' in csv_text
        assert 'Expense 2' in csv_text
        assert '100.00' in csv_text
        assert '200.00' in csv_text



def test_generate_csv_with_settlements(app):
    """Test CSV generation includes settlement details."""
    with app.app_context():
        from models import Settlement
        
        creator = User(email='creator@test.com')
        member = User(email='member@test.com')
        db.session.add_all([creator, member])
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(member)
        db.session.add(group)
        db.session.flush()
        
        now = datetime.now()
        
        # Add expense
        expense = Expense(
            description='Test Expense',
            amount=100.00,
            group_id=group.id,
            payer=creator.email,
            expense_date=now.date(),
            category='Food'
        )
        db.session.add(expense)
        
        # Add settlement
        settlement = Settlement(
            amount=50.00,
            payer_id=member.id,
            recipient_id=creator.id,
            note='Payment for dinner'
        )
        db.session.add(settlement)
        db.session.commit()
        
        report_data = GroupReportService.get_group_monthly_summary(
            group.id, now.year, now.month, creator.id
        )
        csv_content = GroupReportService.generate_csv(report_data)
        
        csv_text = csv_content.decode('utf-8')
        assert 'Settlement Details' in csv_text
        assert 'Settlements by Payer' in csv_text
        assert '50.00' in csv_text
