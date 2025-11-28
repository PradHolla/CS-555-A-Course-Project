"""
Comprehensive seed script for SprintPay expense management application.

This script populates the database with realistic test data covering all features:
- Users with various configurations
- Groups with multiple members
- Group invitations (pending, accepted, declined)
- Expenses with all split types (equal, custom, percentage, shares)
- Comments on expenses
- Settlements between users
- Announcements (pinned and unpinned)
- Group notifications
- User group points

Usage:
    python seed.py

TEST USER LOGIN EMAILS (created by this script):
================================================
 1. alice.anderson@gmail.com (Alice Anderson)
 2. bob.brown@yahoo.com (Bob Brown)
 3. charlie.chen@outlook.com (Charlie Chen)
 4. diana.davis@gmail.com (Diana Davis)
 5. eve.evans@yahoo.com (Eve Evans)
 6. frank.foster@outlook.com (Frank Foster)
 7. grace.garcia@gmail.com (Grace Garcia)
 8. henry.harris@yahoo.com (Henry Harris)
 9. ivy.ito@outlook.com (Ivy Ito)
10. jack.johnson@gmail.com (Jack Johnson)
11. liam.foster@example.com (Liam Foster)
12. alice.smith@yahoo.com (Alice Smith)
13. kate.evans@example.com (Kate Evans)
14. bob.kim@gmail.com (Bob Kim)
15. jack.ito@example.com (Jack Ito)
16. sam.johnson@gmail.com
17. liam.foster@gmail.com (Liam Foster)
18. paul.johnson@outlook.com (Paul Johnson)
19. noah.anderson@hotmail.com (Noah Anderson)
20. paul.o'brien@hotmail.com (Paul O'Brien)
21. frank.garcia@example.com (Frank Garcia)
22. liam.taylor@gmail.com (Liam Taylor)
23. rachel.kim@example.com (Rachel Kim)
24. sam.o'brien@yahoo.com (Sam O'Brien)
25. bob.harris@yahoo.com (Bob Harris)
"""

import json
import random
from datetime import date, datetime, timedelta, timezone

from app import create_app
from extensions import db
from models import (
    Announcement,
    Comment,
    Expense,
    Group,
    GroupInvitation,
    GroupNotification,
    Settlement,
    User,
    UserGroupPoints,
)
from services.points_service import PointsService

# Sample data
FIRST_NAMES = [
    "Alice",
    "Bob",
    "Charlie",
    "Diana",
    "Eve",
    "Frank",
    "Grace",
    "Henry",
    "Ivy",
    "Jack",
    "Kate",
    "Liam",
    "Mia",
    "Noah",
    "Olivia",
    "Paul",
    "Quinn",
    "Rachel",
    "Sam",
    "Tina",
]

LAST_NAMES = [
    "Anderson",
    "Brown",
    "Chen",
    "Davis",
    "Evans",
    "Foster",
    "Garcia",
    "Harris",
    "Ito",
    "Johnson",
    "Kim",
    "Lee",
    "Martinez",
    "Nguyen",
    "O'Brien",
    "Patel",
    "Quinn",
    "Rodriguez",
    "Smith",
    "Taylor",
]

GROUP_NAMES = [
    "Roommates 2024",
    "Weekend Trip to Vegas",
    "Office Lunch Club",
    "Family Reunion",
    "College Study Group",
    "Gaming Night Squad",
    "Book Club",
    "Fitness Buddies",
    "Travel Europe 2024",
    "Birthday Party Planning",
    "House Renovation",
    "Wedding Planning",
    "Holiday Shopping",
    "Car Pool Group",
    "Dinner Club",
]

EXPENSE_DESCRIPTIONS = [
    "Groceries at Whole Foods",
    "Uber ride to airport",
    "Restaurant dinner",
    "Movie tickets",
    "Concert tickets",
    "Hotel booking",
    "Gas for road trip",
    "Coffee shop",
    "Bar tab",
    "Grocery shopping",
    "Amazon order",
    "Netflix subscription",
    "Spotify premium",
    "Electricity bill",
    "Water bill",
    "Internet bill",
    "Phone bill",
    "Rent payment",
    "Parking fee",
    "Toll charges",
    "Breakfast at diner",
    "Lunch at cafe",
    "Dinner at restaurant",
    "Snacks and drinks",
    "Shopping at mall",
    "Gym membership",
    "Yoga class",
    "Fitness equipment",
    "Books",
    "School supplies",
    "Party decorations",
    "Birthday cake",
    "Gift purchase",
    "Charity donation",
    "Taxi fare",
    "Train ticket",
    "Bus pass",
    "Flight ticket",
    "Airbnb booking",
    "Vacation rental",
]

