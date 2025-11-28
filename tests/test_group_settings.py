"""Tests for group settings and profile picture functionality."""

import os
from io import BytesIO

from PIL import Image

from extensions import db
from models import Group, User


class TestGroupSettings:
    """Tests for group settings page access."""

    def test_group_settings_requires_login(self, client):
        """Test that group settings requires authentication."""
        response = client.get("/groups/1/settings")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_group_settings_nonexistent_group(self, client, auth_user):
        """Test accessing settings for nonexistent group."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        response = client.get("/groups/99999/settings", follow_redirects=True)
        assert response.status_code == 200
        assert b"Group not found" in response.data

    def test_group_settings_non_member(self, client, auth_user, app):
        """Test that non-members cannot access group settings."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        # Create another user and group
        other_user = User(email="other@test.com")
        db.session.add(other_user)
        db.session.commit()

        group = Group(name="Other Group", created_by_id=other_user.id)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings", follow_redirects=True)
        assert response.status_code == 200
        assert b"not a member" in response.data

    def test_group_settings_page_loads(self, client, auth_user, app):
        """Test that group settings page loads for members."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings")
        assert response.status_code == 200
        assert b"Group Settings" in response.data
        assert b"Test Group" in response.data
        assert b"Group Picture" in response.data

    def test_group_settings_shows_sections(self, client, auth_user, app):
        """Test that settings page shows all functional sections."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings")
        assert response.status_code == 200
        # Check for section headers
        assert b"Group Picture" in response.data
        assert b"Edit Group Name" in response.data
        assert b"Manage Members" in response.data
        # Check for actual functionality (not placeholders)
        assert b"edit-name" in response.data  # Edit name form action
        assert b"invite-members" in response.data  # Invite members form action


