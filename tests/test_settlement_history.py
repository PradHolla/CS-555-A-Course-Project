"""Tests for settlement history feature."""

import pytest
from datetime import datetime, timezone

from extensions import db
from models import Settlement, User
from services.settlement_service import SettlementService


class TestSettlementHistoryService:
    """Tests for SettlementService.get_user_settlements method."""

    def test_get_user_settlements_returns_empty_list_for_user_with_no_settlements(self, app):
        """Test that get_user_settlements returns empty list for user with no settlements."""
        with app.app_context():
            user = User(email="lonely@example.com", display_name="Lonely User")
            db.session.add(user)
            db.session.commit()

            settlements = SettlementService.get_user_settlements(user.id)
            assert settlements == []

    def test_get_user_settlements_returns_settlements_where_user_is_payer(self, app):
        """Test that settlements where user is payer are included."""
        with app.app_context():
            payer = User(email="payer@example.com", display_name="Payer")
            recipient = User(email="recipient@example.com", display_name="Recipient")
            db.session.add_all([payer, recipient])
            db.session.commit()

            settlement = Settlement(
                amount=50.00,
                payer_id=payer.id,
                recipient_id=recipient.id,
                note="Test payment"
            )
            db.session.add(settlement)
            db.session.commit()

            settlements = SettlementService.get_user_settlements(payer.id)
            assert len(settlements) == 1
            assert settlements[0].amount == 50.00
            assert settlements[0].payer_id == payer.id

    def test_get_user_settlements_returns_settlements_where_user_is_recipient(self, app):
        """Test that settlements where user is recipient are included."""
        with app.app_context():
            payer = User(email="payer2@example.com", display_name="Payer")
            recipient = User(email="recipient2@example.com", display_name="Recipient")
            db.session.add_all([payer, recipient])
            db.session.commit()

            settlement = Settlement(
                amount=75.00,
                payer_id=payer.id,
                recipient_id=recipient.id,
                note="Payment received"
            )
            db.session.add(settlement)
            db.session.commit()

            settlements = SettlementService.get_user_settlements(recipient.id)
            assert len(settlements) == 1
            assert settlements[0].amount == 75.00
            assert settlements[0].recipient_id == recipient.id

    def test_get_user_settlements_returns_both_paid_and_received(self, app):
        """Test that user sees both payments they made and received."""
        with app.app_context():
            user = User(email="user@example.com", display_name="User")
            other1 = User(email="other1@example.com", display_name="Other 1")
            other2 = User(email="other2@example.com", display_name="Other 2")
            db.session.add_all([user, other1, other2])
            db.session.commit()

            # User pays other1
            settlement1 = Settlement(
                amount=30.00,
                payer_id=user.id,
                recipient_id=other1.id,
            )
            # other2 pays user
            settlement2 = Settlement(
                amount=40.00,
                payer_id=other2.id,
                recipient_id=user.id,
            )
            db.session.add_all([settlement1, settlement2])
            db.session.commit()

            settlements = SettlementService.get_user_settlements(user.id)
            assert len(settlements) == 2

    def test_get_user_settlements_ordered_by_date_descending(self, app):
        """Test that settlements are returned in chronological order (newest first)."""
        with app.app_context():
            user = User(email="order_user@example.com", display_name="User")
            other = User(email="order_other@example.com", display_name="Other")
            db.session.add_all([user, other])
            db.session.commit()

            # Create multiple settlements
            settlement1 = Settlement(
                amount=10.00,
                payer_id=user.id,
                recipient_id=other.id,
            )
            db.session.add(settlement1)
            db.session.commit()

            settlement2 = Settlement(
                amount=20.00,
                payer_id=user.id,
                recipient_id=other.id,
            )
            db.session.add(settlement2)
            db.session.commit()

            settlement3 = Settlement(
                amount=30.00,
                payer_id=user.id,
                recipient_id=other.id,
            )
            db.session.add(settlement3)
            db.session.commit()

            settlements = SettlementService.get_user_settlements(user.id)
            
            # Should be ordered newest first
            assert len(settlements) == 3
            assert settlements[0].amount == 30.00  # Most recent
            assert settlements[1].amount == 20.00
            assert settlements[2].amount == 10.00  # Oldest

    def test_get_user_settlements_excludes_other_users_settlements(self, app):
        """Test that settlements between other users are not included."""
        with app.app_context():
            user = User(email="me@example.com", display_name="Me")
            other1 = User(email="other1_exc@example.com", display_name="Other 1")
            other2 = User(email="other2_exc@example.com", display_name="Other 2")
            db.session.add_all([user, other1, other2])
            db.session.commit()

            # Settlement between other1 and other2 (not involving user)
            settlement = Settlement(
                amount=100.00,
                payer_id=other1.id,
                recipient_id=other2.id,
            )
            db.session.add(settlement)
            db.session.commit()

            settlements = SettlementService.get_user_settlements(user.id)
            assert len(settlements) == 0