CATEGORIES = [
    "Food & Dining",
    "Transportation",
    "Entertainment",
    "Shopping",
    "Bills & Utilities",
    "Travel",
    "Groceries",
    "Subscriptions",
    "Health & Fitness",
    "Education",
    "Gifts",
    "Other",
]

COMMENT_TEXTS = [
    "Thanks for covering this!",
    "I'll pay you back soon.",
    "This was a great meal!",
    "Can you send me the receipt?",
    "I think the amount is wrong.",
    "Thanks for organizing!",
    "Let me know when you want to be paid back.",
    "This was fun!",
    "I'll split this with you.",
    "Thanks for picking this up!",
    "I owe you one!",
    "Perfect, thanks!",
    "Can we discuss this?",
    "I'll handle the next one.",
    "Thanks for the reminder!",
]

ANNOUNCEMENT_TEXTS = [
    "Remember to submit receipts by end of week",
    "Group dinner this Friday at 7pm",
    "Please settle outstanding balances",
    "New member joined the group",
    "Upcoming trip planning meeting",
    "Expense report due next Monday",
    "Group photo session this weekend",
    "Important: Check your balances",
    "Welcome to the group!",
    "Monthly summary available",
    "Don't forget to add your expenses",
    "Group settings updated",
    "New feature: Points system active",
    "Reminder: Payment deadline approaching",
    "Thanks for being part of this group!",
]


def generate_email(first_name, last_name):
    """Generate a realistic email address."""
    domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "example.com"])
    return f"{first_name.lower()}.{last_name.lower()}@{domain}"


def create_users(num_users=25):
    """Create users with various configurations.
    
    First creates 10 known test users with predictable emails,
    then creates additional random users.
    """
    users = []
    
    # Known test users with predictable emails for easy login
    TEST_USERS = [
        ("Alice", "Anderson", "alice.anderson@gmail.com"),
        ("Bob", "Brown", "bob.brown@yahoo.com"),
        ("Charlie", "Chen", "charlie.chen@outlook.com"),
        ("Diana", "Davis", "diana.davis@gmail.com"),
        ("Eve", "Evans", "eve.evans@yahoo.com"),
        ("Frank", "Foster", "frank.foster@outlook.com"),
        ("Grace", "Garcia", "grace.garcia@gmail.com"),
        ("Henry", "Harris", "henry.harris@yahoo.com"),
        ("Ivy", "Ito", "ivy.ito@outlook.com"),
        ("Jack", "Johnson", "jack.johnson@gmail.com"),
    ]
    
    print(f"Creating {len(TEST_USERS)} known test users + {num_users - len(TEST_USERS)} random users...")
    
    # Create known test users first
    for first_name, last_name, email in TEST_USERS:
        # Skip if user already exists
        if User.query.filter_by(email=email).first():
            continue
            
        user = User(
            email=email,
            display_name=f"{first_name} {last_name}",
            daily_reminder_enabled=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 365)),
        )
        db.session.add(user)
        users.append(user)
    
    # Create additional random users
    remaining_users = num_users - len(users)
    for i in range(remaining_users):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        email = generate_email(first_name, last_name)

        # Ensure unique emails
        while User.query.filter_by(email=email).first():
            email = generate_email(first_name, last_name)

        # Some users have display names, some don't
        display_name = None
        if random.random() > 0.2:  # 80% have display names
            display_name = f"{first_name} {last_name}"

        # Some users have daily reminders disabled
        daily_reminder_enabled = random.random() > 0.3  # 70% have reminders enabled

        # Create user with random creation date (within last year)
        days_ago = random.randint(0, 365)
        created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

        user = User(
            email=email,
            display_name=display_name,
            daily_reminder_enabled=daily_reminder_enabled,
            created_at=created_at,
        )
        db.session.add(user)
        users.append(user)

    db.session.commit()
    print(f"✓ Created {len(users)} users")
    
    # Print all user emails for reference
    print("\nAll user emails (for login testing):")
    print("-" * 60)
    for i, user in enumerate(users, 1):
        display = f" ({user.display_name})" if user.display_name else ""
        print(f"{i:2d}. {user.email}{display}")
    print("-" * 60)
    print()
    
    return users


