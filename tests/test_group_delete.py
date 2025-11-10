"""Tests for group deletion behaviour."""

from models import Group, User


def test_delete_group_by_creator_removes_children(client, app):
    """Creator can delete a group and related invitations/notifications/expenses are removed."""
    from extensions import db
    from models import Expense, GroupInvitation, GroupNotification

    # Arrange
    creator = User(email="creator@example.com")
    member = User(email="member@example.com")
    db.session.add_all([creator, member])
    db.session.commit()

    group = Group(name="ToBeDeleted", created_by_id=creator.id)
    group.members.extend([creator, member])
    db.session.add(group)
    db.session.commit()

    # Add an invitation, expense and notification tied to the group
    invitation = GroupInvitation(
        email="invitee@example.com", group_id=group.id, invited_by_id=creator.id
    )
    expense = Expense(
        description="Lunch",
        amount=10.0,
        payer=creator.email,
        group_id=group.id,
        split_type="equal",
        split_details='{"creator@example.com": 10.0}',
        participants=creator.email,
    )
    notification = GroupNotification(
        group_id=group.id,
        notification_type="expense_deleted",
        description="Lunch",
        amount=10.0,
        payer=creator.email,
        deleted_by=creator.email,
        read_by="[]",
    )
    db.session.add_all([invitation, expense, notification])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email

    # Act
    response = client.post(f"/groups/{group.id}/delete", follow_redirects=False)

    # Assert - redirect to groups list and group and children removed
    assert response.status_code == 302
    assert db.session.get(Group, group.id) is None
    assert GroupInvitation.query.filter_by(group_id=group.id).first() is None
    assert Expense.query.filter_by(group_id=group.id).first() is None
    assert GroupNotification.query.filter_by(group_id=group.id).first() is None


def test_delete_group_non_creator_cannot_delete(client, app):
    """A non-creator (even a member) cannot delete the group."""
    from extensions import db

    creator = User(email="creator2@example.com")
    other = User(email="other@example.com")
    db.session.add_all([creator, other])
    db.session.commit()

    group = Group(name="SafeGroup", created_by_id=creator.id)
    group.members.extend([creator, other])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = other.id
        sess["user_email"] = other.email

    # Act
    response = client.post(f"/groups/{group.id}/delete", follow_redirects=False)

    # Assert - should not delete and should redirect back to group page
    assert response.status_code == 302
    assert db.session.get(Group, group.id) is not None


def test_delete_button_visibility(client, app):
    """Only the creator sees the Delete Group button on the group page."""
    from extensions import db

    creator = User(email="creator3@example.com")
    member = User(email="member3@example.com")
    db.session.add_all([creator, member])
    db.session.commit()

    group = Group(name="VisibleGroup", created_by_id=creator.id)
    group.members.extend([creator, member])
    db.session.add(group)
    db.session.commit()

    # As creator - should see button
    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email
    response = client.get(f"/groups/{group.id}")
    assert response.status_code == 200
    assert b"Delete Group" in response.data

    # As normal member - should NOT see button
    with client.session_transaction() as sess:
        sess["user_id"] = member.id
        sess["user_email"] = member.email
    response = client.get(f"/groups/{group.id}")
    assert response.status_code == 200
    assert b"Delete Group" not in response.data


def test_delete_group_handles_commit_failure(client, app, monkeypatch):
    """If commit fails during deletion, the group remains and an error is flashed."""
    from extensions import db

    creator = User(email="errcreator@example.com")
    db.session.add(creator)
    db.session.commit()

    group = Group(name="ErrGroup", created_by_id=creator.id)
    group.members.append(creator)
    db.session.add(group)
    db.session.commit()

    # Monkeypatch commit to raise only during delete
    real_commit = db.session.commit

    def fake_commit():
        raise Exception("boom")

    monkeypatch.setattr(db.session, "commit", fake_commit)

    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email

    response = client.post(f"/groups/{group.id}/delete", follow_redirects=True)

    # After failure, group should still exist
    assert response.status_code == 200
    assert (
        b"Failed to delete group" in response.data
        or b"Failed to delete group due to related data constraints" in response.data
    )
    assert db.session.get(Group, group.id) is not None

    # restore commit to avoid breaking other tests
    monkeypatch.setattr(db.session, "commit", real_commit)


def test_create_group_creates_invitations_for_all_users(client, app):
    """Creating a group with a mix of existing users and unknown emails should create invitations for both.

    All users (existing or new) must accept invitations to join groups.
    """
    from extensions import db
    from models import GroupInvitation

    creator = User(email="creator4@example.com")
    existing = User(email="existing@example.com")
    db.session.add_all([creator, existing])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email

    data = {
        "name": "MixedGroup",
        "members": f"{existing.email}, newinvite@example.com",
    }

    response = client.post("/groups/create", data=data, follow_redirects=False)
    assert response.status_code == 302

    group = Group.query.filter_by(name="MixedGroup").first()
    assert group is not None

    # Both existing user and new user should have invitations
    existing_inv = GroupInvitation.query.filter_by(email=existing.email, group_id=group.id).first()
    new_inv = GroupInvitation.query.filter_by(
        email="newinvite@example.com", group_id=group.id
    ).first()
    assert existing_inv is not None
    assert new_inv is not None
    assert existing_inv.status == "pending"
    assert new_inv.status == "pending"

    # Neither should be members yet (must accept invitation first)
    assert len(group.members) == 1  # Only creator
    assert not any(m.email == existing.email for m in group.members)


def test_group_expenses_create_percentage_and_shares(client, app):
    """POST to group expenses with percentage and shares splits should create expenses."""
    from extensions import db
    from models import Expense

    payer = User(email="p_percent@example.com")
    p2 = User(email="p2_percent@example.com")
    db.session.add_all([payer, p2])
    db.session.commit()

    group = Group(name="SplitGroup", created_by_id=payer.id)
    group.members.extend([payer, p2])
    db.session.add(group)
    db.session.commit()

    # Percentage split
    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    percent_data = {
        "description": "Pct Lunch",
        "amount": "100.00",
        "payer": payer.email,
        "split_type": "percentage",
        f"percentage_{payer.email}": "60",
        f"percentage_{p2.email}": "40",
    }

    response = client.post(f"/groups/{group.id}", data=percent_data, follow_redirects=False)
    assert response.status_code == 302
    expense = Expense.query.filter_by(description="Pct Lunch", group_id=group.id).first()
    assert expense is not None

    # Shares split
    shares_data = {
        "description": "Shares Dinner",
        "amount": "90.00",
        "payer": payer.email,
        "split_type": "shares",
        f"shares_{payer.email}": "2",
        f"shares_{p2.email}": "1",
    }

    response = client.post(f"/groups/{group.id}", data=shares_data, follow_redirects=False)
    assert response.status_code == 302
    expense2 = Expense.query.filter_by(description="Shares Dinner", group_id=group.id).first()
    assert expense2 is not None