class TestGroupPictureUpload:
    """Tests for group profile picture upload."""

    def create_test_image(self, format="PNG", size=(100, 100), color="red"):
        """Helper to create a test image in memory."""
        img = Image.new("RGB", size, color)
        img_io = BytesIO()
        img.save(img_io, format)
        img_io.seek(0)
        return img_io

    def test_upload_requires_login(self, client):
        """Test that upload requires authentication."""
        response = client.post("/groups/1/upload-picture")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_upload_nonexistent_group(self, client, auth_user):
        """Test uploading to nonexistent group."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        response = client.post("/groups/99999/upload-picture", follow_redirects=True)
        assert response.status_code == 200
        assert b"Group not found" in response.data

    def test_upload_non_member(self, client, auth_user, app):
        """Test that non-members cannot upload group pictures."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        other_user = User(email="other@test.com")
        db.session.add(other_user)
        db.session.commit()

        group = Group(name="Other Group", created_by_id=other_user.id)
        db.session.add(group)
        db.session.commit()

        response = client.post(f"/groups/{group.id}/upload-picture", follow_redirects=True)
        assert response.status_code == 200
        assert b"not a member" in response.data

    def test_upload_no_file(self, client, auth_user, app):
        """Test upload without file."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(f"/groups/{group.id}/upload-picture", data={}, follow_redirects=True)
        assert response.status_code == 200
        assert b"No file uploaded" in response.data

    def test_upload_empty_filename(self, client, auth_user, app):
        """Test upload with empty filename."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/upload-picture",
            data={"profile_picture": (BytesIO(b""), "")},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"No file selected" in response.data

    def test_upload_invalid_file_type(self, client, auth_user, app):
        """Test upload with invalid file type."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/upload-picture",
            data={"profile_picture": (BytesIO(b"fake content"), "test.txt")},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Invalid file type" in response.data

    def test_upload_valid_image_png(self, client, auth_user, app, tmp_path):
        """Test successful upload of PNG image."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Create test image
        img_data = self.create_test_image("PNG")

        # Set upload folder to tmp_path
        upload_folder = tmp_path / "static" / "uploads" / "group_pics"
        upload_folder.mkdir(parents=True, exist_ok=True)

        with client.application.app_context():
            # Temporarily override the upload folder
            old_cwd = os.getcwd()
            os.chdir(tmp_path)

            try:
                response = client.post(
                    f"/groups/{group.id}/upload-picture",
                    data={"profile_picture": (img_data, "test.png")},
                    follow_redirects=False,
                )
                assert response.status_code == 302

                # Check database
                updated_group = db.session.get(Group, group.id)
                assert updated_group.profile_picture is not None
                assert updated_group.profile_picture.endswith(".png")

                # Check file exists
                filepath = upload_folder / updated_group.profile_picture
                assert filepath.exists()

                # Verify image was processed
                img = Image.open(filepath)
                assert img.format == "JPEG"  # Should be converted to JPEG
                assert img.size[0] <= 500
                assert img.size[1] <= 500
            finally:
                os.chdir(old_cwd)

    def test_upload_valid_image_jpg(self, client, auth_user, app, tmp_path):
        """Test successful upload of JPG image."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        img_data = self.create_test_image("JPEG")

        upload_folder = tmp_path / "static" / "uploads" / "group_pics"
        upload_folder.mkdir(parents=True, exist_ok=True)

        old_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            response = client.post(
                f"/groups/{group.id}/upload-picture",
                data={"profile_picture": (img_data, "test.jpg")},
                follow_redirects=False,
            )
            assert response.status_code == 302

            updated_group = db.session.get(Group, group.id)
            assert updated_group.profile_picture is not None
            assert updated_group.profile_picture.endswith(".jpg")
        finally:
            os.chdir(old_cwd)

    def test_upload_replaces_old_picture(self, client, auth_user, app, tmp_path):
        """Test that uploading new picture replaces old one."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        upload_folder = tmp_path / "static" / "uploads" / "group_pics"
        upload_folder.mkdir(parents=True, exist_ok=True)

        old_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Upload first image
            img_data1 = self.create_test_image("PNG", color="red")
            client.post(
                f"/groups/{group.id}/upload-picture",
                data={"profile_picture": (img_data1, "first.png")},
            )

            first_filename = db.session.get(Group, group.id).profile_picture
            first_filepath = upload_folder / first_filename

            # Upload second image
            img_data2 = self.create_test_image("PNG", color="blue")
            client.post(
                f"/groups/{group.id}/upload-picture",
                data={"profile_picture": (img_data2, "second.png")},
            )

            second_filename = db.session.get(Group, group.id).profile_picture

            # Verify old file was deleted
            assert not first_filepath.exists()
            assert first_filename != second_filename
        finally:
            os.chdir(old_cwd)

    def test_upload_large_image_resized(self, client, auth_user, app, tmp_path):
        """Test that large images are resized to max 500x500."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Create large image
        img_data = self.create_test_image("PNG", size=(2000, 2000))

        upload_folder = tmp_path / "static" / "uploads" / "group_pics"
        upload_folder.mkdir(parents=True, exist_ok=True)

        old_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            client.post(
                f"/groups/{group.id}/upload-picture",
                data={"profile_picture": (img_data, "large.png")},
            )

            updated_group = db.session.get(Group, group.id)
            filepath = upload_folder / updated_group.profile_picture

            # Verify size
            img = Image.open(filepath)
            assert img.size[0] <= 500
            assert img.size[1] <= 500
        finally:
            os.chdir(old_cwd)


class TestGroupPictureDelete:
    """Tests for group profile picture deletion."""

    def test_delete_requires_login(self, client):
        """Test that delete requires authentication."""
        response = client.post("/groups/1/delete-picture")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_delete_nonexistent_group(self, client, auth_user):
        """Test deleting from nonexistent group."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        response = client.post("/groups/99999/delete-picture", follow_redirects=True)
        assert response.status_code == 200
        assert b"Group not found" in response.data

    def test_delete_non_member(self, client, auth_user, app):
        """Test that non-members cannot delete group pictures."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        other_user = User(email="other@test.com")
        db.session.add(other_user)
        db.session.commit()

        group = Group(name="Other Group", created_by_id=other_user.id)
        db.session.add(group)
        db.session.commit()

        response = client.post(f"/groups/{group.id}/delete-picture", follow_redirects=True)
        assert response.status_code == 200
        assert b"not a member" in response.data

    def test_delete_no_picture(self, client, auth_user, app):
        """Test deleting when no picture exists."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(f"/groups/{group.id}/delete-picture", follow_redirects=True)
        assert response.status_code == 200
        assert b"No picture to delete" in response.data

    def test_delete_picture_success(self, client, auth_user, app, tmp_path):
        """Test successful deletion of group picture."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Create test file
        upload_folder = tmp_path / "static" / "uploads" / "group_pics"
        upload_folder.mkdir(parents=True, exist_ok=True)
        test_filename = "test_group.jpg"
        test_filepath = upload_folder / test_filename
        test_filepath.write_bytes(b"fake image data")

        # Set picture in database
        group.profile_picture = test_filename
        db.session.commit()

        old_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            response = client.post(f"/groups/{group.id}/delete-picture", follow_redirects=False)
            assert response.status_code == 302

            # Verify database cleared
            updated_group = db.session.get(Group, group.id)
            assert updated_group.profile_picture is None

            # Verify file deleted
            assert not test_filepath.exists()
        finally:
            os.chdir(old_cwd)

    def test_delete_picture_file_not_exists(self, client, auth_user, app, tmp_path):
        """Test deleting picture when file doesn't exist (orphaned DB record)."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        group.profile_picture = "nonexistent.jpg"
        db.session.add(group)
        db.session.commit()

        upload_folder = tmp_path / "static" / "uploads" / "group_pics"
        upload_folder.mkdir(parents=True, exist_ok=True)

        old_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            response = client.post(f"/groups/{group.id}/delete-picture", follow_redirects=True)
            assert response.status_code == 200

            # Should still clear database even if file doesn't exist
            updated_group = db.session.get(Group, group.id)
            assert updated_group.profile_picture is None
        finally:
            os.chdir(old_cwd)


