"""
Demo script for Payment Confirmation Email Notification feature.

This script demonstrates the email notification feature by creating
a test payment and showing the email output.

Usage:
    python demo_payment_notification.py
"""

from app import create_app
from extensions import db
from models import Settlement, User


def demo_payment_notification():
    """Demonstrate the payment notification feature."""
    app = create_app()
    
    with app.app_context():
        with app.test_request_context():
            # Create test database
            db.create_all()
            
            # Create test users
            print("\n" + "=" * 60)
            print("Creating test users...")
            print("=" * 60)
            
            payer = User(email="neha@example.com", display_name="Neha")
            recipient = User(email="john@example.com", display_name="John")
            
            db.session.add_all([payer, recipient])
            db.session.commit()
            
            print(f"✓ Created payer: {payer.display_name} ({payer.email})")
            print(f"✓ Created recipient: {recipient.display_name} ({recipient.email})")
            
            # Create a settlement
            print("\n" + "=" * 60)
            print("Creating payment settlement...")
            print("=" * 60)
            
            settlement = Settlement(
                amount=500.00,
                payer_id=payer.id,
                recipient_id=recipient.id,
                note="Rent payment for November"
            )
            
            db.session.add(settlement)
            db.session.commit()
            
            print(f"✓ Created settlement: ${settlement.amount:.2f}")
            print(f"  From: {payer.display_name}")
            print(f"  To: {recipient.display_name}")
            print(f"  Note: {settlement.note}")
            
            # Send notification
            print("\n" + "=" * 60)
            print("Sending email notification...")
            print("=" * 60)
            print(f"EMAIL_ENABLED = {app.config.get('EMAIL_ENABLED', False)}")
            print()
            
            from services.notification_service import notify_settlement_recipient
            
            notify_settlement_recipient(settlement)
            
            print("\n" + "=" * 60)
            print("Demo completed!")
            print("=" * 60)
            print("\nTo enable actual email sending:")
            print("1. Set EMAIL_ENABLED=true in your .env file")
            print("2. Configure MAIL_USERNAME and MAIL_PASSWORD")
            print("3. Run the demo again")
            print()


if __name__ == "__main__":
    demo_payment_notification()
