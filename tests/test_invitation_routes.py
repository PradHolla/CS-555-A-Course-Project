"""Tests for invitation management routes."""

from models import Group, GroupInvitation, User


def test_invitations_list_returns_ok(client, app):
    """Test that GET /invitations returns 200 and displays pending invitations."""
    # Arrange
    from extensions import db

    with app.app_context():
        # Create inviter and invitee users
        inviter = User(email="inviter@example.com", display_name="Inviter User")
        invitee = User(email="invitee@example.com", display_name="Invitee User")
        db.session.add_all([inviter, invitee])
        db.session.commit()

        # Create group
        group = Group(name="Test Group", created_by_id=inviter.id)
        group.members.append(inviter)
        db.session.add(group)
        db.session.commit()

        # Create pending invitation
        invitation = GroupInvitation(
            email="invitee@example.com", group_id=group.id, invited_by_id=inviter.id
        )
        db.session.add(invitation)
        db.session.commit()

        invitee_id = invitee.id

    # Login as invitee
    with client.session_transaction() as sess:
        sess["user_id"] = invitee_id
        sess["user_email"] = "invitee@example.com"

    # Act
    response = client.get("/invitations/")

    # Assert
    assert response.status_code == 200
    assert b"Test Group" in response.data
    assert b"Inviter User" in response.data


