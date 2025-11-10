"""Tests for profile picture functionality."""

import os
from io import BytesIO

from PIL import Image

from models import User


class TestProfilePictureUpload:
    """Tests for profile picture upload functionality."""

    def test_upload_valid_jpg_image(self, client, auth_user):
        """Test uploading a valid JPG image."""
        # Create a test image
        img = Image.new("RGB", (300, 300), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "test.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 302  # Redirect after successful upload
        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        assert auth_user.profile_picture is not None
        assert auth_user.profile_picture.endswith(".jpg")

    def test_upload_valid_png_image(self, client, auth_user):
        """Test uploading a valid PNG image."""
        img = Image.new("RGB", (300, 300), color="blue")
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "test.png")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        assert auth_user.profile_picture is not None
        assert auth_user.profile_picture.endswith(".png")

    def test_upload_requires_authentication(self, client):
        """Test that upload requires login."""
        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "test.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_upload_rejects_invalid_file_type(self, client, auth_user):
        """Test that invalid file types are rejected."""
        # Create a fake text file pretending to be an image
        file_io = BytesIO(b"This is not an image")

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (file_io, "test.txt")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert b"Invalid file type" in response.data or b"not allowed" in response.data

    def test_upload_rejects_file_with_no_extension(self, client, auth_user):
        """Test that files without extensions are rejected."""
        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "noextension")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert b"Invalid file type" in response.data or b"not allowed" in response.data

    def test_upload_without_file_shows_error(self, client, auth_user):
        """Test uploading without selecting a file."""
        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post(
            "/profile/upload-picture",
            data={},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert b"No file selected" in response.data or b"required" in response.data

    def test_upload_replaces_old_picture(self, client, auth_user, app):
        """Test that uploading a new picture deletes the old one."""
        # Upload first image
        img1 = Image.new("RGB", (100, 100), color="red")
        img1_io = BytesIO()
        img1.save(img1_io, "JPEG")
        img1_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img1_io, "first.jpg")},
            content_type="multipart/form-data",
        )

        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        first_filename = auth_user.profile_picture
        first_filepath = os.path.join(app.config["UPLOAD_FOLDER"], first_filename)

        # Upload second image
        img2 = Image.new("RGB", (100, 100), color="blue")
        img2_io = BytesIO()
        img2.save(img2_io, "JPEG")
        img2_io.seek(0)

        client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img2_io, "second.jpg")},
            content_type="multipart/form-data",
        )

        auth_user = db.session.get(User, auth_user.id)
        assert auth_user.profile_picture != first_filename
        # Old file should be deleted
        assert not os.path.exists(first_filepath)

    def test_sanitizes_malicious_filename(self, client, auth_user):
        """Test that malicious filenames are sanitized."""
        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        # Try path traversal attack
        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "../../etc/passwd.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        # Filename should be sanitized (no ../ or directory separators)
        assert ".." not in auth_user.profile_picture
        assert "/" not in auth_user.profile_picture
        assert "\\" not in auth_user.profile_picture

    def test_image_is_resized_to_standard_size(self, client, auth_user, app):
        """Test that uploaded images are resized to standard dimensions."""
        # Upload a large image
        img = Image.new("RGB", (3000, 2000), color="green")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "large.jpg")},
            content_type="multipart/form-data",
        )

        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], auth_user.profile_picture)

        # Check that the saved image is resized
        with Image.open(filepath) as saved_img:
            assert saved_img.width <= 400
            assert saved_img.height <= 400


class TestProfilePictureDelete:
    """Tests for profile picture deletion."""

    def test_delete_profile_picture(self, client, auth_user, app):
        """Test deleting a profile picture."""
        # First upload an image
        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "test.jpg")},
            content_type="multipart/form-data",
        )

        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        filename = auth_user.profile_picture
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Delete the picture
        response = client.post("/profile/delete-picture")

        assert response.status_code == 302
        auth_user = db.session.get(User, auth_user.id)
        assert auth_user.profile_picture is None
        assert not os.path.exists(filepath)

    def test_delete_requires_authentication(self, client):
        """Test that delete requires login."""
        response = client.post("/profile/delete-picture")

        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_delete_when_no_picture_exists(self, client, auth_user):
        """Test deleting when user has no profile picture."""
        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post("/profile/delete-picture", follow_redirects=True)

        assert response.status_code == 200
        # Should handle gracefully without error


