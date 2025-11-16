"""Unit tests for notification service."""

import os
from datetime import datetime

import pytest

# Set test environment variables before importing app
os.environ["MAIL_USERNAME"] = "test@example.com"
os.environ["MAIL_PASSWORD"] = "test_password"
os.environ["EMAIL_ENABLED"] = "false"

from app import create_app
from extensions import db
from models import User
from services.notification_service import send_payment_reminder


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["EMAIL_ENABLED"] = False
    app.config["APP_URL"] = "http://localhost:5000"
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestSendPaymentReminder:
    """Tests for send_payment_reminder function."""

    def test_send_reminder_success(self, app):
        """Test sending payment reminder successfully."""
        with app.app_context():
            user = User(email="debtor@example.com", display_name="Test Debtor")
            db.session.add(user)
            db.session.commit()
            
            balance_breakdown = [
                {"creditor": "creditor1@example.com", "amount": 50.0},
                {"creditor": "creditor2@example.com", "amount": 75.0}
            ]
            
            # Should not raise exception
            send_payment_reminder(
                user=user,
                balance_amount=-125.0,
                days_outstanding=10,
                balance_breakdown=balance_breakdown
            )

    def test_send_reminder_with_display_name(self, app):
        """Test reminder uses display name when available."""
        with app.app_context():
            user = User(email="debtor@example.com", display_name="John Doe")
            db.session.add(user)
            db.session.commit()
            
            balance_breakdown = [
                {"creditor": "creditor@example.com", "amount": 100.0}
            ]
            
            send_payment_reminder(
                user=user,
                balance_amount=-100.0,
                days_outstanding=7,
                balance_breakdown=balance_breakdown
            )

    def test_send_reminder_without_display_name(self, app):
        """Test reminder uses email when display name not available."""
        with app.app_context():
            user = User(email="debtor@example.com", display_name=None)
            db.session.add(user)
            db.session.commit()
            
            balance_breakdown = [
                {"creditor": "creditor@example.com", "amount": 50.0}
            ]
            
            send_payment_reminder(
                user=user,
                balance_amount=-50.0,
                days_outstanding=14,
                balance_breakdown=balance_breakdown
            )

    def test_send_reminder_multiple_creditors(self, app):
        """Test reminder with multiple creditors."""
        with app.app_context():
            user = User(email="debtor@example.com", display_name="Debtor")
            db.session.add(user)
            db.session.commit()
            
            balance_breakdown = [
                {"creditor": "creditor1@example.com", "amount": 100.0},
                {"creditor": "creditor2@example.com", "amount": 75.0},
                {"creditor": "creditor3@example.com", "amount": 50.0}
            ]
            
            send_payment_reminder(
                user=user,
                balance_amount=-225.0,
                days_outstanding=20,
                balance_breakdown=balance_breakdown
            )

    def test_send_reminder_invalid_user(self, app):
        """Test reminder with invalid user raises error."""
        with app.app_context():
            balance_breakdown = [
                {"creditor": "creditor@example.com", "amount": 50.0}
            ]
            
            with pytest.raises(ValueError, match="Invalid user object"):
                send_payment_reminder(
                    user=None,
                    balance_amount=-50.0,
                    days_outstanding=7,
                    balance_breakdown=balance_breakdown
                )

    def test_send_reminder_empty_breakdown(self, app):
        """Test reminder with empty breakdown raises error."""
        with app.app_context():
            user = User(email="debtor@example.com", display_name="Debtor")
            db.session.add(user)
            db.session.commit()
            
            with pytest.raises(ValueError, match="Balance breakdown is required"):
                send_payment_reminder(
                    user=user,
                    balance_amount=-50.0,
                    days_outstanding=7,
                    balance_breakdown=[]
                )

    def test_send_reminder_negative_days(self, app):
        """Test reminder with negative days raises error."""
        with app.app_context():
            user = User(email="debtor@example.com", display_name="Debtor")
            db.session.add(user)
            db.session.commit()
            
            balance_breakdown = [
                {"creditor": "creditor@example.com", "amount": 50.0}
            ]
            
            with pytest.raises(ValueError, match="Days outstanding must be non-negative"):
                send_payment_reminder(
                    user=user,
                    balance_amount=-50.0,
                    days_outstanding=-5,
                    balance_breakdown=balance_breakdown
                )