def test_invitations_list_requires_login(client):
    """Test that /invitations redirects to login when not authenticated."""
    # Act
    response = client.get("/invitations/", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_accept_invitation_adds_user_to_group(client, app):
    """Test that POST /invitations/<id>/accept adds user to group."""
    # Arrange
    from extensions import db

    with app.app_context():
        inviter = User(email="inviter@example.com")
        invitee = User(email="invitee@example.com")
        db.session.add_all([inviter, invitee])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=inviter.id)
        group.members.append(inviter)
        db.session.add(group)
        db.session.commit()

        invitation = GroupInvitation(
            email="invitee@example.com", group_id=group.id, invited_by_id=inviter.id
        )
        db.session.add(invitation)
        db.session.commit()

        invitee_id = invitee.id
        invitation_id = invitation.id
        group_id = group.id

    with client.session_transaction() as sess:
        sess["user_id"] = invitee_id
        sess["user_email"] = "invitee@example.com"

    # Act
    response = client.post(f"/invitations/{invitation_id}/accept", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/invitations" in response.location

    # Verify user added to group
    with app.app_context():
        group = db.session.get(Group, group_id)
        invitee = db.session.get(User, invitee_id)
        assert invitee in group.members

        # Verify invitation status updated
        invitation = db.session.get(GroupInvitation, invitation_id)
        assert invitation.status == "accepted"


def test_decline_invitation_marks_as_declined(client, app):
    """Test that POST /invitations/<id>/decline marks invitation as declined."""
    # Arrange
    from extensions import db

    with app.app_context():
        inviter = User(email="inviter@example.com")
        invitee = User(email="invitee@example.com")
        db.session.add_all([inviter, invitee])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=inviter.id)
        group.members.append(inviter)
        db.session.add(group)
        db.session.commit()

        invitation = GroupInvitation(
            email="invitee@example.com", group_id=group.id, invited_by_id=inviter.id
        )
        db.session.add(invitation)
        db.session.commit()

        invitee_id = invitee.id
        invitation_id = invitation.id
        group_id = group.id

    with client.session_transaction() as sess:
        sess["user_id"] = invitee_id
        sess["user_email"] = "invitee@example.com"

    # Act
    response = client.post(f"/invitations/{invitation_id}/decline", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/invitations" in response.location

    # Verify user NOT added to group
    with app.app_context():
        group = db.session.get(Group, group_id)
        invitee = db.session.get(User, invitee_id)
        assert invitee not in group.members

        # Verify invitation status updated
        invitation = db.session.get(GroupInvitation, invitation_id)
        assert invitation.status == "declined"


def test_accept_invitation_requires_login(client, app):
    """Test that accepting invitation requires authentication."""
    # Arrange
    with app.app_context():
        from extensions import db

        inviter = User(email="inviter@example.com")
        db.session.add(inviter)
        db.session.commit()

        group = Group(name="Test Group", created_by_id=inviter.id)
        db.session.add(group)
        db.session.commit()

        invitation = GroupInvitation(
            email="test@example.com", group_id=group.id, invited_by_id=inviter.id
        )
        db.session.add(invitation)
        db.session.commit()
        invitation_id = invitation.id

    # Act (not logged in)
    response = client.post(f"/invitations/{invitation_id}/accept", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_accept_invitation_only_by_invitee(client, app):
    """Test that only the invited user can accept the invitation."""
    # Arrange
    from extensions import db

    with app.app_context():
        inviter = User(email="inviter@example.com")
        invitee = User(email="invitee@example.com")
        other_user = User(email="other@example.com")
        db.session.add_all([inviter, invitee, other_user])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=inviter.id)
        db.session.add(group)
        db.session.commit()

        invitation = GroupInvitation(
            email="invitee@example.com", group_id=group.id, invited_by_id=inviter.id
        )
        db.session.add(invitation)
        db.session.commit()

        other_user_id = other_user.id
        invitation_id = invitation.id

    # Login as different user
    with client.session_transaction() as sess:
        sess["user_id"] = other_user_id
        sess["user_email"] = "other@example.com"

    # Act
    response = client.post(f"/invitations/{invitation_id}/accept", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"not authorized" in response.data or b"Not authorized" in response.data


def test_invitations_list_only_shows_pending(client, app):
    """Test that invitations list only shows pending invitations."""
    # Arrange
    from extensions import db

    with app.app_context():
        inviter = User(email="inviter@example.com")
        invitee = User(email="invitee@example.com")
        db.session.add_all([inviter, invitee])
        db.session.commit()

        group1 = Group(name="Pending Group", created_by_id=inviter.id)
        group2 = Group(name="Accepted Group", created_by_id=inviter.id)
        group3 = Group(name="Declined Group", created_by_id=inviter.id)
        db.session.add_all([group1, group2, group3])
        db.session.commit()

        # Pending invitation
        invitation1 = GroupInvitation(
            email="invitee@example.com", group_id=group1.id, invited_by_id=inviter.id, status="pending"
        )
        # Accepted invitation
        invitation2 = GroupInvitation(
            email="invitee@example.com", group_id=group2.id, invited_by_id=inviter.id, status="accepted"
        )
        # Declined invitation
        invitation3 = GroupInvitation(
            email="invitee@example.com", group_id=group3.id, invited_by_id=inviter.id, status="declined"
        )
        db.session.add_all([invitation1, invitation2, invitation3])
        db.session.commit()

        invitee_id = invitee.id

    with client.session_transaction() as sess:
        sess["user_id"] = invitee_id
        sess["user_email"] = "invitee@example.com"

    # Act
    response = client.get("/invitations/")

    # Assert
    assert response.status_code == 200
    assert b"Pending Group" in response.data
    assert b"Accepted Group" not in response.data
    assert b"Declined Group" not in response.data


def test_accept_invitation_shows_success_message(client, app):
    """Test that accepting invitation shows success flash message."""
    # Arrange
    from extensions import db

    with app.app_context():
        inviter = User(email="inviter@example.com")
        invitee = User(email="invitee@example.com")
        db.session.add_all([inviter, invitee])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=inviter.id)
        db.session.add(group)
        db.session.commit()

        invitation = GroupInvitation(
            email="invitee@example.com", group_id=group.id, invited_by_id=inviter.id
        )
        db.session.add(invitation)
        db.session.commit()

        invitee_id = invitee.id
        invitation_id = invitation.id

    with client.session_transaction() as sess:
        sess["user_id"] = invitee_id
        sess["user_email"] = "invitee@example.com"

    # Act
    response = client.post(f"/invitations/{invitation_id}/accept", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"accepted" in response.data or b"joined" in response.data


def test_invitation_not_found(client, app):
    """Test that accepting non-existent invitation returns error."""
    # Arrange
    from extensions import db

    with app.app_context():
        user = User(email="test@example.com")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_email"] = "test@example.com"

    # Act
    response = client.post("/invitations/99999/accept", follow_redirects=True)

    # Assert
    assert response.status_code == 200
    assert b"not found" in response.data or b"Not found" in response.data