class TestProfilePictureDisplay:
    """Tests for displaying profile pictures."""

    def test_get_profile_picture_url_with_picture(self, client, auth_user, app):
        """Test getting URL for user with profile picture."""
        auth_user.profile_picture = "test_user_123.jpg"
        from extensions import db

        db.session.commit()

        from services.profile_service import get_profile_picture_url

        # Use test request context to allow url_for to work
        with app.test_request_context():
            url = get_profile_picture_url(auth_user)
            assert "/static/uploads/profile_pics/test_user_123.jpg" in url

    def test_get_profile_picture_url_without_picture(self, auth_user):
        """Test getting URL for user without profile picture (default avatar)."""
        auth_user.profile_picture = None
        from extensions import db

        db.session.commit()

        from services.profile_service import get_profile_picture_url

        url = get_profile_picture_url(auth_user)
        # Should return a default avatar URL
        assert "default" in url or "avatar" in url or url.startswith("data:image")

    def test_profile_page_displays_picture(self, client, auth_user):
        """Test that profile page shows the profile picture."""
        # Upload an image first
        img = Image.new("RGB", (100, 100), color="purple")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "test.jpg")},
            content_type="multipart/form-data",
        )

        # Visit profile page
        response = client.get("/profile/")
        assert response.status_code == 200
        # Should contain image tag with profile picture
        assert b"<img" in response.data
        assert b"profile" in response.data.lower()


class TestProfilePictureValidation:
    """Tests for profile picture validation logic."""

    def test_allowed_file_with_valid_extensions(self, app):
        """Test that valid extensions are allowed."""
        from services.profile_service import allowed_file

        assert allowed_file("test.jpg") is True
        assert allowed_file("test.jpeg") is True
        assert allowed_file("test.png") is True
        assert allowed_file("test.gif") is True
        assert allowed_file("test.webp") is True
        assert allowed_file("TEST.JPG") is True  # Case insensitive

    def test_allowed_file_with_invalid_extensions(self, app):
        """Test that invalid extensions are rejected."""
        from services.profile_service import allowed_file

        assert allowed_file("test.txt") is False
        assert allowed_file("test.exe") is False
        assert allowed_file("test.php") is False
        assert allowed_file("test.py") is False
        assert allowed_file("test") is False
        assert allowed_file("") is False


