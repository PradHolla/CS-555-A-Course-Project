"""Integration tests for report routes."""
from datetime import date
from extensions import db
from models import Expense, Group, User

def test_monthly_expense_form_requires_login(client):
    response = client.get("/reports/monthly-expense")
    assert response.status_code == 302

def test_monthly_expense_form_displays(client, app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.get("/reports/monthly-expense")
        assert response.status_code == 200
        assert b"Monthly Expense Report" in response.data

def test_download_pdf_success(client, app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=100.00, payer=user.email, group_id=group.id, expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/pdf", data={"year": "2024", "month": "1"})
        assert response.status_code == 200
        assert response.content_type == "application/pdf"

def test_download_csv_success(client, app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=100.00, payer=user.email, group_id=group.id, expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/csv", data={"year": "2024", "month": "1"})
        assert response.status_code == 200
        assert "text/csv" in response.content_type

def test_download_pdf_invalid_date(client, app):
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/pdf", data={"year": "2024", "month": "13"}, follow_redirects=True)
        assert b"Month must be between 1 and 12" in response.data


def test_download_pdf_empty_month(app, client):
    """Test PDF download for month with no expenses."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/pdf", data={"year": "2024", "month": "1"})
        assert response.status_code == 200
        assert response.content_type == "application/pdf"

def test_download_csv_invalid_input(app, client):
    """Test CSV download handles invalid input gracefully."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/csv", data={"year": "invalid", "month": "1"}, follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid input" in response.data or b"error" in response.data.lower()

def test_download_pdf_with_filters(app, client):
    """Test PDF download with group and category filters."""
    with app.app_context():
        user = User(email="user@example.com")
        db.session.add(user)
        db.session.flush()
        group = Group(name="Test", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.flush()
        expense = Expense(description="Test", amount=100.00, payer=user.email, group_id=group.id, category="Food", expense_date=date(2024, 1, 15))
        db.session.add(expense)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email
        response = client.post("/reports/monthly-expense/pdf", data={"year": "2024", "month": "1", "group_ids": [str(group.id)], "category": "Food"})
        assert response.status_code == 200


# Group Report Routes Tests

def test_group_monthly_report_form_requires_login(client):
    """Test that group report form requires authentication."""
    response = client.get('/reports/group/1/monthly')
    assert response.status_code == 302
    assert '/auth/login' in response.location


def test_group_monthly_report_form_requires_admin(client, app):
    """Test that only group admins can access the form."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        
        # Create users
        creator = User(email='creator@test.com')
        member = User(email='member@test.com')
        db.session.add_all([creator, member])
        db.session.flush()
        
        # Create group
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(member)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        member_id = member.id
    
    # Login as non-admin member
    with client.session_transaction() as sess:
        sess['user_id'] = member_id
    
    response = client.get(f'/reports/group/{group_id}/monthly')
    assert response.status_code == 302


def test_group_monthly_report_form_displays(client, app):
    """Test that group report form displays for admin."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.get(f'/reports/group/{group_id}/monthly')
    assert response.status_code == 200
    assert b'Group Monthly Summary Report' in response.data


def test_download_group_pdf_success(client, app):
    """Test successful group PDF download."""
    with app.app_context():
        from extensions import db
        from models import User, Group, Expense
        from datetime import datetime
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.flush()
        
        # Add expense
        expense = Expense(
            description='Test Expense',
            amount=100.00,
            group_id=group.id,
            payer=creator.email,
            expense_date=datetime.now().date(),
            category='Food'
        )
        db.session.add(expense)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/pdf', data={
        'year': datetime.now().year,
        'month': datetime.now().month
    })
    
    assert response.status_code == 200
    assert response.content_type == 'application/pdf'


def test_download_group_csv_success(client, app):
    """Test successful group CSV download."""
    with app.app_context():
        from extensions import db
        from models import User, Group, Expense
        from datetime import datetime
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.flush()
        
        expense = Expense(
            description='Test Expense',
            amount=100.00,
            group_id=group.id,
            payer=creator.email,
            expense_date=datetime.now().date(),
            category='Food'
        )
        db.session.add(expense)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/csv', data={
        'year': datetime.now().year,
        'month': datetime.now().month
    })
    
    assert response.status_code == 200
    assert 'text/csv' in response.content_type


