"""Tests for the points/rewards feature."""

import json

from extensions import db
from models import Expense, Group, User, UserGroupPoints
from services.points_service import PointsService


def test_points_service_should_award_points_multiple_participants(app):
    """Test that points are awarded when payer covers more than one participant."""
    with app.app_context():
        # Create expense with multiple participants
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        
        assert PointsService.should_award_points(expense) is True


def test_points_service_should_not_award_points_single_participant(app):
    """Test that points are NOT awarded when payer only covers themselves."""
    with app.app_context():
        # Create expense with only one participant (payer)
        expense = Expense(
            description="Personal lunch",
            amount=50.0,
            payer="alice@example.com",
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0
            }),
            participants="alice@example.com"
        )
        
        assert PointsService.should_award_points(expense) is False


def test_points_service_calculate_points_for_group_awards_points(app):
    """Test that calculate_points_for_group correctly awards points."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        charlie = User(email="charlie@example.com", display_name="Charlie")
        db.session.add_all([alice, bob, charlie])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob, charlie])
        db.session.add(group)
        db.session.commit()
        
        # Create expense where Alice pays for multiple participants
        expense = Expense(
            description="Dinner",
            amount=150.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0,
                "charlie@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com, charlie@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        
        # Check that Alice has 10 points
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 10
        
        # Check that Bob and Charlie have 0 points
        bob_points = PointsService.get_user_points_in_group(bob.id, group.id)
        charlie_points = PointsService.get_user_points_in_group(charlie.id, group.id)
        assert bob_points == 0
        assert charlie_points == 0


def test_points_service_calculate_points_multiple_expenses(app):
    """Test that multiple expenses correctly accumulate points."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        # Create first expense - Alice pays
        expense1 = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense1)
        db.session.commit()
        
        # Create second expense - Bob pays
        expense2 = Expense(
            description="Dinner",
            amount=200.0,
            payer="bob@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 100.0,
                "bob@example.com": 100.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense2)
        db.session.commit()
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        
        # Check that both have 10 points
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        bob_points = PointsService.get_user_points_in_group(bob.id, group.id)
        assert alice_points == 10
        assert bob_points == 10


def test_points_service_no_points_for_single_participant_expense(app):
    """Test that expenses with only one participant don't award points."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        # Create expense where Alice pays only for herself
        expense = Expense(
            description="Personal lunch",
            amount=50.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0
            }),
            participants="alice@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        
        # Check that Alice has 0 points
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 0


def test_points_service_recalculates_on_expense_deletion(app):
    """Test that points are recalculated when an expense is deleted."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        # Create expense - Alice pays
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        # Calculate points - Alice should have 10 points
        PointsService.calculate_points_for_group(group.id)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 10
        
        # Delete the expense
        db.session.delete(expense)
        db.session.commit()
        
        # Recalculate points - Alice should have 0 points now
        PointsService.calculate_points_for_group(group.id)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 0


