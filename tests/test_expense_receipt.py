"""Tests for expense receipt image upload functionality."""

import os
from io import BytesIO

from PIL import Image

from models import Expense, Group, User


class TestExpenseReceiptUpload:
    """Tests for receipt image upload when creating expenses."""

    def test_upload_valid_jpg_receipt_when_creating_expense(self, client, app):
        """Test uploading a valid JPG receipt when creating an expense."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create test image
        img = Image.new("RGB", (300, 300), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Create expense with receipt
        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Lunch"),
                ("amount", "25.50"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img_io, "receipt.jpg")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302
        expense = Expense.query.filter_by(description="Lunch").first()
        assert expense is not None
        assert expense.receipt_image is not None
        assert expense.receipt_image.endswith(".jpg") or expense.receipt_image.endswith(".jpeg")

        # Verify file exists
        receipt_folder = os.path.join("static", "uploads", "receipts")
        receipt_filepath = os.path.join(receipt_folder, expense.receipt_image)
        assert os.path.exists(receipt_filepath)
        
        # Verify uploader and timestamp are stored
        assert expense.receipt_uploaded_by == "user1@example.com"
        assert expense.receipt_uploaded_at is not None

    def test_upload_valid_png_receipt_when_creating_expense(self, client, app):
        """Test uploading a valid PNG receipt when creating an expense."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create test image
        img = Image.new("RGB", (300, 300), color="blue")
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Create expense with receipt
        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Dinner"),
                ("amount", "45.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img_io, "receipt.png")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302
        expense = Expense.query.filter_by(description="Dinner").first()
        assert expense is not None
        assert expense.receipt_image is not None
        assert expense.receipt_uploaded_by == "user1@example.com"
        assert expense.receipt_uploaded_at is not None

    def test_upload_receipt_when_editing_expense(self, client, app):
        """Test uploading a receipt when editing an expense."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense without receipt
        expense = Expense(
            description="Coffee",
            amount=10.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 5.0, "user2@example.com": 5.0}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        # Create test image
        img = Image.new("RGB", (300, 300), color="green")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Edit expense with receipt
        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Coffee"),
                ("amount", "10.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img_io, "receipt.jpg")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}/expense/{expense.id}/edit",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302
        expense = db.session.get(Expense, expense.id)
        assert expense.receipt_image is not None
        assert expense.receipt_uploaded_by == "user1@example.com"
        assert expense.receipt_uploaded_at is not None

    def test_upload_replaces_old_receipt(self, client, app):
        """Test that uploading a new receipt deletes the old one."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with first receipt
        expense = Expense(
            description="Lunch",
            amount=30.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 15.0, "user2@example.com": 15.0}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        # Upload first receipt
        img1 = Image.new("RGB", (100, 100), color="red")
        img1_io = BytesIO()
        img1.save(img1_io, "JPEG")
        img1_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data1 = MultiDict(
            [
                ("description", "Lunch"),
                ("amount", "30.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img1_io, "first.jpg")),
            ]
        )

        client.post(
            f"/groups/{group.id}/expense/{expense.id}/edit",
            data=expense_data1,
            content_type="multipart/form-data",
        )

        expense = db.session.get(Expense, expense.id)
        first_filename = expense.receipt_image
        receipt_folder = os.path.join("static", "uploads", "receipts")
        first_filepath = os.path.join(receipt_folder, first_filename)

        # Upload second receipt
        img2 = Image.new("RGB", (100, 100), color="blue")
        img2_io = BytesIO()
        img2.save(img2_io, "JPEG")
        img2_io.seek(0)

        expense_data2 = MultiDict(
            [
                ("description", "Lunch"),
                ("amount", "30.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img2_io, "second.jpg")),
            ]
        )

        client.post(
            f"/groups/{group.id}/expense/{expense.id}/edit",
            data=expense_data2,
            content_type="multipart/form-data",
        )

        expense = db.session.get(Expense, expense.id)
        assert expense.receipt_image != first_filename
        # Old file should be deleted
        assert not os.path.exists(first_filepath)

    def test_upload_without_file_optional(self, client, app):
        """Test that creating expense without receipt file is optional and doesn't error."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Snacks"),
                ("amount", "15.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            follow_redirects=False,
        )

        assert response.status_code == 302
        expense = Expense.query.filter_by(description="Snacks").first()
        assert expense is not None
        # Receipt should be None (optional)
        assert expense.receipt_image is None

    def test_upload_requires_authentication(self, client, app):
        """Test that upload requires login."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Test"),
                ("amount", "10.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("receipt_image", (img_io, "test.jpg")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_upload_rejects_invalid_file_type(self, client, app):
        """Test that invalid file types are rejected."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create a fake text file
        file_io = BytesIO(b"This is not an image")

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Test"),
                ("amount", "10.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (file_io, "test.txt")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        # Should still create expense but without receipt (invalid file is silently ignored)
        assert response.status_code == 302
        expense = Expense.query.filter_by(description="Test").first()
        # Receipt should be None since invalid file type is rejected
        assert expense.receipt_image is None

    def test_upload_rejects_file_with_no_extension(self, client, app):
        """Test that files without extensions are rejected."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Test"),
                ("amount", "10.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img_io, "noextension")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        # Should still create expense but without receipt
        assert response.status_code == 302
        expense = Expense.query.filter_by(description="Test").first()
        assert expense.receipt_image is None

    def test_sanitizes_malicious_filename(self, client, app):
        """Test that malicious filenames are sanitized."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        img = Image.new("RGB", (100, 100), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Test"),
                ("amount", "10.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img_io, "../../etc/passwd.jpg")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302
        expense = Expense.query.filter_by(description="Test").first()
        if expense.receipt_image:
            # Filename should be sanitized
            assert ".." not in expense.receipt_image
            assert "/" not in expense.receipt_image
            assert "\\" not in expense.receipt_image

    def test_upload_resizes_large_images(self, client, app):
        """Test that uploaded images are resized to standard dimensions."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Upload a large image
        img = Image.new("RGB", (3000, 2000), color="green")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Large Receipt"),
                ("amount", "50.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img_io, "large.jpg")),
            ]
        )

        client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
        )

        expense = Expense.query.filter_by(description="Large Receipt").first()
        receipt_folder = os.path.join("static", "uploads", "receipts")
        receipt_filepath = os.path.join(receipt_folder, expense.receipt_image)

        # Check that the saved image is resized
        with Image.open(receipt_filepath) as saved_img:
            assert saved_img.width <= 800
            assert saved_img.height <= 800

    def test_upload_handles_rgba_png_images(self, client, app):
        """Test uploading PNG with transparency (RGBA mode)."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create RGBA image with transparency
        img = Image.new("RGBA", (500, 500), color=(255, 0, 0, 128))
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Transparent Receipt"),
                ("amount", "20.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img_io, "transparent.png")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302
        expense = Expense.query.filter_by(description="Transparent Receipt").first()
        receipt_folder = os.path.join("static", "uploads", "receipts")
        receipt_filepath = os.path.join(receipt_folder, expense.receipt_image)

        # Verify image was converted to RGB and resized
        with Image.open(receipt_filepath) as saved_img:
            assert saved_img.mode == "RGB"  # Should be converted from RGBA
            assert saved_img.width <= 800
            assert saved_img.height <= 800

    def test_upload_handles_palette_mode_images(self, client, app):
        """Test uploading image with palette mode (GIF)."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create palette mode image (common in GIFs)
        img = Image.new("P", (500, 500))
        img.putpalette([i % 256 for i in range(768)])  # Add a palette
        img_io = BytesIO()
        img.save(img_io, "GIF")
        img_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "GIF Receipt"),
                ("amount", "15.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img_io, "palette.gif")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}",
            data=expense_data,
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302
        expense = Expense.query.filter_by(description="GIF Receipt").first()
        receipt_folder = os.path.join("static", "uploads", "receipts")
        receipt_filepath = os.path.join(receipt_folder, expense.receipt_image)

        # Verify image was processed and resized
        with Image.open(receipt_filepath) as saved_img:
            assert saved_img.width <= 800
            assert saved_img.height <= 800

        # Verify file exists
        assert os.path.exists(receipt_filepath)


class TestExpenseReceiptDisplay:
    """Tests for displaying receipt images."""

    def test_expense_detail_displays_receipt_thumbnail(self, client, app):
        """Test that expense detail page shows receipt thumbnail when receipt exists."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="test_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        # Create the receipt file
        receipt_folder = os.path.join("static", "uploads", "receipts")
        os.makedirs(receipt_folder, exist_ok=True)
        receipt_filepath = os.path.join(receipt_folder, "test_receipt.jpg")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(receipt_filepath, "JPEG")

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}/expense/{expense.id}")

        assert response.status_code == 200
        assert b"Receipt:" in response.data
        assert b"test_receipt.jpg" in response.data
        assert b'receipts/test_receipt.jpg' in response.data

    def test_expense_detail_no_receipt_section_when_no_receipt(self, client, app):
        """Test that expense detail page does not show receipt section when no receipt."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense without receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        response = client.get(f"/groups/{group.id}/expense/{expense.id}")

        assert response.status_code == 200
        # Should not contain receipt section
        assert b"Receipt:" not in response.data or b"Receipt (Optional)" not in response.data


class TestExpenseReceiptDeletion:
    """Tests for receipt deletion when expense is deleted."""

    def test_deleting_expense_deletes_receipt_file(self, client, app):
        """Test that deleting expense deletes associated receipt file."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="test_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        # Create the receipt file
        receipt_folder = os.path.join("static", "uploads", "receipts")
        os.makedirs(receipt_folder, exist_ok=True)
        receipt_filepath = os.path.join(receipt_folder, "test_receipt.jpg")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(receipt_filepath, "JPEG")

        assert os.path.exists(receipt_filepath)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Delete the expense
        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete")

        assert response.status_code == 302
        # Receipt file should be deleted
        assert not os.path.exists(receipt_filepath)

    def test_deleting_expense_without_receipt_handles_gracefully(self, client, app):
        """Test that deleting expense without receipt handles gracefully."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense without receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Delete the expense
        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete")

        assert response.status_code == 302
        # Should not crash

    def test_file_deletion_errors_dont_crash_expense_deletion(self, client, app, monkeypatch):
        """Test that file deletion errors don't crash expense deletion."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="test_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        # Create the receipt file
        receipt_folder = os.path.join("static", "uploads", "receipts")
        os.makedirs(receipt_folder, exist_ok=True)
        receipt_filepath = os.path.join(receipt_folder, "test_receipt.jpg")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(receipt_filepath, "JPEG")

        # Mock os.remove to raise OSError
        def mock_remove(path):
            raise OSError("Permission denied")

        monkeypatch.setattr(os, "remove", mock_remove)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Delete the expense - should succeed despite file deletion error
        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete")

        assert response.status_code == 302
        # Expense should still be deleted from database
        expense = db.session.get(Expense, expense.id)
        assert expense is None


class TestExpenseReceiptEdgeCases:
    """Tests for edge cases in receipt handling."""

    def test_upload_with_oserror_on_old_file_deletion(self, client, app, monkeypatch):
        """Test that upload continues even if old file deletion fails."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with first receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="first_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        # Create first receipt file
        receipt_folder = os.path.join("static", "uploads", "receipts")
        os.makedirs(receipt_folder, exist_ok=True)
        first_receipt_filepath = os.path.join(receipt_folder, "first_receipt.jpg")
        img1 = Image.new("RGB", (100, 100), color="red")
        img1.save(first_receipt_filepath, "JPEG")

        # Mock os.remove to raise OSError
        original_remove = os.remove

        def mock_remove(path):
            if "first_receipt.jpg" in path:
                raise OSError("Permission denied")
            return original_remove(path)

        monkeypatch.setattr(os, "remove", mock_remove)

        # Upload second receipt
        img2 = Image.new("RGB", (100, 100), color="blue")
        img2_io = BytesIO()
        img2.save(img2_io, "JPEG")
        img2_io.seek(0)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        from werkzeug.datastructures import MultiDict

        expense_data = MultiDict(
            [
                ("description", "Test Expense"),
                ("amount", "25.00"),
                ("payer", "user1@example.com"),
                ("split_type", "equal"),
                ("participants", "user1@example.com"),
                ("participants", "user2@example.com"),
                ("receipt_image", (img2_io, "second.jpg")),
            ]
        )

        response = client.post(
            f"/groups/{group.id}/expense/{expense.id}/edit",
            data=expense_data,
            content_type="multipart/form-data",
        )

        assert response.status_code == 302
        expense = db.session.get(Expense, expense.id)
        assert expense.receipt_image is not None
        # Verify the receipt was updated (different from first)
        assert expense.receipt_image != "first_receipt.jpg"
        # Verify the new file exists
        new_receipt_filepath = os.path.join(receipt_folder, expense.receipt_image)
        assert os.path.exists(new_receipt_filepath)

    def test_receipt_file_missing_from_filesystem_handles_gracefully(self, client, app):
        """Test that missing receipt file from filesystem handles gracefully."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with receipt filename but file doesn't exist
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="missing_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Try to delete expense - should handle missing file gracefully
        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete")

        assert response.status_code == 302
        # Should not crash


class TestExpenseReceiptDeletionRoute:
    """Tests for deleting receipt via delete route."""

    def test_delete_receipt_removes_file_and_clears_fields(self, client, app):
        """Test that deleting receipt removes file and clears database fields."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="test_receipt.jpg",
            receipt_uploaded_by="user1@example.com",
        )
        from datetime import datetime, timezone

        expense.receipt_uploaded_at = datetime.now(timezone.utc)
        db.session.add(expense)
        db.session.commit()

        # Create the receipt file
        receipt_folder = os.path.join("static", "uploads", "receipts")
        os.makedirs(receipt_folder, exist_ok=True)
        receipt_filepath = os.path.join(receipt_folder, "test_receipt.jpg")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(receipt_filepath, "JPEG")

        assert os.path.exists(receipt_filepath)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Delete the receipt
        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete-receipt")

        assert response.status_code == 302
        expense = db.session.get(Expense, expense.id)
        # Receipt fields should be cleared
        assert expense.receipt_image is None
        assert expense.receipt_uploaded_by is None
        assert expense.receipt_uploaded_at is None
        # Receipt file should be deleted
        assert not os.path.exists(receipt_filepath)

    def test_delete_receipt_requires_authentication(self, client, app):
        """Test that deleting receipt requires login."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="test_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete-receipt")

        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_delete_receipt_requires_group_membership(self, client, app):
        """Test that deleting receipt requires group membership."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        user3 = User(email="user3@example.com", display_name="User 3")
        from extensions import db

        db.session.add_all([user1, user2, user3])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="test_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user3.id  # user3 is not a member

        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete-receipt")

        assert response.status_code == 302
        # Should redirect to groups list with error
        assert "/groups" in response.location

    def test_delete_receipt_when_no_receipt_handles_gracefully(self, client, app):
        """Test that deleting receipt when no receipt exists handles gracefully."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense without receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Try to delete receipt
        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete-receipt")

        assert response.status_code == 302
        # Should redirect with error message

    def test_delete_receipt_file_deletion_errors_dont_crash(self, client, app, monkeypatch):
        """Test that file deletion errors don't crash receipt deletion."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        # Create expense with receipt
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="test_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        # Create the receipt file
        receipt_folder = os.path.join("static", "uploads", "receipts")
        os.makedirs(receipt_folder, exist_ok=True)
        receipt_filepath = os.path.join(receipt_folder, "test_receipt.jpg")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(receipt_filepath, "JPEG")

        # Mock os.remove to raise OSError
        def mock_remove(path):
            raise OSError("Permission denied")

        monkeypatch.setattr(os, "remove", mock_remove)

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Delete the receipt - should succeed despite file deletion error
        response = client.post(f"/groups/{group.id}/expense/{expense.id}/delete-receipt")

        assert response.status_code == 302
        expense = db.session.get(Expense, expense.id)
        # Receipt fields should still be cleared even if file deletion fails
        assert expense.receipt_image is None
        assert expense.receipt_uploaded_by is None
        assert expense.receipt_uploaded_at is None

    def test_delete_receipt_group_not_found(self, client, app):
        """Test that deleting receipt handles group not found error."""
        # Create user
        user1 = User(email="user1@example.com", display_name="User 1")
        from extensions import db

        db.session.add(user1)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Try to delete receipt from non-existent group
        response = client.post("/groups/999/expense/1/delete-receipt")

        assert response.status_code == 302
        assert "/groups" in response.location

    def test_delete_receipt_expense_not_found(self, client, app):
        """Test that deleting receipt handles expense not found error."""
        # Create users and group
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group = Group(name="Test Group", created_by_id=user1.id)
        group.members.extend([user1, user2])
        db.session.add(group)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Try to delete receipt from non-existent expense
        response = client.post(f"/groups/{group.id}/expense/999/delete-receipt")

        assert response.status_code == 302
        assert f"/groups/{group.id}" in response.location

    def test_delete_receipt_expense_wrong_group(self, client, app):
        """Test that deleting receipt handles expense belonging to different group."""
        # Create users and groups
        user1 = User(email="user1@example.com", display_name="User 1")
        user2 = User(email="user2@example.com", display_name="User 2")
        from extensions import db

        db.session.add_all([user1, user2])
        db.session.commit()

        group1 = Group(name="Test Group 1", created_by_id=user1.id)
        group1.members.extend([user1, user2])
        group2 = Group(name="Test Group 2", created_by_id=user1.id)
        group2.members.extend([user1, user2])
        db.session.add_all([group1, group2])
        db.session.commit()

        # Create expense in group1
        expense = Expense(
            description="Test Expense",
            amount=25.00,
            payer="user1@example.com",
            group_id=group1.id,
            split_type="equal",
            split_details='{"user1@example.com": 12.5, "user2@example.com": 12.5}',
            participants="user1@example.com, user2@example.com",
            receipt_image="test_receipt.jpg",
        )
        db.session.add(expense)
        db.session.commit()

        with client.session_transaction() as session:
            session["user_id"] = user1.id

        # Try to delete receipt using group2's ID
        response = client.post(f"/groups/{group2.id}/expense/{expense.id}/delete-receipt")

        assert response.status_code == 302
        assert f"/groups/{group2.id}" in response.location

