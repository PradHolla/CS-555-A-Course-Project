"""Validation utilities for the application."""

import re


def is_valid_email(email):
    """
    Validate email format using regex.

    Args:
        email: Email string to validate

    Returns:
        bool: True if email is valid format, False otherwise
    """
    if not email:
        return False

    # Basic email regex pattern
    # Matches: user@domain.com, user.name@domain.co.uk, a@b.co, etc.
    # Rejects: consecutive dots, leading/trailing dots, missing @ or domain
    # Allow single character usernames and domains
    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9._%+-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$"

    return re.match(pattern, email) is not None