def create_groups(users, num_groups=15):
    """Create groups with various member configurations."""
    groups = []
    print(f"Creating {num_groups} groups...")

    for i in range(num_groups):
        name = random.choice(GROUP_NAMES)
        # Ensure unique group names
        while Group.query.filter_by(name=name).first():
            name = f"{name} {random.randint(1, 1000)}"

        # Select a random creator
        creator = random.choice(users)

        # Create group with random creation date
        days_ago = random.randint(0, 180)
        created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

        group = Group(name=name, created_by_id=creator.id, created_at=created_at)
        db.session.add(group)
        db.session.flush()  # Get group.id

        # Add creator as first member
        group.members.append(creator)

        # Add 2-8 additional random members
        num_members = random.randint(2, 8)
        available_users = [u for u in users if u not in group.members]
        additional_members = random.sample(available_users, min(num_members, len(available_users)))

        for member in additional_members:
            group.members.append(member)

        groups.append(group)

    db.session.commit()
    print(f"✓ Created {len(groups)} groups")
    return groups


def create_invitations(users, groups):
    """Create group invitations with various statuses."""
    invitations = []
    print("Creating group invitations...")

    for group in groups:
        # Create 0-5 invitations per group
        num_invitations = random.randint(0, 5)

        for _ in range(num_invitations):
            # Invite random users (some may not exist in system)
            if random.random() > 0.7:  # 30% chance to invite non-existing user
                email = generate_email(random.choice(FIRST_NAMES), random.choice(LAST_NAMES))
            else:
                # Invite existing user
                user = random.choice(users)
                email = user.email

            # Skip if user is already a member
            if any(m.email == email for m in group.members):
                continue

            # Skip if invitation already exists
            if GroupInvitation.query.filter_by(email=email, group_id=group.id).first():
                continue

            # Random status: 60% pending, 30% accepted, 10% declined
            status_rand = random.random()
            if status_rand < 0.6:
                status = "pending"
            elif status_rand < 0.9:
                status = "accepted"
            else:
                status = "declined"

            invited_by = random.choice(group.members)

            # Create invitation with random date
            days_ago = random.randint(0, 30)
            created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

            invitation = GroupInvitation(
                email=email,
                group_id=group.id,
                invited_by_id=invited_by.id,
                status=status,
                created_at=created_at,
            )
            db.session.add(invitation)
            invitations.append(invitation)

    db.session.commit()
    print(f"✓ Created {len(invitations)} invitations")
    return invitations


