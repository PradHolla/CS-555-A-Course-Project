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

    def test_group_settings_shows_placeholders(self, client, auth_user, app):
        """Test that settings page shows placeholder sections."""
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
        assert b"Manage Members" in response.data
        assert b"Coming soon" in response.data


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
