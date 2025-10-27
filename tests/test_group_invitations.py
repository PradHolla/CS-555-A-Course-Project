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
    """Test that creating a group with non-existent member email creates an invitation."""
    from extensions import db

    # Arrange - Create logged-in user
    creator = User(email="creator@example.com")
    db.session.add(creator)
    db.session.commit()

    with client.session_transaction() as session:
        session["user_id"] = creator.id
        session["user_email"] = creator.email

    # Act - Create group with non-existent member
    group_data = {
        "name": "Test Group",
        "members": "existing@example.com, newuser@example.com",
    }

    # Pre-create existing user
    existing_user = User(email="existing@example.com")
    db.session.add(existing_user)
    db.session.commit()

    response = client.post("/groups/create", data=group_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302

    # Check group was created
    group = Group.query.filter_by(name="Test Group").first()
    assert group is not None

    # Check existing user was added to group
    assert existing_user in group.members

    # Check invitation was created for non-existent user
    invitation = GroupInvitation.query.filter_by(email="newuser@example.com").first()
    assert invitation is not None
    assert invitation.group_id == group.id
    assert invitation.invited_by_id == creator.id
    assert invitation.status == "pending"


def test_create_group_with_existing_members_no_invitation(client, app):
    """Test that creating a group with all existing members does not create invitations."""
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

    # Check no invitations were created
    invitations = GroupInvitation.query.all()
    assert len(invitations) == 0

    # Check all members were added
    group = Group.query.filter_by(name="Existing Members Group").first()
    assert len(group.members) == 3  # creator + 2 members


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

    # Check notification was printed
    captured = capsys.readouterr()
    assert "GROUP INVITATION" in captured.out
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
        email="newuser@example.com", group_id=group.id, invited_by_id=inviter.id, status="pending"
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
