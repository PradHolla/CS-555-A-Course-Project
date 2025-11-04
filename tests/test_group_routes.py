"""Tests for group management routes."""

from models import Group, User


def test_groups_list_returns_ok(client, app):
    """Test that GET /groups/ returns 200 for logged-in user."""
    # Arrange
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.get("/groups/")

    # Assert
    assert response.status_code == 200


def test_groups_create_group_with_members(client, app):
    """Test that POST /groups/create creates invitations for non-existent members."""
    # Arrange
    from extensions import db
    from models import GroupInvitation

    # Create the logged-in user (creator)
    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    group_data = {
        "name": "My Agile group",
        "members": "anikait@example.com, sairithik@example.com, pradhyumna@example.com",
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    stored = Group.query.filter_by(name="My Agile group").first()
    assert stored is not None
    assert len(stored.members) == 1  # Only creator (others are invited)
    assert creator in stored.members
    # Check that invitations were created for non-existent users
    assert GroupInvitation.query.filter_by(email="anikait@example.com").first() is not None
    assert GroupInvitation.query.filter_by(email="sairithik@example.com").first() is not None
    assert GroupInvitation.query.filter_by(email="pradhyumna@example.com").first() is not None


def test_groups_create_group_rejects_invalid_member_emails(client, app):
    """Test that POST /groups/create rejects groups with invalid member email formats."""
    # Arrange
    from extensions import db

    # Create the logged-in user (creator)
    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Try creating group with invalid email
    group_data = {
        "name": "Invalid Email Group",
        "members": "valid@example.com, notanemail, another@example.com",
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=True)

    # Assert - should redirect back to create page with error message
    assert response.status_code == 200
    assert b"Invalid email format: notanemail" in response.data
    # Group should not have been created
    assert Group.query.filter_by(name="Invalid Email Group").first() is None


def test_groups_create_group_without_members(client, app):
    """Test that POST /groups/create works without optional members."""
    # Arrange
    from extensions import db

    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    group_data = {
        "name": "Solo Group",
        "members": "",  # No members
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    group = Group.query.filter_by(name="Solo Group").first()
    assert group is not None
    assert len(group.members) == 1  # Just the creator
    assert creator in group.members


def test_groups_create_group_requires_name(client, app):
    """Test that POST /groups/create requires a name."""
    # Arrange
    from extensions import db

    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    group_data = {
        "name": "",  # Empty name
        "members": "alice@example.com",
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert - should redirect back to create page with error
    assert response.status_code == 302
    assert response.location.endswith("/groups/create")
    assert Group.query.count() == 0  # No group created


def test_groups_create_group_skips_duplicate_creator(client, app):
    """Test that creator is not added twice if listed in members, and creates invitation for new user."""
    # Arrange
    from extensions import db
    from models import GroupInvitation

    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    group_data = {
        "name": "Test Group",
        "members": "test@example.com, alice@example.com",  # Creator in members list
    }

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302
    group = Group.query.filter_by(name="Test Group").first()
    assert group is not None
    # Creator should only be in members once
    creator_count = sum(1 for m in group.members if m.email == "test@example.com")
    assert creator_count == 1
    assert len(group.members) == 1  # Only creator (alice gets an invitation)
    # Check invitation was created for alice
    assert GroupInvitation.query.filter_by(email="alice@example.com").first() is not None


def test_groups_list_requires_login(client):
    """Test that GET /groups/ requires login."""
    # Act - no login session
    response = client.get("/groups/", follow_redirects=False)

    # Assert - should redirect to login
    assert response.status_code == 302


def test_groups_create_handles_database_error(client, app, monkeypatch):
    """Test that POST /groups/create handles database errors gracefully."""
    # Arrange
    from extensions import db

    creator = User(email="test@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Simulate database error during commit
    def mock_commit():
        raise Exception("Database error")

    monkeypatch.setattr(db.session, "commit", mock_commit)

    group_data = {"name": "Test Group", "members": "member@example.com"}

    # Act
    response = client.post("/groups/create", data=group_data, follow_redirects=True)

    # Assert - should redirect to create page with error message
    assert response.status_code == 200
    assert b"Failed to create group" in response.data


def test_groups_create_get_returns_ok(client, app):
    """Test that GET /groups/create returns 200 for logged-in user."""
    # Arrange
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.get("/groups/create")

    # Assert
    assert response.status_code == 200
    assert b"Create Group" in response.data or b"CREATE GROUP" in response.data


def test_groups_create_get_requires_login(client):
    """Test that GET /groups/create requires login."""
    # Act - no login session
    response = client.get("/groups/create", follow_redirects=False)

    # Assert - should redirect to login
    assert response.status_code == 302


def test_group_expenses_get_returns_ok(client, app):
    """Test that GET /groups/<group_id> returns 200 for logged-in group member."""
    # Arrange
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.get(f"/groups/{group.id}")

    # Assert
    assert response.status_code == 200
    assert b"Test Group" in response.data


def test_group_expenses_get_requires_login(client, app):
    """Test that GET /groups/<group_id> requires login."""
    # Arrange
    from extensions import db

    user = User(email="test@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    # Act - no login session
    response = client.get(f"/groups/{group.id}", follow_redirects=False)

    # Assert - should redirect to login
    assert response.status_code == 302


def test_group_expenses_requires_membership(client, app):
    """Test that GET /groups/<group_id> requires user to be a group member."""
    # Arrange
    from extensions import db

    member = User(email="member@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([member, non_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=member.id)
    group.members.append(member)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = non_member.id
        sess["user_email"] = non_member.email

    # Act
    response = client.get(f"/groups/{group.id}", follow_redirects=False)

    # Assert - should redirect or return 403
    assert response.status_code in [302, 403]


def test_group_expenses_post_creates_expense(client, app):
    """Test that POST /groups/<group_id> creates expense for that group."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    participant = User(email="participant@example.com")
    db.session.add_all([payer, participant])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, participant])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    # Create MultiDict to handle multiple participants
    expense_data = MultiDict(
        [
            ("description", "Lunch"),
            ("amount", "30.00"),
            ("payer", "payer@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "participant@example.com"),
        ]
    )

    # Act
    response = client.post(f"/groups/{group.id}", data=expense_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect after creation
    expense = Expense.query.filter_by(description="Lunch", group_id=group.id).first()
    assert expense is not None
    assert expense.amount == 30.0


def test_delete_expense_success(client, app):
    """Test that any group member can delete an expense."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([payer, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, deleter])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "deleter@example.com": 15.0}',
        participants="payer@example.com, deleter@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False
    )

    # Assert
    assert response.status_code == 302
    assert db.session.get(Expense, expense_id) is None


def test_delete_expense_requires_login(client, app):
    """Test that unauthenticated users cannot delete expenses."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    db.session.add(payer)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 30.0}',
        participants="payer@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    # Act - no login session
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False
    )

    # Assert - should redirect to login
    assert response.status_code == 302
    assert db.session.get(Expense, expense_id) is not None  # Expense should still exist


def test_delete_expense_requires_membership(client, app):
    """Test that non-group members cannot delete expenses."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([payer, non_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 30.0}',
        participants="payer@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = non_member.id
        sess["user_email"] = non_member.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False
    )

    # Assert - should redirect
    assert response.status_code == 302
    assert db.session.get(Expense, expense_id) is not None  # Expense should still exist


def test_delete_expense_not_found(client, app):
    """Test that deleting non-existent expense returns error."""
    # Arrange
    from extensions import db

    payer = User(email="payer@example.com")
    db.session.add(payer)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    # Act - try to delete non-existent expense
    response = client.post(
        f"/groups/{group.id}/expense/99999/delete", follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Expense not found" in response.data


def test_delete_expense_wrong_group(client, app):
    """Test that cannot delete expense from different group."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    member = User(email="member@example.com")
    db.session.add_all([payer, member])
    db.session.commit()

    group1 = Group(name="Group 1", created_by_id=payer.id)
    group2 = Group(name="Group 2", created_by_id=member.id)
    group1.members.append(payer)
    group2.members.extend([payer, member])
    db.session.add_all([group1, group2])
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group1.id,
        split_type="equal",
        split_details='{"payer@example.com": 30.0}',
        participants="payer@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = member.id
        sess["user_email"] = member.email

    # Act - try to delete expense from group1 while accessing via group2
    response = client.post(
        f"/groups/{group2.id}/expense/{expense_id}/delete", follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Expense does not belong to this group" in response.data
    assert db.session.get(Expense, expense_id) is not None  # Expense should still exist


def test_delete_expense_removes_from_database(client, app):
    """Test that expense is actually removed from database."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([payer, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, deleter])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "deleter@example.com": 15.0}',
        participants="payer@example.com, deleter@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    # Verify expense exists before deletion
    assert db.session.get(Expense, expense_id) is not None

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act
    client.post(f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False)

    # Assert
    assert db.session.get(Expense, expense_id) is None


def test_delete_expense_redirects_correctly(client, app):
    """Test that redirect goes to correct group expenses page."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([payer, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, deleter])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "deleter@example.com": 15.0}',
        participants="payer@example.com, deleter@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False
    )

    # Assert
    assert response.status_code == 302
    assert f"/groups/{group.id}" in response.location


def test_delete_expense_shows_success_message(client, app):
    """Test that flash message appears for deleter."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([payer, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, deleter])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "deleter@example.com": 15.0}',
        participants="payer@example.com, deleter@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Expense deleted successfully" in response.data


def test_delete_expense_sends_notifications(client, app):
    """Test that notifications are sent to other group members."""
    # Arrange
    from unittest.mock import patch

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    deleter = User(email="deleter@example.com")
    other_member = User(email="other@example.com")
    db.session.add_all([payer, deleter, other_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, deleter, other_member])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 10.0, "deleter@example.com": 10.0, "other@example.com": 10.0}',
        participants="payer@example.com, deleter@example.com, other@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act
    with patch("builtins.print") as mock_print:
        client.post(
            f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False
        )

        # Assert - check that notifications were printed
        assert mock_print.called
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        # Should notify payer and other_member, but not deleter
        assert "payer@example.com" in printed_output or "other@example.com" in printed_output
        assert "EXPENSE DELETION NOTIFICATION" in printed_output or "deleted" in printed_output.lower()


def test_delete_expense_no_notification_to_deleter(client, app):
    """Test that deleter does not receive notification."""
    # Arrange
    from unittest.mock import patch

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([payer, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, deleter])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "deleter@example.com": 15.0}',
        participants="payer@example.com, deleter@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act
    with patch("builtins.print") as mock_print:
        client.post(
            f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False
        )

        # Assert - check that notification is not sent TO the deleter
        if mock_print.called:
            printed_output = " ".join(str(call) for call in mock_print.call_args_list)
            # Notification should be sent TO payer@example.com but NOT TO deleter@example.com
            # The deleter's email may appear in the body as "Deleted by", but should not appear as "To:"
            assert "To: payer@example.com" in printed_output
            assert "To: deleter@example.com" not in printed_output


def test_delete_expense_user_not_found_error(client, app):
    """Test delete expense handles user not found error."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    db.session.add(payer)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 30.0}',
        participants="payer@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    # Act - Delete user after session is set up to test the defensive check
    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        # Simulate user being deleted (defensive check in function)
        db.session.delete(payer)
        db.session.flush()  # Don't commit yet, but flush to make it visible

    # The login_required decorator will catch this, but we test the defensive check
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=True
    )

    # Assert - login_required decorator should redirect to login
    assert response.status_code == 200


def test_delete_expense_group_not_found_error(client, app):
    """Test delete expense handles group not found error."""
    # Arrange
    from extensions import db
    from models import Expense

    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="user@example.com",
        group_id=99999,  # Non-existent group
        split_type="equal",
        split_details='{"user@example.com": 30.0}',
        participants="user@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.post(
        f"/groups/99999/expense/{expense_id}/delete", follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Group not found" in response.data


def test_edit_expense_with_percentage_split(client, app):
    """Test editing an expense with percentage split."""
    # Arrange
    import json

    from extensions import db
    from models import Expense

    user1 = User(email="user1@example.com")
    user2 = User(email="user2@example.com")
    db.session.add_all([user1, user2])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user1.id)
    group.members.extend([user1, user2])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Original Expense",
        amount=100.0,
        payer="user1@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user1@example.com": 50.0, "user2@example.com": 50.0}',
        participants="user1@example.com, user2@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = user1.id
        sess["user_email"] = user1.email

    # Act - Edit with percentage split (60% user1, 40% user2)
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Updated Expense",
            "amount": "100.00",
            "payer": "user1@example.com",
            "split_type": "percentage",
            "percentage_user1@example.com": "60",
            "percentage_user2@example.com": "40",
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    updated_expense = db.session.get(Expense, expense_id)
    assert updated_expense.description == "Updated Expense"
    assert updated_expense.split_type == "percentage"
    split_details = json.loads(updated_expense.split_details)
    assert split_details["user1@example.com"] == 60.0  # 60% of 100
    assert split_details["user2@example.com"] == 40.0  # 40% of 100


def test_edit_expense_with_shares_split(client, app):
    """Test editing an expense with shares split."""
    # Arrange
    import json

    from extensions import db
    from models import Expense

    user1 = User(email="user1@example.com")
    user2 = User(email="user2@example.com")
    user3 = User(email="user3@example.com")
    db.session.add_all([user1, user2, user3])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user1.id)
    group.members.extend([user1, user2, user3])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Original Expense",
        amount=120.0,
        payer="user1@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user1@example.com": 40.0, "user2@example.com": 40.0, "user3@example.com": 40.0}',
        participants="user1@example.com, user2@example.com, user3@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = user1.id
        sess["user_email"] = user1.email

    # Act - Edit with shares split (2 shares user1, 1 share user2, 1 share user3)
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Updated Shares Expense",
            "amount": "120.00",
            "payer": "user1@example.com",
            "split_type": "shares",
            "shares_user1@example.com": "2",
            "shares_user2@example.com": "1",
            "shares_user3@example.com": "1",
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    updated_expense = db.session.get(Expense, expense_id)
    assert updated_expense.description == "Updated Shares Expense"
    assert updated_expense.split_type == "shares"
    split_details = json.loads(updated_expense.split_details)
    # Total shares = 4, user1 gets 2/4 = 60, user2 gets 1/4 = 30, user3 gets 1/4 = 30
    assert split_details["user1@example.com"] == 60.0
    assert split_details["user2@example.com"] == 30.0
    assert split_details["user3@example.com"] == 30.0


def test_edit_expense_rejects_invalid_percentage_total(client, app):
    """Test that editing with percentages not totaling 100% is rejected."""
    # Arrange
    from extensions import db
    from models import Expense

    user1 = User(email="user1@example.com")
    user2 = User(email="user2@example.com")
    db.session.add_all([user1, user2])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user1.id)
    group.members.extend([user1, user2])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Original Expense",
        amount=100.0,
        payer="user1@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user1@example.com": 50.0, "user2@example.com": 50.0}',
        participants="user1@example.com, user2@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = user1.id
        sess["user_email"] = user1.email

    # Act - Try to edit with percentages totaling 90% (invalid)
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Updated Expense",
            "amount": "100.00",
            "payer": "user1@example.com",
            "split_type": "percentage",
            "percentage_user1@example.com": "50",
            "percentage_user2@example.com": "40",  # Total = 90%
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Percentages must sum to 100%" in response.data
    # Expense should not be updated
    unchanged_expense = db.session.get(Expense, expense_id)
    assert unchanged_expense.description == "Original Expense"
    assert unchanged_expense.split_type == "equal"


def test_edit_expense_rejects_negative_shares(client, app):
    """Test that editing with negative shares is rejected."""
    # Arrange
    from extensions import db
    from models import Expense

    user1 = User(email="user1@example.com")
    user2 = User(email="user2@example.com")
    db.session.add_all([user1, user2])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user1.id)
    group.members.extend([user1, user2])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Original Expense",
        amount=100.0,
        payer="user1@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user1@example.com": 50.0, "user2@example.com": 50.0}',
        participants="user1@example.com, user2@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = user1.id
        sess["user_email"] = user1.email

    # Act - Try to edit with negative shares
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Updated Expense",
            "amount": "100.00",
            "payer": "user1@example.com",
            "split_type": "shares",
            "shares_user1@example.com": "2",
            "shares_user2@example.com": "-1",  # Negative!
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Share count for user2@example.com must be positive" in response.data
    # Expense should not be updated
    unchanged_expense = db.session.get(Expense, expense_id)
    assert unchanged_expense.description == "Original Expense"
    assert unchanged_expense.split_type == "equal"


def test_delete_expense_handles_notification_error(client, app):
    """Test that expense deletion continues even if notification fails."""
    # Arrange
    from extensions import db
    from models import Expense, GroupNotification
    from unittest.mock import patch

    payer = User(email="payer@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([payer, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, deleter])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "deleter@example.com": 15.0}',
        participants="payer@example.com, deleter@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act - Simulate notification failure
    with patch("routes.groups.notify_expense_deletion", side_effect=Exception("Notification error")):
        response = client.post(
            f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False
        )

    # Assert - Expense should still be deleted and notification should be created
    assert response.status_code == 302
    assert db.session.get(Expense, expense_id) is None
    notification = GroupNotification.query.filter_by(
        group_id=group.id, notification_type="expense_deleted"
    ).first()
    assert notification is not None


def test_delete_expense_creates_notification(client, app):
    """Test that deleting an expense creates a database notification."""
    # Arrange
    from extensions import db
    from models import Expense, GroupNotification

    payer = User(email="payer@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([payer, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, deleter])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "deleter@example.com": 15.0}',
        participants="payer@example.com, deleter@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act
    client.post(f"/groups/{group.id}/expense/{expense_id}/delete", follow_redirects=False)

    # Assert
    notification = GroupNotification.query.filter_by(
        group_id=group.id, notification_type="expense_deleted"
    ).first()
    assert notification is not None
    assert notification.description == "Lunch"
    assert notification.amount == 30.0
    assert notification.payer == "payer@example.com"
    assert notification.deleted_by == deleter.email


def test_group_member_sees_deletion_notification(client, app):
    """Test that group members see deletion notification banner."""
    # Arrange
    from extensions import db
    from models import Expense, GroupNotification

    import json

    payer = User(email="payer@example.com")
    viewer = User(email="viewer@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([payer, viewer, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, viewer, deleter])
    db.session.add(group)
    db.session.commit()

    # Create notification manually (simulating deletion)
    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        deleted_by="deleter@example.com",
        read_by="[]",
    )
    db.session.add(notification)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = viewer.id
        sess["user_email"] = viewer.email

    # Act
    response = client.get(f"/groups/{group.id}")

    # Assert
    assert response.status_code == 200
    assert b"Lunch" in response.data
    assert b"$30.00" in response.data
    assert b"deleter@example.com" in response.data


def test_notification_with_null_read_by(client, app):
    """Test that notification works when read_by is None."""
    # Arrange
    from extensions import db
    from models import GroupNotification

    import json

    payer = User(email="payer@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([payer, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, viewer])
    db.session.add(group)
    db.session.commit()

    # Create notification with null read_by
    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        deleted_by="payer@example.com",
        read_by=None,  # Null read_by
    )
    db.session.add(notification)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = viewer.id
        sess["user_email"] = viewer.email

    # Act
    response = client.get(f"/groups/{group.id}")

    # Assert - Should show notification since read_by is None
    assert response.status_code == 200
    assert b"Lunch" in response.data


def test_notification_not_shown_after_read(client, app):
    """Test that notification is not shown after user marks it as read."""
    # Arrange
    from extensions import db
    from models import GroupNotification

    import json

    payer = User(email="payer@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([payer, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, viewer])
    db.session.add(group)
    db.session.commit()

    # Create notification with viewer already marked as read
    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        deleted_by="payer@example.com",
        read_by=json.dumps([viewer.id]),
    )
    db.session.add(notification)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = viewer.id
        sess["user_email"] = viewer.email

    # Act
    response = client.get(f"/groups/{group.id}")

    # Assert
    assert response.status_code == 200
    # Notification should not be shown since viewer already read it
    assert b"Expense Deleted" not in response.data or b"Lunch" not in response.data


def test_mark_notification_read_with_null_read_by(client, app):
    """Test marking notification as read when read_by is None."""
    # Arrange
    from extensions import db
    from models import GroupNotification

    import json

    payer = User(email="payer@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([payer, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, viewer])
    db.session.add(group)
    db.session.commit()

    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        deleted_by="payer@example.com",
        read_by=None,  # Null read_by
    )
    db.session.add(notification)
    db.session.commit()
    notification_id = notification.id

    with client.session_transaction() as sess:
        sess["user_id"] = viewer.id
        sess["user_email"] = viewer.email

    # Act
    response = client.post(
        f"/groups/{group.id}/notification/{notification_id}/read", follow_redirects=False
    )

    # Assert
    assert response.status_code == 302
    notification = db.session.get(GroupNotification, notification_id)
    read_by_ids = json.loads(notification.read_by)
    assert viewer.id in read_by_ids


def test_mark_notification_read_already_read(client, app):
    """Test that marking already-read notification doesn't add duplicate."""
    # Arrange
    from extensions import db
    from models import GroupNotification

    import json

    payer = User(email="payer@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([payer, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, viewer])
    db.session.add(group)
    db.session.commit()

    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        deleted_by="payer@example.com",
        read_by=json.dumps([viewer.id]),  # Already read by viewer
    )
    db.session.add(notification)
    db.session.commit()
    notification_id = notification.id

    with client.session_transaction() as sess:
        sess["user_id"] = viewer.id
        sess["user_email"] = viewer.email

    # Act - Mark as read again
    response = client.post(
        f"/groups/{group.id}/notification/{notification_id}/read", follow_redirects=False
    )

    # Assert - Should not add duplicate
    assert response.status_code == 302
    notification = db.session.get(GroupNotification, notification_id)
    read_by_ids = json.loads(notification.read_by)
    assert read_by_ids.count(viewer.id) == 1  # Should only appear once


def test_mark_notification_read(client, app):
    """Test that marking notification as read works."""
    # Arrange
    from extensions import db
    from models import GroupNotification

    import json

    payer = User(email="payer@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([payer, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, viewer])
    db.session.add(group)
    db.session.commit()

    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        deleted_by="payer@example.com",
        read_by="[]",
    )
    db.session.add(notification)
    db.session.commit()
    notification_id = notification.id

    with client.session_transaction() as sess:
        sess["user_id"] = viewer.id
        sess["user_email"] = viewer.email

    # Act
    response = client.post(
        f"/groups/{group.id}/notification/{notification_id}/read", follow_redirects=False
    )

    # Assert
    assert response.status_code == 302
    notification = db.session.get(GroupNotification, notification_id)
    read_by_ids = json.loads(notification.read_by)
    assert viewer.id in read_by_ids


def test_mark_notification_read_requires_membership(client, app):
    """Test that only group members can mark notifications as read."""
    # Arrange
    from extensions import db
    from models import GroupNotification

    import json

    payer = User(email="payer@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([payer, non_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        deleted_by="payer@example.com",
        read_by="[]",
    )
    db.session.add(notification)
    db.session.commit()
    notification_id = notification.id

    with client.session_transaction() as sess:
        sess["user_id"] = non_member.id
        sess["user_email"] = non_member.email

    # Act
    response = client.post(
        f"/groups/{group.id}/notification/{notification_id}/read", follow_redirects=False
    )

    # Assert - should redirect and not mark as read
    assert response.status_code == 302
    notification = db.session.get(GroupNotification, notification_id)
    read_by_ids = json.loads(notification.read_by)
    assert non_member.id not in read_by_ids


def test_mark_notification_read_user_not_found(client, app):
    """Test mark notification read handles user not found."""
    # Arrange
    from extensions import db
    from models import GroupNotification

    payer = User(email="payer@example.com")
    db.session.add(payer)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        deleted_by="payer@example.com",
        read_by="[]",
    )
    db.session.add(notification)
    db.session.commit()
    notification_id = notification.id

    # Act - invalid user_id in session
    with client.session_transaction() as sess:
        sess["user_id"] = 99999  # Non-existent user

    response = client.post(
        f"/groups/{group.id}/notification/{notification_id}/read", follow_redirects=False
    )

    # Assert - should redirect
    assert response.status_code == 302


def test_mark_notification_read_notification_not_found(client, app):
    """Test mark notification read handles notification not found."""
    # Arrange
    from extensions import db

    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act - try to mark non-existent notification as read
    response = client.post(
        f"/groups/{group.id}/notification/99999/read", follow_redirects=False
    )

    # Assert - should redirect
    assert response.status_code == 302


# Edit Expense Tests


def test_edit_expense_success(client, app):
    """Test that any group member can edit an expense."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - edit expense
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", "editor@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=False
    )

    # Assert
    assert response.status_code == 302
    updated_expense = db.session.get(Expense, expense_id)
    assert updated_expense is not None
    assert updated_expense.description == "Dinner"
    assert updated_expense.amount == 50.0
    assert updated_expense.payer == "editor@example.com"


def test_edit_expense_requires_login(client, app):
    """Test that unauthenticated users cannot edit expenses."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    db.session.add(payer)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 30.0}',
        participants="payer@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    # Act - no login session
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "equal",
            "participants": ["payer@example.com"],
        },
        follow_redirects=False,
    )

    # Assert - should redirect to login
    assert response.status_code == 302
    expense = db.session.get(Expense, expense_id)
    assert expense.description == "Lunch"  # Should not be changed