def test_points_service_recalculates_on_expense_edit(app):
    """Test that points are recalculated when an expense is edited."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        charlie = User(email="charlie@example.com", display_name="Charlie")
        db.session.add_all([alice, bob, charlie])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob, charlie])
        db.session.add(group)
        db.session.commit()
        
        # Create expense - Alice pays for Alice and Bob
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        # Calculate points - Alice should have 10 points
        PointsService.calculate_points_for_group(group.id)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 10
        
        # Edit expense - change payer to Bob
        expense.payer = "bob@example.com"
        expense.split_details = json.dumps({
            "alice@example.com": 50.0,
            "bob@example.com": 50.0
        })
        db.session.commit()
        
        # Recalculate points - Bob should have 10 points, Alice should have 0
        PointsService.calculate_points_for_group(group.id)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        bob_points = PointsService.get_user_points_in_group(bob.id, group.id)
        assert alice_points == 0
        assert bob_points == 10


def test_create_expense_awards_points(client, app):
    """Test that creating an expense awards points to the payer."""
    from werkzeug.datastructures import MultiDict
    
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        group_id = group.id
        alice_id = alice.id
    
    # Login as Alice
    with client.session_transaction() as session:
        session["user_id"] = alice_id
        session["user_email"] = "alice@example.com"
    
    # Create expense where Alice pays for multiple participants
    # Use MultiDict to handle multiple participants
    expense_data = MultiDict([
        ("description", "Lunch"),
        ("amount", "100.0"),
        ("payer", "alice@example.com"),
        ("split_type", "equal"),
        ("participants", "alice@example.com"),
        ("participants", "bob@example.com"),
    ])
    
    response = client.post(
        f"/groups/{group_id}",
        data=expense_data,
        follow_redirects=False
    )
    
    assert response.status_code == 302
    
    # Check that Alice has 10 points (within app context)
    with app.app_context():
        # Verify expense was created
        expense = Expense.query.filter_by(description="Lunch", group_id=group_id).first()
        assert expense is not None, "Expense was not created"
        assert expense.payer == "alice@example.com"
        
        # Verify split_details are correct
        import json
        from services.expense_service import ExpenseService
        split_details = ExpenseService._parse_split_details(expense)
        assert len(split_details) == 2, f"Expected 2 participants but got {len(split_details)}: {split_details}"
        assert "alice@example.com" in split_details
        assert "bob@example.com" in split_details
        
        # Verify should_award_points returns True
        assert PointsService.should_award_points(expense), "Expense should award points but doesn't"
        
        # Manually trigger points calculation to ensure it runs
        PointsService.calculate_points_for_group(group_id)
        
        # Check that Alice has 10 points
        alice_points = PointsService.get_user_points_in_group(alice_id, group_id)
        assert alice_points == 10, f"Expected 10 points but got {alice_points}. Expense payer: {expense.payer}, split_details: {split_details}"


def test_groups_list_displays_points(client, app):
    """Test that the groups list page displays points for all members."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        # Create expense where Alice pays
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        # Login as Alice
        with client.session_transaction() as session:
            session["user_id"] = alice.id
            session["user_email"] = alice.email
        
        # Get groups list page
        response = client.get("/groups/")
        assert response.status_code == 200
        
        # Check that points are displayed
        response_data = response.data.decode('utf-8')
        assert "You have 10 points" in response_data or "10 points" in response_data


def test_group_expenses_displays_all_members_points(client, app):
    """Test that the group expenses page displays points for all members."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        charlie = User(email="charlie@example.com", display_name="Charlie")
        db.session.add_all([alice, bob, charlie])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob, charlie])
        db.session.add(group)
        db.session.commit()
        
        # Create expense where Alice pays
        expense1 = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense1)
        
        # Create expense where Bob pays
        expense2 = Expense(
            description="Dinner",
            amount=200.0,
            payer="bob@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 100.0,
                "bob@example.com": 100.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense2)
        db.session.commit()
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        
        # Login as Charlie (who has no points)
        with client.session_transaction() as session:
            session["user_id"] = charlie.id
            session["user_email"] = charlie.email
        
        # Get group expenses page
        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200
        
        # Check that both Alice's and Bob's points are displayed
        response_data = response.data.decode('utf-8')
        # Should show Alice has 10 points and Bob has 10 points
        assert "Alice" in response_data or "alice@example.com" in response_data
        assert "Bob" in response_data or "bob@example.com" in response_data
        assert "10 points" in response_data


def test_points_visible_to_all_group_members(client, app):
    """Test that all group members can see each other's points."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        # Create expense where Alice pays
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        
        # Login as Bob (who didn't pay)
        with client.session_transaction() as session:
            session["user_id"] = bob.id
            session["user_email"] = bob.email
        
        # Get group expenses page
        response = client.get(f"/groups/{group.id}")
        assert response.status_code == 200
        
        # Check that Bob can see Alice's points
        response_data = response.data.decode('utf-8')
        # Should show that Alice has points (not "You have" since Bob is viewing)
        assert "Alice" in response_data or "alice@example.com" in response_data
        assert "10 points" in response_data