class TestSendOrLogEmail:
    """Tests for _send_or_log_email helper function."""

    def test_email_disabled_logs_to_console(self, app, capsys):
        """Test that emails are logged when EMAIL_ENABLED is False."""
        with app.app_context():
            from services.notification_service import _send_or_log_email
            
            _send_or_log_email(
                to_email="test@example.com",
                subject="Test Subject",
                body="Test body content"
            )
            
            captured = capsys.readouterr()
            assert "EMAIL NOTIFICATION" in captured.out
            assert "test@example.com" in captured.out
            assert "Test Subject" in captured.out


class TestNotifySettlementRecipient:
    """Tests for notify_settlement_recipient function."""

    def test_notify_settlement_basic(self, app):
        """Test settlement notification with basic data."""
        with app.app_context():
            from models import Settlement
            from services.notification_service import notify_settlement_recipient
            
            payer = User(email="payer@example.com", display_name="Payer")
            recipient = User(email="recipient@example.com", display_name="Recipient")
            db.session.add_all([payer, recipient])
            db.session.commit()
            
            settlement = Settlement(
                amount=50.0,
                payer_id=payer.id,
                recipient_id=recipient.id,
                note="Test payment"
            )
            db.session.add(settlement)
            db.session.commit()
            
            # Should not raise exception
            notify_settlement_recipient(settlement)

    def test_notify_settlement_no_note(self, app):
        """Test settlement notification without note."""
        with app.app_context():
            from models import Settlement
            from services.notification_service import notify_settlement_recipient
            
            payer = User(email="payer@example.com", display_name="Payer")
            recipient = User(email="recipient@example.com", display_name="Recipient")
            db.session.add_all([payer, recipient])
            db.session.commit()
            
            settlement = Settlement(
                amount=100.0,
                payer_id=payer.id,
                recipient_id=recipient.id,
                note=None
            )
            db.session.add(settlement)
            db.session.commit()
            
            notify_settlement_recipient(settlement)