def test_download_group_pdf_unauthorized(client, app):
    """Test that non-admin cannot download group PDF."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        from datetime import datetime
        
        creator = User(email='creator@test.com')
        member = User(email='member@test.com')
        db.session.add_all([creator, member])
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(member)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        member_id = member.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = member_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/pdf', data={
        'year': datetime.now().year,
        'month': datetime.now().month
    })
    
    assert response.status_code == 302



def test_download_group_csv_unauthorized(client, app):
    """Test that non-admin cannot download group CSV."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        from datetime import datetime
        
        creator = User(email='creator@test.com')
        member = User(email='member@test.com')
        db.session.add_all([creator, member])
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(member)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        member_id = member.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = member_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/csv', data={
        'year': datetime.now().year,
        'month': datetime.now().month
    })
    
    assert response.status_code == 302


def test_download_group_pdf_invalid_date(client, app):
    """Test group PDF download with invalid date."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/pdf', data={
        'year': 2024,
        'month': 13  # Invalid month
    }, follow_redirects=False)
    
    assert response.status_code == 302


def test_download_group_csv_invalid_date(client, app):
    """Test group CSV download with invalid date."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/csv', data={
        'year': 2099,
        'month': 12  # Future date
    }, follow_redirects=False)
    
    assert response.status_code == 302


def test_group_monthly_report_form_invalid_group(client, app):
    """Test accessing report form for non-existent group."""
    with app.app_context():
        from extensions import db
        from models import User
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.commit()
        
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.get('/reports/group/99999/monthly')
    assert response.status_code == 302


def test_download_group_pdf_with_settlements(client, app):
    """Test PDF download with settlements included."""
    with app.app_context():
        from extensions import db
        from models import User, Group, Expense, Settlement
        from datetime import datetime
        
        creator = User(email='creator@test.com')
        member = User(email='member@test.com')
        db.session.add_all([creator, member])
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(member)
        db.session.add(group)
        db.session.flush()
        
        # Add expense
        expense = Expense(
            description='Test Expense',
            amount=100.00,
            group_id=group.id,
            payer=creator.email,
            expense_date=datetime.now().date(),
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
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/pdf', data={
        'year': datetime.now().year,
        'month': datetime.now().month
    })
    
    assert response.status_code == 200
    assert response.content_type == 'application/pdf'


def test_download_group_pdf_empty_month(client, app):
    """Test PDF download for month with no data."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    # Request report for a past month with no data
    response = client.post(f'/reports/group/{group_id}/monthly/pdf', data={
        'year': 2020,
        'month': 1
    })
    
    assert response.status_code == 200
    assert response.content_type == 'application/pdf'


def test_download_group_csv_empty_month(client, app):
    """Test CSV download for month with no data."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/csv', data={
        'year': 2020,
        'month': 1
    })
    
    assert response.status_code == 200
    assert 'text/csv' in response.content_type






def test_download_group_pdf_with_error(client, app):
    """Test group PDF download with service error."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    # Try with invalid data that might cause an error
    response = client.post(f'/reports/group/{group_id}/monthly/pdf', data={
        'year': 'invalid',
        'month': 'invalid'
    }, follow_redirects=False)
    
    assert response.status_code == 302


def test_download_group_csv_with_error(client, app):
    """Test group CSV download with service error."""
    with app.app_context():
        from extensions import db
        from models import User, Group
        
        creator = User(email='creator@test.com')
        db.session.add(creator)
        db.session.flush()
        
        group = Group(name='Test Group', created_by_id=creator.id)
        group.members.append(creator)
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        creator_id = creator.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = creator_id
    
    response = client.post(f'/reports/group/{group_id}/monthly/csv', data={
        'year': 'invalid',
        'month': 'invalid'
    }, follow_redirects=False)
    
    assert response.status_code == 302