def create_expenses(groups, num_expenses_per_group=15):
    """Create expenses with all split types and various configurations."""
    expenses = []
    print(f"Creating expenses (target: {num_expenses_per_group} per group)...")

    split_types = ["equal", "custom", "percentage", "shares"]

    for group in groups:
        members = list(group.members)
        if len(members) < 2:
            continue

        # Create multiple expenses per group
        num_expenses = random.randint(5, num_expenses_per_group)

        for _ in range(num_expenses):
            # Random payer
            payer = random.choice(members)

            # Random split type
            split_type = random.choice(split_types)

            # Random description and category
            description = random.choice(EXPENSE_DESCRIPTIONS)
            category = random.choice(CATEGORIES) if random.random() > 0.1 else None  # 90% have category

            # Random amount between $5 and $500
            amount = round(random.uniform(5.0, 500.0), 2)

            # Random date within last 6 months
            days_ago = random.randint(0, 180)
            expense_date = date.today() - timedelta(days=days_ago)

            # Calculate split details based on split type
            split_details = {}

            if split_type == "equal":
                # Select 2 to all members as participants
                num_participants = random.randint(2, len(members))
                participants = random.sample(members, num_participants)
                participant_emails = [p.email for p in participants]

                # Calculate equal split
                per_person = round(amount / len(participants), 2)
                # Adjust for rounding
                total = per_person * len(participants)
                remainder = round(amount - total, 2)

                for email in participant_emails:
                    split_details[email] = per_person

                # Add remainder to first participant
                if remainder != 0 and participant_emails:
                    split_details[participant_emails[0]] = round(
                        split_details[participant_emails[0]] + remainder, 2
                    )

            elif split_type == "custom":
                # Select 2 to all members
                num_participants = random.randint(2, len(members))
                participants = random.sample(members, num_participants)
                participant_emails = [p.email for p in participants]

                # Assign random custom amounts
                remaining = amount
                for i, email in enumerate(participant_emails):
                    if i == len(participant_emails) - 1:
                        # Last person gets remainder
                        split_details[email] = round(remaining, 2)
                    else:
                        # Random amount between $1 and remaining
                        max_amount = remaining - (len(participant_emails) - i - 1) * 1.0
                        custom_amount = round(random.uniform(1.0, max(1.0, max_amount)), 2)
                        split_details[email] = custom_amount
                        remaining -= custom_amount

            elif split_type == "percentage":
                # Select 2 to all members
                num_participants = random.randint(2, len(members))
                participants = random.sample(members, num_participants)
                participant_emails = [p.email for p in participants]

                # Assign random percentages (must sum to 100)
                percentages = []
                remaining = 100.0
                for i in range(len(participants)):
                    if i == len(participants) - 1:
                        percentages.append(remaining)
                    else:
                        pct = round(random.uniform(5.0, remaining - (len(participants) - i - 1) * 5.0), 2)
                        percentages.append(pct)
                        remaining -= pct

                # Shuffle percentages
                random.shuffle(percentages)

                # Calculate amounts from percentages
                for email, pct in zip(participant_emails, percentages):
                    split_details[email] = round(amount * pct / 100.0, 2)

                # Adjust for rounding
                total = sum(split_details.values())
                remainder = round(amount - total, 2)
                if remainder != 0 and participant_emails:
                    split_details[participant_emails[0]] = round(
                        split_details[participant_emails[0]] + remainder, 2
                    )

            else:  # shares
                # Select 2 to all members
                num_participants = random.randint(2, len(members))
                participants = random.sample(members, num_participants)
                participant_emails = [p.email for p in participants]

                # Assign random shares (1-10 per person)
                shares = {}
                total_shares = 0
                for email in participant_emails:
                    share = random.randint(1, 10)
                    shares[email] = share
                    total_shares += share

                # Calculate amounts from shares
                for email in participant_emails:
                    split_details[email] = round(amount * shares[email] / total_shares, 2)

                # Adjust for rounding
                total = sum(split_details.values())
                remainder = round(amount - total, 2)
                if remainder != 0 and participant_emails:
                    split_details[participant_emails[0]] = round(
                        split_details[participant_emails[0]] + remainder, 2
                    )

            # Create expense
            expense = Expense(
                description=description,
                amount=amount,
                payer=payer.email,
                group_id=group.id,
                split_type=split_type,
                split_details=json.dumps(split_details),
                participants=", ".join(split_details.keys()),
                category=category,
                expense_date=expense_date,
                created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
            )

            # 20% of expenses have receipts
            if random.random() < 0.2:
                expense.receipt_image = f"receipt_{random.randint(1000, 9999)}.jpg"
                expense.receipt_uploaded_by = payer.email
                expense.receipt_uploaded_at = datetime.now(timezone.utc) - timedelta(
                    days=days_ago, hours=random.randint(1, 12)
                )

            db.session.add(expense)
            expenses.append(expense)

    db.session.commit()
    print(f"✓ Created {len(expenses)} expenses")
    return expenses


def create_comments(expenses, users):
    """Create comments on expenses."""
    comments = []
    print("Creating comments on expenses...")

    for expense in expenses:
        # 30% of expenses have comments
        if random.random() < 0.3:
            # Get group members who can comment
            group = expense.group
            commenters = list(group.members)

            # 1-5 comments per expense
            num_comments = random.randint(1, 5)

            for _ in range(num_comments):
                commenter = random.choice(commenters)
                comment_text = random.choice(COMMENT_TEXTS)

                # Random date after expense creation
                days_after = random.randint(0, 30)
                created_at = expense.created_at + timedelta(days=days_after)

                comment = Comment(
                    expense_id=expense.id,
                    user_id=commenter.id,
                    content=comment_text,
                    created_at=created_at,
                )
                db.session.add(comment)
                comments.append(comment)

    db.session.commit()
    print(f"✓ Created {len(comments)} comments")
    return comments