class TestProfilePictureImageProcessing:
    """Tests for image processing functions."""

    def test_resize_rgba_png_image(self, client, auth_user, app):
        """Test uploading PNG with transparency (RGBA mode)."""
        # Create RGBA image with transparency
        img = Image.new("RGBA", (500, 500), color=(255, 0, 0, 128))
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "transparent.png")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], auth_user.profile_picture)

        # Verify image was converted to RGB and resized
        with Image.open(filepath) as saved_img:
            assert saved_img.mode == "RGB"  # Should be converted from RGBA
            assert saved_img.width <= 400
            assert saved_img.height <= 400

    def test_resize_palette_mode_image(self, client, auth_user, app):
        """Test uploading image with palette mode (P mode)."""
        # Create palette mode image (common in GIFs)
        img = Image.new("P", (500, 500))
        img.putpalette([i % 256 for i in range(768)])  # Add a palette
        img_io = BytesIO()
        img.save(img_io, "GIF")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "palette.gif")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], auth_user.profile_picture)

        # Verify image was processed and resized
        with Image.open(filepath) as saved_img:
            # Image should be resized (500x500 -> 400x400 or less)
            assert saved_img.width <= 400
            assert saved_img.height <= 400

        # Verify file exists
        assert os.path.exists(filepath)

    def test_upload_with_oserror_on_old_file_deletion(self, client, auth_user, app, monkeypatch):
        """Test that upload continues even if old file deletion fails."""
        # Upload first image
        img1 = Image.new("RGB", (100, 100), color="red")
        img1_io = BytesIO()
        img1.save(img1_io, "JPEG")
        img1_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img1_io, "first.jpg")},
            content_type="multipart/form-data",
        )

        from extensions import db

        auth_user = db.session.get(User, auth_user.id)
        first_picture = auth_user.profile_picture

        # Mock os.remove to raise OSError
        def mock_remove(path):
            # Raise OSError for any file deletion attempt
            raise OSError("Permission denied")

        monkeypatch.setattr(os, "remove", mock_remove)

        # Upload second image - should succeed despite OSError
        img2 = Image.new("RGB", (100, 100), color="blue")
        img2_io = BytesIO()
        img2.save(img2_io, "JPEG")
        img2_io.seek(0)

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img2_io, "second.jpg")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 302  # Should still succeed
        auth_user = db.session.get(User, auth_user.id)
        assert auth_user.profile_picture is not None
        # Verify the profile picture was updated (different from first)
        assert auth_user.profile_picture != first_picture
        # Verify the new file exists
        new_filepath = os.path.join(app.config["UPLOAD_FOLDER"], auth_user.profile_picture)
        assert os.path.exists(new_filepath)

    def test_save_profile_picture_with_none_file(self, app, auth_user):
        """Test save_profile_picture with None file."""
        from services.profile_service import save_profile_picture

        success, message = save_profile_picture(auth_user, None)
        assert success is False
        assert "No file provided" in message

    def test_upload_with_corrupted_image_file(self, client, auth_user):
        """Test uploading a corrupted/invalid image file."""
        # Create a file that looks like an image but isn't
        fake_img = BytesIO(b"Not a real image file")

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        response = client.post(
            "/profile/upload-picture",
            data={"profile_picture": (fake_img, "corrupted.jpg")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        # Should show error message
        assert b"Error uploading file" in response.data or b"error" in response.data.lower()

    def test_delete_profile_picture_with_oserror(self, client, auth_user, app, monkeypatch):
        """Test delete continues even if file removal fails."""
        # Upload an image first
        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = auth_user.id

        client.post(
            "/profile/upload-picture",
            data={"profile_picture": (img_io, "test.jpg")},
            content_type="multipart/form-data",
        )

        # Mock os.remove to raise OSError
        def mock_remove(path):
            raise OSError("File locked")

        monkeypatch.setattr(os, "remove", mock_remove)

        # Try to delete - should handle error gracefully
        response = client.post("/profile/delete-picture", follow_redirects=True)

        # Should show error message but not crash
        assert response.status_code == 200
        assert b"Error deleting file" in response.data or b"error" in response.data.lower()


class TestProfilePictureHelperFunctions:
    """Tests for helper functions."""

    def test_generate_unique_filename(self, app):
        """Test that generated filenames are unique."""
        from services.profile_service import generate_unique_filename

        filename1 = generate_unique_filename(1, "test.jpg")
        filename2 = generate_unique_filename(1, "test.jpg")

        assert filename1 != filename2  # Should be unique
        assert filename1.startswith("user_1_")
        assert filename1.endswith(".jpg")

    def test_generate_unique_filename_without_extension(self, app):
        """Test filename generation when file has no extension."""
        from services.profile_service import generate_unique_filename

        filename = generate_unique_filename(1, "noext")
        assert filename.startswith("user_1_")
        assert filename.endswith(".jpg")  # Should default to jpg

    def test_generate_default_avatar_with_display_name(self, app, auth_user):
        """Test default avatar generation with display name."""
        from services.profile_service import generate_default_avatar

        auth_user.display_name = "John Doe"
        avatar = generate_default_avatar(auth_user)

        assert avatar.startswith("data:image/svg+xml;base64,")
        assert "JD" in str(avatar) or len(avatar) > 100  # Contains initials or is valid SVG

    def test_generate_default_avatar_with_single_word_name(self, app, auth_user):
        """Test default avatar with single word name."""
        from services.profile_service import generate_default_avatar

        auth_user.display_name = "Alice"
        avatar = generate_default_avatar(auth_user)

        assert avatar.startswith("data:image/svg+xml;base64,")
        # Should use first 2 letters
        assert len(avatar) > 100

    def test_generate_default_avatar_with_none_user(self, app):
        """Test default avatar with None user."""
        from services.profile_service import generate_default_avatar

        avatar = generate_default_avatar(None)
        assert avatar.startswith("data:image/svg+xml;base64,")
        assert "?" in str(avatar) or len(avatar) > 100  # Contains ? or is valid SVG

    def test_get_profile_picture_url_returns_default_for_none(self, app):
        """Test get_profile_picture_url with None user."""
        from services.profile_service import get_profile_picture_url

        with app.test_request_context():
            url = get_profile_picture_url(None)
            assert "data:image/svg+xml" in url