class TestGroupAvatarIntegration:
    """Tests for group avatar display integration."""

    def test_groups_list_shows_default_avatar(self, client, auth_user, app):
        """Test that groups list shows default avatar when no picture."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get("/groups/")
        assert response.status_code == 200
        # Should show initials in default avatar
        assert b"TE" in response.data  # First 2 letters of "Test Group"

    def test_groups_list_shows_uploaded_picture(self, client, auth_user, app):
        """Test that groups list shows uploaded picture."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id, profile_picture="test_pic.jpg")
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get("/groups/")
        assert response.status_code == 200
        assert b"group_pics/test_pic.jpg" in response.data

    def test_settings_page_shows_current_picture(self, client, auth_user, app):
        """Test that settings page displays current picture."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id, profile_picture="test_pic.jpg")
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings")
        assert response.status_code == 200
        assert b"group_pics/test_pic.jpg" in response.data
        assert b"Delete Picture" in response.data

    def test_settings_page_shows_default_when_no_picture(self, client, auth_user, app):
        """Test that settings page shows default avatar when no picture."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Cool Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings")
        assert response.status_code == 200
        # Should show initials
        assert b"CO" in response.data  # First 2 letters of "Cool Group"
        assert b"Delete Picture" not in response.data

    def test_expenses_page_has_settings_link(self, client, auth_user, app):
        """Test that expenses page has link to settings."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200
        assert b"Settings" in response.data
        assert f"/groups/{group.id}/settings".encode() in response.data


class TestMemberManagement:
    """Tests for inviting members to groups."""

    def test_invite_members_requires_login(self, client):
        """Test that invite members requires authentication."""
        response = client.post("/groups/1/invite-members", data={"member_emails": "test@test.com"})
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_invite_members_nonexistent_group(self, client, auth_user):
        """Test inviting members to nonexistent group."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        response = client.post(
            "/groups/99999/invite-members",
            data={"member_emails": "test@test.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Group not found" in response.data

    def test_invite_members_non_member(self, client, auth_user):
        """Test that non-members cannot invite members."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        # Create another user and group
        other_user = User(email="other@test.com")
        db.session.add(other_user)
        db.session.commit()

        group = Group(name="Other Group", created_by_id=other_user.id)
        group.members.append(other_user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/invite-members",
            data={"member_emails": "test@test.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"not a member" in response.data

    def test_invite_members_empty_emails(self, client, auth_user):
        """Test inviting with empty email list."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/invite-members", data={"member_emails": ""}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Please enter at least one email" in response.data

    def test_invite_members_invalid_email(self, client, auth_user):
        """Test inviting with invalid email format."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/invite-members",
            data={"member_emails": "notanemail"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Invalid email format" in response.data

    def test_invite_members_single_email(self, client, auth_user):
        """Test successfully inviting a single member."""
        from models import GroupInvitation

        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/invite-members",
            data={"member_emails": "newuser@test.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"1 invitation(s) sent successfully" in response.data

        # Verify invitation was created
        invitation = GroupInvitation.query.filter_by(
            email="newuser@test.com", group_id=group.id
        ).first()
        assert invitation is not None
        assert invitation.status == "pending"

    def test_invite_members_multiple_emails(self, client, auth_user):
        """Test inviting multiple members at once."""
        from models import GroupInvitation

        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/invite-members",
            data={"member_emails": "user1@test.com, user2@test.com, user3@test.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"3 invitation(s) sent successfully" in response.data

        # Verify all invitations were created
        invitations = GroupInvitation.query.filter_by(group_id=group.id).all()
        assert len(invitations) == 3
        emails = {inv.email for inv in invitations}
        assert "user1@test.com" in emails
        assert "user2@test.com" in emails
        assert "user3@test.com" in emails

    
    def test_invite_members_rejects_when_group_full(self, client, auth_user):
        """Test inviting members fails when group already has 5 participants."""
        from models import GroupInvitation
    
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email
    
        creator = db.session.get(User, auth_user.id)
    
        # Create group and add it to session FIRST
        group = Group(name="Full Group", created_by_id=creator.id)
        db.session.add(group)
    
        # Flush so group gets an ID before adding members
        db.session.flush()
    
        # Add creator as member
        group.members.append(creator)
    
        # Add four additional members to reach 5 total participants
        for idx in range(4):
            member = User(email=f"member{idx}@test.com")
            db.session.add(member)
            db.session.flush()
            group.members.append(member)
    
        db.session.commit()
    
        response = client.post(
            f"/groups/{group.id}/invite-members",
            data={"member_emails": "newmember@test.com"},
            follow_redirects=True,
        )
    
        assert response.status_code == 200
        assert b"Group limit reached!" in response.data
    
        assert (
            GroupInvitation.query.filter_by(email="newmember@test.com", group_id=group.id).first()
            is None
        )

    def test_invite_members_already_member(self, client, auth_user):
        """Test inviting user who is already a member."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        existing_member = User(email="existing@test.com")
        db.session.add(existing_member)
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        group.members.append(existing_member)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/invite-members",
            data={"member_emails": "existing@test.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Already members" in response.data

    def test_invite_members_already_invited(self, client, auth_user):
        """Test inviting user who already has pending invitation."""
        from models import GroupInvitation

        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        # Create existing invitation
        invitation = GroupInvitation(
            email="invited@test.com", group_id=group.id, invited_by_id=user.id
        )
        db.session.add(invitation)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/invite-members",
            data={"member_emails": "invited@test.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Already invited" in response.data

    def test_invite_members_mixed_scenario(self, client, auth_user):
        """Test inviting mix of new, existing members, and already invited."""
        from models import GroupInvitation

        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        existing_member = User(email="member@test.com")
        db.session.add(existing_member)
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        group.members.append(existing_member)
        db.session.add(group)
        db.session.commit()

        # Create existing invitation
        invitation = GroupInvitation(
            email="invited@test.com", group_id=group.id, invited_by_id=user.id
        )
        db.session.add(invitation)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/invite-members",
            data={"member_emails": "newuser@test.com, member@test.com, invited@test.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"1 invitation(s) sent successfully" in response.data
        assert b"Already members" in response.data
        assert b"Already invited" in response.data

    def test_settings_page_shows_invite_ui(self, client, auth_user):
        """Test that settings page shows invite members UI."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings")
        assert response.status_code == 200
        assert b"Invite New Members" in response.data
        assert b"Email Addresses" in response.data
        assert b"Send Invitations" in response.data
        assert b"Current Members" in response.data

    def test_settings_page_shows_all_members(self, client, auth_user):
        """Test that settings page displays all group members."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        member1 = User(email="member1@test.com", display_name="Member One")
        member2 = User(email="member2@test.com", display_name="Member Two")
        db.session.add(member1)
        db.session.add(member2)
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        group.members.append(member1)
        group.members.append(member2)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings")
        assert response.status_code == 200
        assert b"Current Members (3)" in response.data
        assert b"member1@test.com" in response.data
        assert b"member2@test.com" in response.data
        assert b"Member One" in response.data
        assert b"Member Two" in response.data

    def test_settings_page_marks_creator(self, client, auth_user):
        """Test that settings page marks the group creator."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        other_member = User(email="other@test.com", display_name="Other Member")
        db.session.add(other_member)
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        group.members.append(other_member)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings")
        assert response.status_code == 200
        assert b"Creator" in response.data


class TestEditGroupName:
    """Tests for editing group name."""

    def test_edit_group_name_requires_login(self, client):
        """Test that edit group name requires authentication."""
        response = client.post("/groups/1/edit-name", data={"group_name": "New Name"})
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_edit_group_name_nonexistent_group(self, client, auth_user):
        """Test editing name for nonexistent group."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        response = client.post(
            "/groups/99999/edit-name", data={"group_name": "New Name"}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Group not found" in response.data

    def test_edit_group_name_non_member(self, client, auth_user):
        """Test that non-members cannot edit group name."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        # Create another user and group
        other_user = User(email="other@test.com")
        db.session.add(other_user)
        db.session.commit()

        group = Group(name="Other Group", created_by_id=other_user.id)
        group.members.append(other_user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/edit-name", data={"group_name": "New Name"}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"not a member" in response.data

    def test_edit_group_name_empty_name(self, client, auth_user):
        """Test editing with empty name."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/edit-name", data={"group_name": ""}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"cannot be empty" in response.data

        # Verify name wasn't changed
        db.session.expire_all()
        updated_group = db.session.get(Group, group.id)
        assert updated_group.name == "Test Group"

    def test_edit_group_name_whitespace_only(self, client, auth_user):
        """Test editing with whitespace-only name."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/edit-name", data={"group_name": "   "}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"cannot be empty" in response.data

    def test_edit_group_name_too_long(self, client, auth_user):
        """Test editing with name exceeding max length."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        long_name = "A" * 101  # Exceeds 100 character limit

        response = client.post(
            f"/groups/{group.id}/edit-name", data={"group_name": long_name}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"100 characters or less" in response.data

    def test_edit_group_name_success(self, client, auth_user):
        """Test successfully editing group name."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Old Name", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/edit-name", data={"group_name": "New Name"}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Group renamed" in response.data
        assert b"Old Name" in response.data
        assert b"New Name" in response.data

        # Verify name was actually changed in database
        db.session.expire_all()
        updated_group = db.session.get(Group, group.id)
        assert updated_group.name == "New Name"

    def test_edit_group_name_max_length_allowed(self, client, auth_user):
        """Test editing with exactly 100 characters (max allowed)."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        max_name = "A" * 100  # Exactly 100 characters

        response = client.post(
            f"/groups/{group.id}/edit-name", data={"group_name": max_name}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Group renamed" in response.data

        # Verify name was changed
        db.session.expire_all()
        updated_group = db.session.get(Group, group.id)
        assert updated_group.name == max_name

    def test_edit_group_name_trims_whitespace(self, client, auth_user):
        """Test that leading/trailing whitespace is trimmed."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/edit-name",
            data={"group_name": "  New Name  "},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Group renamed" in response.data

        # Verify whitespace was trimmed
        db.session.expire_all()
        updated_group = db.session.get(Group, group.id)
        assert updated_group.name == "New Name"

    def test_edit_group_name_any_member_can_edit(self, client, auth_user):
        """Test that any group member (not just creator) can edit name."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        # Create group with different creator
        creator = User(email="creator@test.com")
        db.session.add(creator)
        db.session.commit()

        # Refresh auth_user to get it in the current session
        user = db.session.get(User, auth_user.id)

        group = Group(name="Test Group", created_by_id=creator.id)
        group.members.append(creator)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f"/groups/{group.id}/edit-name",
            data={"group_name": "Renamed by Member"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Group renamed" in response.data

        # Verify name was changed
        db.session.expire_all()
        updated_group = db.session.get(Group, group.id)
        assert updated_group.name == "Renamed by Member"

    def test_edit_group_name_with_special_characters(self, client, auth_user):
        """Test editing with special characters in name."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        special_name = "Team #1 - Best Group! 🎉"

        response = client.post(
            f"/groups/{group.id}/edit-name",
            data={"group_name": special_name},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Group renamed" in response.data

        # Verify name was changed
        db.session.expire_all()
        updated_group = db.session.get(Group, group.id)
        assert updated_group.name == special_name

    def test_settings_page_shows_edit_name_form(self, client, auth_user):
        """Test that settings page shows edit name form."""
        with client.session_transaction() as sess:
            sess["user_id"] = auth_user.id
            sess["user_email"] = auth_user.email

        user = db.session.get(User, auth_user.id)
        group = Group(name="Test Group", created_by_id=user.id)
        group.members.append(user)
        db.session.add(group)
        db.session.commit()

        response = client.get(f"/groups/{group.id}/settings")
        assert response.status_code == 200
        assert b"Edit Group Name" in response.data
        assert b"group_name" in response.data
        assert b"Save Name" in response.data
        assert b"Test Group" in response.data  # Current name should be in input

    
    