def test_edit_expense_requires_membership(client, app):
    """Test that non-group members cannot edit expenses."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([payer, non_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 30.0}',
        participants="payer@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = non_member.id
        sess["user_email"] = non_member.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "equal",
            "participants": ["payer@example.com"],
        },
        follow_redirects=True,
    )

    # Assert - should redirect with error
    assert response.status_code == 200
    assert b"You are not a member of this group" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.description == "Lunch"  # Should not be changed


def test_edit_expense_not_found(client, app):
    """Test that editing non-existent expense returns error."""
    # Arrange
    from extensions import db

    payer = User(email="payer@example.com")
    db.session.add(payer)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    # Act - try to edit non-existent expense
    response = client.post(
        f"/groups/{group.id}/expense/99999/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "equal",
            "participants": ["payer@example.com"],
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Expense not found" in response.data


def test_edit_expense_wrong_group(client, app):
    """Test that editing expense from different group fails."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group1 = Group(name="Group 1", created_by_id=payer.id)
    group1.members.extend([payer, editor])
    group2 = Group(name="Group 2", created_by_id=payer.id)
    group2.members.append(payer)
    db.session.add_all([group1, group2])
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group1.id,
        split_type="equal",
        split_details='{"payer@example.com": 30.0}',
        participants="payer@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    # Act - try to edit expense from group1 while accessing group2
    response = client.post(
        f"/groups/{group2.id}/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "equal",
            "participants": ["payer@example.com"],
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Expense does not belong to this group" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.description == "Lunch"  # Should not be changed


def test_edit_expense_negative_amount(client, app):
    """Test that editing expense with negative amount fails."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with negative amount
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "-10.00"),
            ("payer", "payer@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Amount must be greater than zero" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.amount == 30.0  # Should not be changed


def test_edit_expense_zero_amount(client, app):
    """Test that editing expense with zero amount fails."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with zero amount
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "0.00"),
            ("payer", "payer@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Amount must be greater than zero" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.amount == 30.0  # Should not be changed


def test_edit_expense_invalid_payer(client, app):
    """Test that editing with payer not in group fails."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([payer, editor, non_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with non-member as payer
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", "nonmember@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Payer must be a member of the group" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.payer == "payer@example.com"  # Should not be changed


def test_edit_expense_invalid_participants(client, app):
    """Test that editing with participants not in group fails."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([payer, editor, non_member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with non-member as participant
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", "payer@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "nonmember@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"not in the group" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.description == "Lunch"  # Should not be changed


def test_edit_expense_invalid_split_sum(client, app):
    """Test that editing with custom split not summing to amount fails."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with custom split that doesn't sum to amount
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "custom",
            "custom_amount_payer@example.com": "30.00",
            "custom_amount_editor@example.com": "15.00",  # Total = 45, but amount = 50
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"must equal total amount" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.amount == 30.0  # Should not be changed


def test_edit_expense_updates_database(client, app):
    """Test that editing expense updates the database correctly."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    import json

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act
    expense_data = MultiDict(
        [
            ("description", "Dinner at restaurant"),
            ("amount", "75.50"),
            ("payer", "editor@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=False
    )

    # Assert
    assert response.status_code == 302
    updated_expense = db.session.get(Expense, expense_id)
    assert updated_expense is not None
    assert updated_expense.description == "Dinner at restaurant"
    assert updated_expense.amount == 75.5
    assert updated_expense.payer == "editor@example.com"
    assert updated_expense.split_type == "equal"
    split_details = json.loads(updated_expense.split_details)
    assert len(split_details) == 2
    assert split_details["payer@example.com"] == 37.75
    assert split_details["editor@example.com"] == 37.75


def test_edit_expense_creates_notification(client, app):
    """Test that editing an expense creates a database notification."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense, GroupNotification

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", "editor@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=False
    )

    # Assert
    assert response.status_code == 302
    notification = GroupNotification.query.filter_by(
        group_id=group.id, notification_type="expense_edited"
    ).first()
    assert notification is not None
    assert notification.description == "Dinner"
    assert notification.amount == 50.0
    assert notification.payer == "editor@example.com"
    assert notification.edited_by == editor.email


def test_group_member_sees_edit_notification(client, app):
    """Test that group members see edit notification banner."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense, GroupNotification

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    viewer = User(email="viewer@example.com")
    db.session.add_all([payer, editor, viewer])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor, viewer])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    # Edit expense as editor
    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", "editor@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    client.post(f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data)

    # View as viewer
    with client.session_transaction() as sess:
        sess["user_id"] = viewer.id
        sess["user_email"] = viewer.email

    # Act
    response = client.get(f"/groups/{group.id}", follow_redirects=False)

    # Assert
    assert response.status_code == 200
    assert b"Expense Edited" in response.data
    assert b"Dinner" in response.data
    assert b"$50.00" in response.data
    assert b"editor@example.com" in response.data


def test_edit_expense_sends_notifications(client, app):
    """Test that editing expense sends terminal notifications to other members."""
    # Arrange
    from unittest.mock import patch
    from io import StringIO

    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    member = User(email="member@example.com")
    db.session.add_all([payer, editor, member])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor, member])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - capture print output
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", "editor@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    output = StringIO()
    with patch("sys.stdout", output):
        response = client.post(
            f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=False
        )

    printed_output = output.getvalue()

    # Assert
    assert response.status_code == 302
    assert "EXPENSE EDIT NOTIFICATION" in printed_output
    assert "Dinner" in printed_output
    assert "$50.00" in printed_output
    assert "To: payer@example.com" in printed_output
    assert "To: member@example.com" in printed_output


