"""Test script for weekly summary with custom date range."""

from datetime import datetime, timedelta, timezone
from app import create_app
from services.group_activity_service import GroupActivityService
from services.notification_service import send_group_activity_summary

app = create_app()

with app.app_context():
    print("\n" + "="*60)
    print("Testing Weekly Summary with Custom Date Range")
    print("="*60 + "\n")
    
    # Get all groups
    groups = GroupActivityService.get_all_active_groups()
    print(f"Found {len(groups)} active group(s)\n")
    
    if not groups:
        print("❌ No groups found. Create a group first!")
        exit(1)
    
    # Test with last 30 days instead of 7
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
    
    for group in groups:
        print(f"Group: {group.name}")
        
        # Get activity
        activity = GroupActivityService.get_weekly_activity(
            group.id, 
            start_date, 
            end_date
        )
        
        print(f"  Expenses: {len(activity['expenses'])}")
        print(f"  Settlements: {len(activity['settlements'])}")
        print(f"  Has activity: {activity['has_activity']}")
        
        if activity['has_activity']:
            # Format and send
            summary = GroupActivityService.format_activity_summary(activity)
            
            print(f"\n  Sending to {len(group.members)} member(s):")
            for member in group.members:
                send_group_activity_summary(member, summary)
                print(f"    ✓ Sent to {member.email}")
        else:
            print("  ⚠️  No activity found\n")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60 + "\n")
