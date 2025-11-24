from datetime import date, datetime, timezone

from extensions import db

# Association table for many-to-many relationship between Users and Groups
group_members = db.Table(
    "group_members",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("group.id"), primary_key=True),
    db.Column("joined_at", db.DateTime, default=lambda: datetime.now(timezone.utc)),
)


class User(db.Model):
    """User model for authentication."""

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(100), nullable=True)  # User's display name for groups
    email = db.Column(db.String(200), nullable=False, unique=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)  # Filename for profile picture
    daily_reminder_enabled = db.Column(
        db.Boolean, default=True, nullable=False
    )  # Daily reminder preference
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Many-to-many relationship with Groups
    groups = db.relationship(
        "Group", secondary=group_members, back_populates="members", lazy="dynamic"
    )

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

    # Relationship
    comments = db.relationship("Comment", backref="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payer = db.Column(db.String(100), nullable=False)
    participants = db.Column(db.Text)  # Keep for backward compatibility during migration
    group_id = db.Column(
        db.Integer, db.ForeignKey("group.id"), nullable=True
    )  # Start as nullable for migration
    split_type = db.Column(
        db.String(20), nullable=False, default="equal"
    )  # 'equal', 'custom', 'percentage', or 'shares'
    split_details = db.Column(db.Text)  # JSON string: {"member": amount/percentage/shares}
    category = db.Column(db.String(50), nullable=True)  # Expense category
    expense_date = db.Column(db.Date, default=lambda: date.today())  # Date when expense occurred
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    group = db.relationship("Group", backref="expenses")
    comments = db.relationship(
        "Comment", backref="expense", lazy="dynamic", cascade="all, delete-orphan"
    )


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
    profile_picture = db.Column(db.String(255), nullable=True)  # Filename for group picture
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )  # Who created the group

    # Many-to-many relationship with Users
    members = db.relationship(
        "User", secondary=group_members, back_populates="groups", lazy="select"
    )

    # Creator relationship
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<Group {self.name}>"


class GroupInvitation(db.Model):
    """Model for tracking pending group invitations."""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="pending"
    )  # 'pending', 'accepted', 'declined'
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    group = db.relationship("Group", backref="invitations")
    invited_by = db.relationship("User", foreign_keys=[invited_by_id])

    def __repr__(self):
        return f"<GroupInvitation {self.email} -> {self.group.name}>"


class GroupNotification(db.Model):
    """Model for tracking group notifications like expense deletions and edits."""

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    notification_type = db.Column(
        db.String(50), nullable=False
    )  # 'expense_deleted', 'expense_edited'
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=True)
    payer = db.Column(db.String(200), nullable=True)
    deleted_by = db.Column(db.String(200), nullable=True)
    edited_by = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    read_by = db.Column(db.Text)  # JSON array of user IDs who have seen this

    # Relationships
    group = db.relationship("Group", backref="notifications")

    def __repr__(self):
        return f"<GroupNotification {self.notification_type} for group {self.group_id}>"


class Comment(db.Model):
    """Model for comments on expenses."""

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expense.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Comment {self.id} on expense {self.expense_id}>"


class UserGroupPoints(db.Model):
    """Model for tracking points earned by users in groups."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", backref="group_points")
    group = db.relationship("Group", backref="member_points")

    # Unique constraint: one record per user per group
    __table_args__ = (db.UniqueConstraint("user_id", "group_id", name="unique_user_group_points"),)

    def __repr__(self):
        return f"<UserGroupPoints user_id={self.user_id} group_id={self.group_id} points={self.points}>"