def test_edit_expense_no_notification_to_editor(client, app):
    """Test that editor does not receive terminal notification."""
    # Arrange
    from unittest.mock import patch
    from io import StringIO

    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - capture print output
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", "editor@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    output = StringIO()
    with patch("sys.stdout", output):
        response = client.post(
            f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=False
        )

    printed_output = output.getvalue()

    # Assert
    assert response.status_code == 302
    assert "To: editor@example.com" not in printed_output
    assert "To: payer@example.com" in printed_output


def test_edit_expense_handles_notification_error(client, app):
    """Test that expense editing continues even if notification fails."""
    # Arrange
    from unittest.mock import patch

    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense, GroupNotification

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - Simulate notification failure
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", "editor@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    with patch("routes.groups.notify_expense_edited", side_effect=Exception("Notification error")):
        response = client.post(
            f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=False
        )

    # Assert - Expense should still be updated and notification should be created
    assert response.status_code == 302
    updated_expense = db.session.get(Expense, expense_id)
    assert updated_expense is not None
    assert updated_expense.description == "Dinner"
    notification = GroupNotification.query.filter_by(
        group_id=group.id, notification_type="expense_edited"
    ).first()
    assert notification is not None


def test_edit_expense_missing_description(client, app):
    """Test that editing expense without description fails."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with empty description
    expense_data = MultiDict(
        [
            ("description", ""),  # Empty description
            ("amount", "50.00"),
            ("payer", "payer@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Description is required" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.description == "Lunch"  # Should not be changed


def test_edit_expense_missing_payer(client, app):
    """Test that editing expense without payer fails."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with empty payer
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "50.00"),
            ("payer", ""),  # Empty payer
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Payer is required" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.payer == "payer@example.com"  # Should not be changed


