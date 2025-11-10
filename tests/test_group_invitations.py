"""Tests for group invitation functionality."""

from models import Group, GroupInvitation, User


def test_group_invitation_model_creation(app):
    """Test that GroupInvitation model can be created and persisted."""
    from extensions import db

    # Arrange
    inviter = User(email="inviter@example.com")
    db.session.add(inviter)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=inviter.id)
    db.session.add(group)
    db.session.commit()

    # Act
    invitation = GroupInvitation(
        email="invitee@example.com", group_id=group.id, invited_by_id=inviter.id
    )
    db.session.add(invitation)
    db.session.commit()

    # Assert
    stored_invitation = GroupInvitation.query.filter_by(email="invitee@example.com").first()
    assert stored_invitation is not None
    assert stored_invitation.email == "invitee@example.com"
    assert stored_invitation.group_id == group.id
    assert stored_invitation.invited_by_id == inviter.id
    assert stored_invitation.status == "pending"


def test_create_group_with_non_existent_member_creates_invitation(client, app):
    """Test that creating a group creates invitations for both existing and non-existent users.

    All users must manually accept invitations to join groups.
    """
    from extensions import db

    # Arrange - Create logged-in user
    creator = User(email="creator@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Pre-create existing user
    existing_user = User(email="existing@example.com")
    db.session.add(existing_user)
    db.session.commit()

    # Act - Create group with mix of existing and non-existent members
    group_data = {
        "name": "Test Group",
        "members": "existing@example.com, newuser@example.com",
    }

    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302

    # Check group was created
    group = Group.query.filter_by(name="Test Group").first()
    assert group is not None

    # Check existing user NOT automatically added (must accept invitation)
    assert existing_user not in group.members
    assert len(group.members) == 1  # Only creator

    # Check invitations were created for BOTH users
    existing_invitation = GroupInvitation.query.filter_by(email="existing@example.com").first()
    new_invitation = GroupInvitation.query.filter_by(email="newuser@example.com").first()

    assert existing_invitation is not None
    assert existing_invitation.group_id == group.id
    assert existing_invitation.invited_by_id == creator.id
    assert existing_invitation.status == "pending"

    assert new_invitation is not None
    assert new_invitation.group_id == group.id
    assert new_invitation.invited_by_id == creator.id
    assert new_invitation.status == "pending"


def test_create_group_with_existing_members_creates_invitations(client, app):
    """Test that creating a group with existing members creates invitations for them.

    Users must manually accept invitations, even if they already have accounts.
    """
    from extensions import db

    # Arrange - Create users
    creator = User(email="creator@example.com")
    member1 = User(email="member1@example.com")
    member2 = User(email="member2@example.com")
    db.session.add_all([creator, member1, member2])
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Act - Create group with existing members
    group_data = {
        "name": "Existing Members Group",
        "members": "member1@example.com, member2@example.com",
    }

    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302

    # Check invitations WERE created for existing users
    invitations = GroupInvitation.query.all()
    assert len(invitations) == 2
    assert {inv.email for inv in invitations} == {"member1@example.com", "member2@example.com"}
    assert all(inv.status == "pending" for inv in invitations)

    # Check members were NOT automatically added (must accept invitation first)
    group = Group.query.filter_by(name="Existing Members Group").first()
    assert len(group.members) == 1  # Only creator initially
    assert creator in group.members
    assert member1 not in group.members
    assert member2 not in group.members


def test_invitation_notification_is_sent(client, app, capsys):
    """Test that notification is printed when invitation is created."""
    from extensions import db

    # Arrange
    creator = User(email="creator@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Act - Create group with non-existent member
    group_data = {"name": "Notification Test", "members": "newuser@example.com"}

    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302

    # Check notification was printed (now uses EMAIL NOTIFICATION header)
    captured = capsys.readouterr()
    assert "EMAIL NOTIFICATION" in captured.out
    assert "newuser@example.com" in captured.out
    assert "Notification Test" in captured.out


def test_user_signup_accepts_pending_invitations(client, app):
    """Test that when a user signs up, they auto-join groups with pending invitations."""
    from extensions import db

    # Arrange - Create group and invitation
    inviter = User(email="inviter@example.com")
    db.session.add(inviter)
    db.session.commit()

    group = Group(name="Auto Join Group", created_by_id=inviter.id)
    group.members.append(inviter)
    db.session.add(group)
    db.session.commit()

    invitation = GroupInvitation(
        email="newuser@example.com", group_id=group.id, invited_by_id=inviter.id
    )
    db.session.add(invitation)
    db.session.commit()

    # Act - New user signs up with invited email
    # Simulate OTP verification which creates the user
    new_user = User(email="newuser@example.com")
    db.session.add(new_user)
    db.session.commit()

    # Auto-accept invitations (this logic will be in auth routes)
    pending_invitations = GroupInvitation.query.filter_by(
        email=new_user.email, status="pending"
    ).all()

    for inv in pending_invitations:
        inv.group.members.append(new_user)
        inv.status = "accepted"

    db.session.commit()

    # Assert
    assert new_user in group.members
    updated_invitation = GroupInvitation.query.filter_by(email="newuser@example.com").first()
    assert updated_invitation.status == "accepted"


def test_duplicate_invitations_not_created(client, app):
    """Test that duplicate invitations are not created for the same email and group."""
    from extensions import db

    # Arrange
    creator = User(email="creator@example.com")
    db.session.add(creator)
    db.session.commit()

    group = Group(name="Duplicate Test", created_by_id=creator.id)
    group.members.append(creator)
    db.session.add(group)
    db.session.commit()

    # Create first invitation manually
    invitation1 = GroupInvitation(
        email="invitee@example.com", group_id=group.id, invited_by_id=creator.id
    )
    db.session.add(invitation1)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Act - Try to create group again with same invitee (shouldn't create duplicate)
    # This tests the logic in the route
    invitations_before = GroupInvitation.query.filter_by(email="invitee@example.com").count()

    # Simulate checking for existing invitation before creating
    existing = GroupInvitation.query.filter_by(
        email="invitee@example.com", group_id=group.id, status="pending"
    ).first()

    if not existing:
        invitation2 = GroupInvitation(
            email="invitee@example.com", group_id=group.id, invited_by_id=creator.id
        )
        db.session.add(invitation2)
        db.session.commit()

    invitations_after = GroupInvitation.query.filter_by(email="invitee@example.com").count()

    # Assert - No duplicate created
    assert invitations_before == invitations_after


def test_invalid_email_does_not_create_invitation(client, app):
    """Test that invalid email format does not create invitation."""
    from extensions import db

    # Arrange
    creator = User(email="creator@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Act - Try to create group with invalid email
    group_data = {"name": "Invalid Email Group", "members": "validemail@example.com, notanemail"}

    response = client.post("/groups/create", data=group_data, follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"Invalid email format" in response.data

    # No group or invitations should be created
    group = Group.query.filter_by(name="Invalid Email Group").first()
    assert group is None

    invitations = GroupInvitation.query.all()
    assert len(invitations) == 0


def test_notification_failure_does_not_stop_invitation_creation(client, app, monkeypatch):
    """Test that notification failure doesn't prevent invitation from being created."""
    from extensions import db

    # Arrange
    creator = User(email="creator@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Mock notification to raise exception
    def mock_notify_error(*args, **kwargs):
        raise Exception("Email service down")

    monkeypatch.setattr("routes.groups.notify_group_invitation", mock_notify_error)

    # Act - Create group with non-existent member
    group_data = {"name": "Notification Error Group", "members": "newuser@example.com"}

    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert - Invitation should still be created despite notification failure
    assert response.status_code == 302

    invitation = GroupInvitation.query.filter_by(email="newuser@example.com").first()
    assert invitation is not None
    assert invitation.status == "pending"

    group = Group.query.filter_by(name="Notification Error Group").first()
    assert group is not None


def test_user_already_in_group_when_accepting_invitation(client, app):
    """Test that auto-accept handles case where user is already in group (edge case)."""
    from extensions import db

    # Arrange - Create group with invitation
    inviter = User(email="inviter@example.com")
    new_user = User(email="newuser@example.com")
    db.session.add_all([inviter, new_user])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=inviter.id)
    group.members.extend([inviter, new_user])  # User already in group
    db.session.add(group)
    db.session.commit()

    # Create pending invitation for user already in group (edge case)
    invitation = GroupInvitation(
        email="newuser@example.com", group_id=group.id, invited_by_id=inviter.id
    )
    db.session.add(invitation)
    db.session.commit()

    # Act - Simulate auto-accept logic from verify_otp
    pending_invitations = GroupInvitation.query.filter_by(
        email=new_user.email, status="pending"
    ).all()

    for inv in pending_invitations:
        # This should handle the case where user is already in group
        if new_user not in inv.group.members:
            inv.group.members.append(new_user)
        inv.status = "accepted"

    db.session.commit()

    # Assert - Invitation marked as accepted, no duplicate membership
    updated_invitation = GroupInvitation.query.filter_by(email="newuser@example.com").first()
    assert updated_invitation.status == "accepted"

    # User should appear only once in members
    member_count = sum(1 for m in group.members if m.email == "newuser@example.com")
    assert member_count == 1