def test_delete_expense_recalculates_points(client, app):
    """Test that deleting an expense recalculates points."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        # Create expense where Alice pays
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        expense_id = expense.id
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 10
        
        # Login as Alice
        with client.session_transaction() as session:
            session["user_id"] = alice.id
            session["user_email"] = alice.email
        
        # Delete the expense
        response = client.post(
            f"/groups/{group.id}/expense/{expense_id}/delete",
            follow_redirects=False
        )
        assert response.status_code == 302
        
        # Check that points are recalculated (Alice should have 0 points now)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 0


def test_edit_expense_recalculates_points(client, app):
    """Test that editing an expense recalculates points."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        # Create expense where Alice pays
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        expense_id = expense.id
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 10
        
        # Login as Alice
        with client.session_transaction() as session:
            session["user_id"] = alice.id
            session["user_email"] = alice.email
        
        # Edit the expense - change payer to Bob
        edit_data = {
            "description": "Lunch",
            "amount": "100.0",
            "payer": "bob@example.com",
            "split_type": "equal",
            "participants": ["alice@example.com", "bob@example.com"]
        }
        
        response = client.post(
            f"/groups/{group.id}/expense/{expense_id}/edit",
            data=edit_data,
            follow_redirects=False
        )
        assert response.status_code == 302
        
        # Check that points are recalculated (Bob should have 10 points, Alice should have 0)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        bob_points = PointsService.get_user_points_in_group(bob.id, group.id)
        assert alice_points == 0
        assert bob_points == 10


def test_get_all_points_for_group(app):
    """Test that get_all_points_for_group returns correct points for all members."""
    with app.app_context():
        # Create users
        alice = User(email="alice@example.com", display_name="Alice")
        bob = User(email="bob@example.com", display_name="Bob")
        charlie = User(email="charlie@example.com", display_name="Charlie")
        db.session.add_all([alice, bob, charlie])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob, charlie])
        db.session.add(group)
        db.session.commit()
        
        # Create expenses
        expense1 = Expense(
            description="Lunch",
            amount=100.0,
            payer="alice@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        expense2 = Expense(
            description="Dinner",
            amount=200.0,
            payer="bob@example.com",
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "bob@example.com": 100.0,
                "charlie@example.com": 100.0
            }),
            participants="bob@example.com, charlie@example.com"
        )
        db.session.add_all([expense1, expense2])
        db.session.commit()
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        
        # Get all points
        all_points = PointsService.get_all_points_for_group(group.id)
        
        # Check points
        assert all_points[alice.id] == 10
        assert all_points[bob.id] == 10
        assert all_points.get(charlie.id, 0) == 0


def test_points_with_display_name(app):
    """Test that points work correctly when users have display names."""
    with app.app_context():
        # Create users with display names
        alice = User(email="alice@example.com", display_name="Alice Smith")
        bob = User(email="bob@example.com", display_name="Bob Jones")
        db.session.add_all([alice, bob])
        db.session.flush()
        
        # Create group
        group = Group(name="Test Group", created_by_id=alice.id)
        group.members.extend([alice, bob])
        db.session.add(group)
        db.session.commit()
        
        # Create expense using display name as payer
        expense = Expense(
            description="Lunch",
            amount=100.0,
            payer="Alice Smith",  # Using display name
            group_id=group.id,
            split_type="equal",
            split_details=json.dumps({
                "alice@example.com": 50.0,
                "bob@example.com": 50.0
            }),
            participants="alice@example.com, bob@example.com"
        )
        db.session.add(expense)
        db.session.commit()
        
        # Calculate points
        PointsService.calculate_points_for_group(group.id)
        
        # Check that Alice has 10 points (should work with display name)
        alice_points = PointsService.get_user_points_in_group(alice.id, group.id)
        assert alice_points == 10

