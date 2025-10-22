from datetime import datetime, timezone

from extensions import db


class User(db.Model):
    """User model for authentication."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def is_otp_valid(self, entered_otp):
        """Check if the entered OTP is valid and not expired."""
        if not self.otp or not self.otp_expiry:
            return False

        if self.otp != entered_otp:
            return False

        # Make otp_expiry timezone-aware if it isn't already
        expiry = self.otp_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expiry:
            return False

        return True


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payer = db.Column(db.String(100), nullable=False)
    participants = db.Column(db.Text)  # Keep for backward compatibility during migration
    group_id = db.Column(
        db.Integer, db.ForeignKey("group.id"), nullable=True
    )  # Start as nullable for migration
    split_type = db.Column(db.String(20), nullable=False, default="equal")  # 'equal' or 'custom'
    split_details = db.Column(db.Text)  # JSON string: {"member": amount}
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    group = db.relationship("Group", backref="expenses")


class Settlement(db.Model):
    """Settlement model for tracking payments between users."""

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    payer = db.relationship("User", foreign_keys=[payer_id], backref="payments_made")
    recipient = db.relationship("User", foreign_keys=[recipient_id], backref="payments_received")


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    members = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