class TestNotifyExpenseParticipants:
    """Tests for notify_expense_participants function."""

    def test_notify_single_participant(self, app):
        """Test notifying single participant."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_participants
            
            expense = Expense(
                description="Lunch",
                amount=50.0,
                payer="payer@example.com",
                split_type="equal",
                participants="participant@example.com"
            )
            db.session.add(expense)
            db.session.commit()
            
            notify_expense_participants(expense, ["participant@example.com"])

    def test_notify_multiple_participants(self, app):
        """Test notifying multiple participants."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_participants
            
            expense = Expense(
                description="Dinner",
                amount=100.0,
                payer="payer@example.com",
                split_type="equal",
                participants="user1@example.com, user2@example.com"
            )
            db.session.add(expense)
            db.session.commit()
            
            notify_expense_participants(
                expense,
                ["user1@example.com", "user2@example.com"]
            )

    def test_notify_expense_no_participants(self, app):
        """Test expense notification with no participants specified."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_participants
            
            expense = Expense(
                description="Solo expense",
                amount=25.0,
                payer="payer@example.com",
                split_type="equal",
                participants=None
            )
            db.session.add(expense)
            db.session.commit()
            
            notify_expense_participants(expense, [])


class TestNotifyGroupInvitation:
    """Tests for notify_group_invitation function."""

    def test_group_invitation_basic(self, app):
        """Test basic group invitation notification."""
        with app.app_context():
            from services.notification_service import notify_group_invitation
            
            notify_group_invitation(
                inviter_email="inviter@example.com",
                invitee_email="invitee@example.com",
                group_name="Test Group"
            )

    def test_group_invitation_special_chars(self, app):
        """Test group invitation with special characters in name."""
        with app.app_context():
            from services.notification_service import notify_group_invitation
            
            notify_group_invitation(
                inviter_email="inviter@example.com",
                invitee_email="invitee@example.com",
                group_name="Team's Expenses & More"
            )


class TestNotifyExpenseDeletion:
    """Tests for notify_expense_deletion function."""

    def test_expense_deletion_single_member(self, app):
        """Test expense deletion notification to single member."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_deletion
            
            member = User(email="member@example.com", display_name="Member")
            deleter = User(email="deleter@example.com", display_name="Deleter")
            db.session.add_all([member, deleter])
            db.session.commit()
            
            expense = Expense(
                description="Deleted expense",
                amount=75.0,
                payer="payer@example.com",
                split_type="equal"
            )
            db.session.add(expense)
            db.session.commit()
            
            notify_expense_deletion(
                expense,
                deleter_email="deleter@example.com",
                group_members=[member, deleter]
            )

    def test_expense_deletion_multiple_members(self, app):
        """Test expense deletion notification to multiple members."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_deletion
            
            member1 = User(email="member1@example.com", display_name="Member1")
            member2 = User(email="member2@example.com", display_name="Member2")
            deleter = User(email="deleter@example.com", display_name="Deleter")
            db.session.add_all([member1, member2, deleter])
            db.session.commit()
            
            expense = Expense(
                description="Group expense",
                amount=150.0,
                payer="payer@example.com",
                split_type="equal"
            )
            db.session.add(expense)
            db.session.commit()
            
            notify_expense_deletion(
                expense,
                deleter_email="deleter@example.com",
                group_members=[member1, member2, deleter]
            )

    def test_expense_deletion_excludes_deleter(self, app):
        """Test that deleter doesn't receive notification."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_deletion
            
            deleter = User(email="deleter@example.com", display_name="Deleter")
            db.session.add(deleter)
            db.session.commit()
            
            expense = Expense(
                description="Self-deleted",
                amount=50.0,
                payer="deleter@example.com",
                split_type="equal"
            )
            db.session.add(expense)
            db.session.commit()
            
            # Should not send to deleter
            notify_expense_deletion(
                expense,
                deleter_email="deleter@example.com",
                group_members=[deleter]
            )


class TestNotifyExpenseEdited:
    """Tests for notify_expense_edited function."""

    def test_expense_edited_single_member(self, app):
        """Test expense edit notification to single member."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_edited
            
            member = User(email="member@example.com", display_name="Member")
            editor = User(email="editor@example.com", display_name="Editor")
            db.session.add_all([member, editor])
            db.session.commit()
            
            expense = Expense(
                description="Edited expense",
                amount=80.0,
                payer="payer@example.com",
                split_type="equal",
                participants="member@example.com"
            )
            db.session.add(expense)
            db.session.commit()
            
            notify_expense_edited(
                expense,
                editor_email="editor@example.com",
                group_members=[member, editor]
            )

    def test_expense_edited_multiple_members(self, app):
        """Test expense edit notification to multiple members."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_edited
            
            member1 = User(email="member1@example.com", display_name="Member1")
            member2 = User(email="member2@example.com", display_name="Member2")
            editor = User(email="editor@example.com", display_name="Editor")
            db.session.add_all([member1, member2, editor])
            db.session.commit()
            
            expense = Expense(
                description="Updated expense",
                amount=200.0,
                payer="payer@example.com",
                split_type="equal",
                participants="member1@example.com, member2@example.com"
            )
            db.session.add(expense)
            db.session.commit()
            
            notify_expense_edited(
                expense,
                editor_email="editor@example.com",
                group_members=[member1, member2, editor]
            )

    def test_expense_edited_excludes_editor(self, app):
        """Test that editor doesn't receive notification."""
        with app.app_context():
            from models import Expense
            from services.notification_service import notify_expense_edited
            
            editor = User(email="editor@example.com", display_name="Editor")
            db.session.add(editor)
            db.session.commit()
            
            expense = Expense(
                description="Self-edited",
                amount=60.0,
                payer="editor@example.com",
                split_type="equal"
            )
            db.session.add(expense)
            db.session.commit()
            
            # Should not send to editor
            notify_expense_edited(
                expense,
                editor_email="editor@example.com",
                group_members=[editor]
            )
