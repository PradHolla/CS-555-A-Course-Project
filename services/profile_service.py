"""Service layer for profile picture management."""

import base64
import os
import uuid

from flask import current_app, url_for
from PIL import Image
from werkzeug.utils import secure_filename

from extensions import db


def allowed_file(filename):
    """Check if the file extension is allowed."""
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in current_app.config.get("ALLOWED_EXTENSIONS", set())


def generate_unique_filename(user_id, original_filename):
    """Generate a unique filename for the uploaded picture."""
    extension = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "jpg"
    # Use user_id and UUID to ensure uniqueness
    unique_id = str(uuid.uuid4())[:8]
    return f"user_{user_id}_{unique_id}.{extension}"


def resize_image(image_path, max_size=(400, 400)):
    """Resize image to fit within max_size while maintaining aspect ratio."""
    with Image.open(image_path) as img:
        # Convert RGBA to RGB if necessary (for PNG with transparency)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background

        # Resize maintaining aspect ratio
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save the resized image
        img.save(image_path, optimize=True, quality=85)


def save_profile_picture(user, file):
    """
    Save a profile picture for the user.

    Args:
        user: User model instance
        file: FileStorage object from request.files

    Returns:
        tuple: (success: bool, message: str)
    """
    if not file:
        return False, "No file provided"

    if not allowed_file(file.filename):
        return False, "Invalid file type. Allowed types: jpg, jpeg, png, gif, webp"

    try:
        # Generate secure filename
        filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(user.id, filename)

        # Get upload folder path
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, unique_filename)

        # Delete old profile picture if exists
        if user.profile_picture:
            old_filepath = os.path.join(upload_folder, user.profile_picture)
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                except OSError:
                    pass  # Continue even if deletion fails

        # Save the file
        file.save(filepath)

        # Resize the image
        resize_image(filepath)

        # Update user model
        user.profile_picture = unique_filename
        db.session.commit()

        return True, "Profile picture uploaded successfully"

    except Exception as e:
        db.session.rollback()
        return False, f"Error uploading file: {str(e)}"


def delete_profile_picture(user):
    """
    Delete a user's profile picture.

    Args:
        user: User model instance

    Returns:
        tuple: (success: bool, message: str)
    """
    if not user.profile_picture:
        return True, "No profile picture to delete"

    try:
        # Delete file from filesystem
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        filepath = os.path.join(upload_folder, user.profile_picture)

        if os.path.exists(filepath):
            os.remove(filepath)

        # Update user model
        user.profile_picture = None
        db.session.commit()

        return True, "Profile picture deleted successfully"

    except Exception as e:
        db.session.rollback()
        return False, f"Error deleting file: {str(e)}"


def get_profile_picture_url(user):
    """
    Get the URL for a user's profile picture or default avatar.

    Args:
        user: User model instance

    Returns:
        str: URL to profile picture or default avatar
    """
    if user and user.profile_picture:
        return url_for("static", filename=f"uploads/profile_pics/{user.profile_picture}")

    # Return a simple SVG default avatar with user's initials
    return generate_default_avatar(user)


def generate_default_avatar(user):
    """
    Generate a default avatar SVG with user's initials.

    Args:
        user: User model instance

    Returns:
        str: Data URI for SVG avatar
    """
    if not user:
        initials = "?"
        color = "#6B7280"  # Gray
    else:
        # Get initials from display name or email
        name = user.display_name or user.email
        if " " in name:
            parts = name.split()
            initials = (parts[0][0] + parts[-1][0]).upper()
        else:
            initials = name[:2].upper()

        # Generate a color based on user ID
        colors = [
            "#EF4444",  # Red
            "#F59E0B",  # Orange
            "#10B981",  # Green
            "#3B82F6",  # Blue
            "#8B5CF6",  # Purple
            "#EC4899",  # Pink
        ]
        color = colors[user.id % len(colors)]

    # Create SVG data URI
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
        <rect width="200" height="200" fill="{color}"/>
        <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
              font-family="Arial, sans-serif" font-size="80" font-weight="bold" fill="white">
            {initials}
        </text>
    </svg>"""

    # Convert to data URI
    svg_bytes = svg.encode("utf-8")
    svg_base64 = base64.b64encode(svg_bytes).decode("utf-8")
    return f"data:image/svg+xml;base64,{svg_base64}"
