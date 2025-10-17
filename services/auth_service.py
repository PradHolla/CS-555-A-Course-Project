"""Authentication service for OTP generation and validation."""

import random
from datetime import datetime, timedelta, timezone


class AuthService:
    """Service class for authentication-related operations."""

    @staticmethod
    def generate_otp():
        """
        Generate a random 6-digit OTP.

        Returns:
            str: 6-digit OTP as a string
        """
        return "".join([str(random.randint(0, 9)) for _ in range(6)])

    @staticmethod
    def get_otp_expiry(minutes=10):
        """
        Get OTP expiry timestamp.

        Args:
            minutes: Number of minutes until expiry (default: 10)

        Returns:
            datetime: Timezone-aware expiry timestamp
        """
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)