class TestSettlementHistoryRoute:
    """Tests for settlement history route."""

    def test_history_route_requires_login(self, client, app):
        """Test that history route requires authentication."""
        response = client.get("/settlements/history", follow_redirects=False)
        assert response.status_code == 302  # Redirect to login

    def test_history_route_returns_ok_for_logged_in_user(self, client, app):
        """Test that history route returns 200 for authenticated user."""
        user = User(email="auth_user@example.com", display_name="Auth User")
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email

        response = client.get("/settlements/history")
        assert response.status_code == 200

    def test_history_route_shows_no_settlements_message(self, client, app):
        """Test that history shows appropriate message when no settlements."""
        user = User(email="empty_user@example.com", display_name="Empty User")
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email

        response = client.get("/settlements/history")
        assert response.status_code == 200
        assert b"No Settlements Yet" in response.data

    def test_history_route_displays_settlements(self, client, app):
        """Test that history page displays user's settlements."""
        user = User(email="history_user@example.com", display_name="History User")
        other = User(email="history_other@example.com", display_name="Other Person")
        db.session.add_all([user, other])
        db.session.commit()

        settlement = Settlement(
            amount=99.99,
            payer_id=user.id,
            recipient_id=other.id,
            note="Test settlement"
        )
        db.session.add(settlement)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email

        response = client.get("/settlements/history")
        assert response.status_code == 200
        assert b"99.99" in response.data
        assert b"Other Person" in response.data

    def test_history_route_shows_payment_direction(self, client, app):
        """Test that history shows whether user paid or received."""
        user = User(email="direction_user@example.com", display_name="Direction User")
        other = User(email="direction_other@example.com", display_name="Direction Other")
        db.session.add_all([user, other])
        db.session.commit()

        # User pays
        settlement1 = Settlement(
            amount=50.00,
            payer_id=user.id,
            recipient_id=other.id,
        )
        # User receives
        settlement2 = Settlement(
            amount=60.00,
            payer_id=other.id,
            recipient_id=user.id,
        )
        db.session.add_all([settlement1, settlement2])
        db.session.commit()

        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email

        response = client.get("/settlements/history")
        assert response.status_code == 200
        assert b"You paid" in response.data
        assert b"You received from" in response.data

    def test_history_route_shows_settlement_notes(self, client, app):
        """Test that settlement notes are displayed."""
        user = User(email="notes_user@example.com", display_name="Notes User")
        other = User(email="notes_other@example.com", display_name="Notes Other")
        db.session.add_all([user, other])
        db.session.commit()

        settlement = Settlement(
            amount=25.00,
            payer_id=user.id,
            recipient_id=other.id,
            note="Paid for lunch last week"
        )
        db.session.add(settlement)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email

        response = client.get("/settlements/history")
        assert response.status_code == 200
        assert b"Paid for lunch last week" in response.data

    def test_history_route_shows_summary_stats(self, client, app):
        """Test that history shows total paid and received stats."""
        user = User(email="stats_user@example.com", display_name="Stats User")
        other = User(email="stats_other@example.com", display_name="Stats Other")
        db.session.add_all([user, other])
        db.session.commit()

        # User pays 100
        settlement1 = Settlement(
            amount=100.00,
            payer_id=user.id,
            recipient_id=other.id,
        )
        # User receives 50
        settlement2 = Settlement(
            amount=50.00,
            payer_id=other.id,
            recipient_id=user.id,
        )
        db.session.add_all([settlement1, settlement2])
        db.session.commit()

        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email

        response = client.get("/settlements/history")
        assert response.status_code == 200
        assert b"Total Paid" in response.data
        assert b"Total Received" in response.data
        assert b"100.00" in response.data
        assert b"50.00" in response.data


class TestBalancePageHistoryLink:
    """Tests for settlement history link on balance page."""

    def test_balance_page_has_history_link(self, client, app):
        """Test that balance page includes link to settlement history."""
        user = User(email="link_user@example.com", display_name="Link User")
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_email"] = user.email

        response = client.get("/balance-summary")
        assert response.status_code == 200
        assert b"Settlement History" in response.data
        assert b"/settlements/history" in response.data