def test_edit_expense_invalid_amount_format(client, app):
    """Test that editing expense with invalid amount format fails."""
    # Arrange
    from werkzeug.datastructures import MultiDict

    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with invalid amount (non-numeric)
    expense_data = MultiDict(
        [
            ("description", "Dinner"),
            ("amount", "not_a_number"),  # Invalid amount
            ("payer", "payer@example.com"),
            ("split_type", "equal"),
            ("participants", "payer@example.com"),
            ("participants", "editor@example.com"),
        ]
    )
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit", data=expense_data, follow_redirects=True
    )

    # Assert
    assert response.status_code == 200
    assert b"Please enter a valid amount" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.amount == 30.0  # Should not be changed


def test_edit_expense_no_participants_equal_split(client, app):
    """Test that editing expense with equal split but no participants fails."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with equal split but no participants selected
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "equal",
            # No participants provided
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Please select at least one participant" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.description == "Lunch"  # Should not be changed


def test_edit_expense_invalid_custom_amount_format(client, app):
    """Test that editing expense with invalid custom amount format fails."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with invalid custom amount (non-numeric)
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "custom",
            "custom_amount_payer@example.com": "not_a_number",  # Invalid custom amount
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Invalid amount" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.amount == 30.0  # Should not be changed


def test_edit_expense_no_custom_split_amounts(client, app):
    """Test that editing expense with custom split but no amounts fails."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([payer, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.extend([payer, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 15.0, "editor@example.com": 15.0}',
        participants="payer@example.com, editor@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act - try to edit with custom split but no amounts specified
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "custom",
            # No custom_amount_* fields provided
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Please specify amounts for at least one participant" in response.data
    expense = db.session.get(Expense, expense_id)
    assert expense.description == "Lunch"  # Should not be changed


def test_edit_expense_user_not_found_error(client, app):
    """Test edit expense handles user not found error."""
    # Arrange
    from extensions import db
    from models import Expense

    payer = User(email="payer@example.com")
    db.session.add(payer)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=payer.id)
    group.members.append(payer)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="payer@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"payer@example.com": 30.0}',
        participants="payer@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    # Act - Delete user after session is set up to test the defensive check
    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        # Simulate user being deleted (defensive check in function)
        db.session.delete(payer)
        db.session.flush()  # Don't commit yet, but flush to make it visible

    # The login_required decorator will catch this, but we test the defensive check
    response = client.post(
        f"/groups/{group.id}/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "payer@example.com",
            "split_type": "equal",
            "participants": ["payer@example.com"],
        },
        follow_redirects=True,
    )

    # Assert - login_required decorator should redirect to login
    assert response.status_code == 200


def test_edit_expense_group_not_found_error(client, app):
    """Test edit expense handles group not found error."""
    # Arrange
    from extensions import db
    from models import Expense

    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=30.0,
        payer="user@example.com",
        group_id=99999,  # Non-existent group
        split_type="equal",
        split_details='{"user@example.com": 30.0}',
        participants="user@example.com",
    )
    db.session.add(expense)
    db.session.commit()
    expense_id = expense.id

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.post(
        f"/groups/99999/expense/{expense_id}/edit",
        data={
            "description": "Dinner",
            "amount": "50.00",
            "payer": "user@example.com",
            "split_type": "equal",
            "participants": ["user@example.com"],
        },
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Group not found" in response.data


    #==== TEST LEAVE GROUP ====
def test_leave_group_success(client, app):
    """Test that a group member can successfully leave a group."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    leaver = User(email="leaver@example.com")
    db.session.add_all([creator, leaver])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.extend([creator, leaver])
    db.session.add(group)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = leaver.id
        sess["user_email"] = leaver.email
    # Act
    response = client.post(f"/groups/{group.id}/leave", follow_redirects=False)
    # Assert
    assert response.status_code == 302
    assert response.location.endswith("/groups/")
    updated_group = db.session.get(Group, group.id)
    assert leaver not in updated_group.members
    assert creator in updated_group.members  # Creator stays
    assert len(updated_group.members) == 1