def create_settlements(users, expenses):
    """Create settlements between users."""
    settlements = []
    print("Creating settlements...")

    # Calculate balances to create realistic settlements
    from services.expense_service import ExpenseService

    balance_data = ExpenseService.calculate_balances(expenses)
    balances = balance_data["balances"]

    # Create settlements for users who owe money
    settlement_count = 0
    max_settlements = 30

    for debtor_email, balance in balances.items():
        if balance >= -0.01 or settlement_count >= max_settlements:
            continue  # Skip if they don't owe or we've created enough

        # Find debtor user
        debtor = User.query.filter_by(email=debtor_email).first()
        if not debtor:
            continue

        # Find creditors (users this debtor owes)
        detailed_breakdown = ExpenseService.calculate_detailed_breakdown(expenses)
        creditors = {}
        for debt in detailed_breakdown:
            if debt["from"] == debtor_email:
                creditor_email = debt["to"]
                if creditor_email not in creditors:
                    creditors[creditor_email] = 0.0
                creditors[creditor_email] += debt["amount"]

        # Create 1-3 settlements per debtor
        num_settlements = random.randint(1, min(3, len(creditors)))

        for creditor_email, owed_amount in list(creditors.items())[:num_settlements]:
            if settlement_count >= max_settlements:
                break

            creditor = User.query.filter_by(email=creditor_email).first()
            if not creditor:
                continue

            # Settlement amount (partial or full)
            if random.random() < 0.7:  # 70% partial payments
                settlement_amount = round(random.uniform(0.1, 0.9) * owed_amount, 2)
            else:  # 30% full payments
                settlement_amount = round(owed_amount, 2)

            # Random note
            notes = [
                "Payment via Venmo",
                "Cash payment",
                "Bank transfer",
                "PayPal payment",
                "Settled up!",
                "Thanks!",
                None,
            ]
            note = random.choice(notes)

            # Random date within last 3 months
            days_ago = random.randint(0, 90)
            created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

            settlement = Settlement(
                amount=settlement_amount,
                payer_id=debtor.id,
                recipient_id=creditor.id,
                note=note,
                created_at=created_at,
            )
            db.session.add(settlement)
            settlements.append(settlement)
            settlement_count += 1

    db.session.commit()
    print(f"✓ Created {len(settlements)} settlements")
    return settlements


def create_announcements(groups, users):
    """Create announcements for groups."""
    announcements = []
    print("Creating announcements...")

    for group in groups:
        # 2-8 announcements per group
        num_announcements = random.randint(2, 8)

        for _ in range(num_announcements):
            author = random.choice(list(group.members))
            content = random.choice(ANNOUNCEMENT_TEXTS)

            # 20% are pinned
            is_pinned = random.random() < 0.2

            # Random date within last 2 months
            days_ago = random.randint(0, 60)
            created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

            # Some announcements are updated
            updated_at = None
            if random.random() < 0.3:  # 30% are updated
                days_after = random.randint(1, 30)
                updated_at = created_at + timedelta(days=days_after)

            announcement = Announcement(
                group_id=group.id,
                author_id=author.id,
                content=content,
                is_pinned=is_pinned,
                created_at=created_at,
                updated_at=updated_at,
            )
            db.session.add(announcement)
            announcements.append(announcement)

    db.session.commit()
    print(f"✓ Created {len(announcements)} announcements")
    return announcements


def create_notifications(groups, expenses):
    """Create group notifications for expense deletions and edits."""
    notifications = []
    print("Creating group notifications...")

    # Create notifications for some deleted expenses (simulate)
    deleted_count = 0
    for group in groups:
        group_expenses = [e for e in expenses if e.group_id == group.id]
        if not group_expenses:
            continue

        # 10% of expenses have deletion notifications
        num_deletions = max(1, len(group_expenses) // 10)

        for _ in range(min(num_deletions, len(group_expenses))):
            expense = random.choice(group_expenses)
            deleter = random.choice(list(group.members))

            days_ago = random.randint(0, 60)
            created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

            # Random read_by (some users have read it)
            read_by = []
            if random.random() < 0.5:  # 50% chance some users read it
                num_readers = random.randint(1, len(group.members) - 1)
                readers = random.sample(list(group.members), num_readers)
                read_by = [r.id for r in readers]

            notification = GroupNotification(
                group_id=group.id,
                notification_type="expense_deleted",
                description=expense.description,
                amount=expense.amount,
                payer=expense.payer,
                deleted_by=deleter.display_name or deleter.email,
                created_at=created_at,
                read_by=json.dumps(read_by),
            )
            db.session.add(notification)
            notifications.append(notification)
            deleted_count += 1

        # Create notifications for some edited expenses
        num_edits = max(1, len(group_expenses) // 15)

        for _ in range(min(num_edits, len(group_expenses))):
            expense = random.choice(group_expenses)
            editor = random.choice(list(group.members))

            days_ago = random.randint(0, 60)
            created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)

            # Random read_by
            read_by = []
            if random.random() < 0.5:
                num_readers = random.randint(1, len(group.members) - 1)
                readers = random.sample(list(group.members), num_readers)
                read_by = [r.id for r in readers]

            notification = GroupNotification(
                group_id=group.id,
                notification_type="expense_edited",
                description=expense.description,
                amount=expense.amount,
                payer=expense.payer,
                edited_by=editor.display_name or editor.email,
                created_at=created_at,
                read_by=json.dumps(read_by),
            )
            db.session.add(notification)
            notifications.append(notification)

    db.session.commit()
    print(f"✓ Created {len(notifications)} notifications")
    return notifications


def calculate_points_for_all_groups(groups):
    """Calculate points for all groups."""
    print("Calculating points for all groups...")
    for group in groups:
        try:
            PointsService.calculate_points_for_group(group.id)
        except Exception as e:
            print(f"Warning: Failed to calculate points for group {group.id}: {e}")
    print("✓ Points calculated for all groups")


def main():
    """Main seed function."""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("SprintPay Database Seeding Script")
        print("=" * 60)
        print()

        # Initialize database tables first
        print("Initializing database tables...")
        db.create_all()
        print("✓ Database tables initialized")
        print()

        # Clear existing data (optional - comment out if you want to keep existing data)
        print("Clearing existing data...")
        try:
            # Delete in reverse order of dependencies to avoid foreign key issues
            db.session.query(UserGroupPoints).delete()
            db.session.query(Comment).delete()
            db.session.query(Announcement).delete()
            db.session.query(GroupNotification).delete()
            db.session.query(Settlement).delete()
            db.session.query(Expense).delete()
            db.session.query(GroupInvitation).delete()
            db.session.query(Group).delete()
            db.session.query(User).delete()
            db.session.commit()
            print("✓ Database cleared")
        except Exception as e:
            # If tables don't exist or are empty, that's fine
            db.session.rollback()
            print(f"✓ Database cleared (or was already empty)")
        print()

        # Create data
        users = create_users(num_users=25)
        groups = create_groups(users, num_groups=15)
        invitations = create_invitations(users, groups)
        expenses = create_expenses(groups, num_expenses_per_group=15)
        comments = create_comments(expenses, users)
        settlements = create_settlements(users, expenses)
        announcements = create_announcements(groups, users)
        notifications = create_notifications(groups, expenses)
        calculate_points_for_all_groups(groups)

        print()
        print("=" * 60)
        print("Seeding Complete!")
        print("=" * 60)
        print(f"Users: {len(users)}")
        print(f"Groups: {len(groups)}")
        print(f"Invitations: {len(invitations)}")
        print(f"Expenses: {len(expenses)}")
        print(f"Comments: {len(comments)}")
        print(f"Settlements: {len(settlements)}")
        print(f"Announcements: {len(announcements)}")
        print(f"Notifications: {len(notifications)}")
        print()
        print("You can now test all features of the application!")
        print("=" * 60)


if __name__ == "__main__":
    main()