def test_leave_group_creator_cannot_leave(client, app):
    """Test that the group creator cannot leave the group."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    member = User(email="member@example.com")
    db.session.add_all([creator, member])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.extend([creator, member])
    db.session.add(group)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email
    # Act
    response = client.post(f"/groups/{group.id}/leave", follow_redirects=True)
    # Assert
    assert response.status_code == 200
    assert b"The group creator cannot leave the group." in response.data
    updated_group = db.session.get(Group, group.id)
    assert creator in updated_group.members
    assert member in updated_group.members


def test_leave_group_requires_login(client, app):
    """Test that unauthenticated users cannot leave a group."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    member = User(email="member@example.com")
    db.session.add_all([creator, member])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.extend([creator, member])
    db.session.add(group)
    db.session.commit()
    # Act - no login session
    response = client.post(f"/groups/{group.id}/leave", follow_redirects=False)
    # Assert
    assert response.status_code == 302
    assert "/login" in response.location
    updated_group = db.session.get(Group, group.id)
    assert member in updated_group.members  # Still in group


def test_leave_group_requires_membership(client, app):
    """Test that non-members cannot leave a group."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    non_member = User(email="nonmember@example.com")
    db.session.add_all([creator, non_member])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.append(creator)
    db.session.add(group)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = non_member.id
        sess["user_email"] = non_member.email
    # Act
    response = client.post(f"/groups/{group.id}/leave", follow_redirects=True)
    # Assert
    assert response.status_code == 200
    assert b"You are not a member of this group" in response.data
    updated_group = db.session.get(Group, group.id)
    assert non_member not in updated_group.members
    assert creator in updated_group.members


def test_leave_group_not_found(client, app):
    """Test leaving a non-existent group returns error."""
    # Arrange
    from extensions import db
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email
    # Act
    response = client.post("/groups/99999/leave", follow_redirects=True)
    # Assert
    assert response.status_code == 200
    assert b"Group not found" in response.data


def test_leave_group_redirects_to_groups_list(client, app):
    """Test that after leaving, user is redirected to /groups/."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    leaver = User(email="leaver@example.com")
    db.session.add_all([creator, leaver])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.extend([creator, leaver])
    db.session.add(group)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = leaver.id
        sess["user_email"] = leaver.email
    # Act
    response = client.post(f"/groups/{group.id}/leave", follow_redirects=False)
    # Assert
    assert response.status_code == 302
    assert response.location.endswith("/groups/")


def test_leave_group_shows_success_message(client, app):
    """Test that a flash message confirms successful leave."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    leaver = User(email="leaver@example.com")
    db.session.add_all([creator, leaver])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.extend([creator, leaver])
    db.session.add(group)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = leaver.id
        sess["user_email"] = leaver.email
    # Act
    response = client.post(f"/groups/{group.id}/leave", follow_redirects=True)
    # Assert
    assert response.status_code == 200
    assert b"You have left the group" in response.data or b"left the group" in response.data.lower()


def test_leave_group_removes_only_leaver(client, app):
    """Test that only the leaving user is removed from the group."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    leaver = User(email="leaver@example.com")
    other = User(email="other@example.com")
    db.session.add_all([creator, leaver, other])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.extend([creator, leaver, other])
    db.session.add(group)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = leaver.id
        sess["user_email"] = leaver.email
    # Act
    client.post(f"/groups/{group.id}/leave")
    # Assert
    updated_group = db.session.get(Group, group.id)
    assert leaver not in updated_group.members
    assert creator in updated_group.members
    assert other in updated_group.members
    assert len(updated_group.members) == 2


def test_leave_group_last_member_except_creator(client, app):
    """Test that a group with only creator + one member allows leaving."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    leaver = User(email="leaver@example.com")
    db.session.add_all([creator, leaver])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.extend([creator, leaver])
    db.session.add(group)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = leaver.id
        sess["user_email"] = leaver.email
    # Act
    response = client.post(f"/groups/{group.id}/leave", follow_redirects=False)
    # Assert
    assert response.status_code == 302
    updated_group = db.session.get(Group, group.id)
    assert leaver not in updated_group.members
    assert creator in updated_group.members
    assert len(updated_group.members) == 1  # Only creator remains


def test_leave_group_user_not_found_defensive(client, app):
    """Test defensive handling when user is deleted mid-session."""
    # Arrange
    from extensions import db
    creator = User(email="creator@example.com")
    leaver = User(email="leaver@example.com")
    db.session.add_all([creator, leaver])
    db.session.commit()
    group = Group(name="Test Group", created_by_id=creator.id)
    group.members.extend([creator, leaver])
    db.session.add(group)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = leaver.id
        sess["user_email"] = leaver.email
        # Simulate user deletion
        db.session.delete(leaver)
        db.session.flush()
    # Act
    response = client.post(f"/groups/{group.id}/leave", follow_redirects=True)
    # Assert - should redirect to login due to login_required
    assert response.status_code == 200
    # Group should still exist, leaver already gone
    updated_group = db.session.get(Group, group.id)
    assert creator in updated_group.members

