"""Tests for comment functionality on expenses."""

from extensions import db
from models import Comment, Expense, Group, User


def test_comment_model_creation(app):
    """Test that Comment model can be created."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    expense = Expense(
        description="Test Expense",
        amount=100.0,
        payer="user@example.com",
        group_id=1,
        split_type="equal",
        split_details='{"user@example.com": 100.0}',
    )
    db.session.add(expense)
    db.session.commit()

    # Act
    comment = Comment(
        expense_id=expense.id,
        user_id=user.id,
        content="Test comment",
    )
    db.session.add(comment)
    db.session.commit()

    # Assert
    stored = Comment.query.first()
    assert stored is not None
    assert stored.content == "Test comment"
    assert stored.expense_id == expense.id
    assert stored.user_id == user.id


def test_create_comment_success(client, app):
    """Test creating a comment on an expense."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment",
        data={"content": "Great lunch!"},
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 302
    comment = Comment.query.filter_by(expense_id=expense.id).first()
    assert comment is not None
    assert comment.content == "Great lunch!"
    assert comment.user_id == user.id


def test_create_comment_empty_content(client, app):
    """Test that creating comment with empty content fails."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment",
        data={"content": ""},
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Comment cannot be empty" in response.data
    comment = Comment.query.filter_by(expense_id=expense.id).first()
    assert comment is None


def test_edit_comment_success(client, app):
    """Test editing own comment."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    comment = Comment(
        expense_id=expense.id,
        user_id=user.id,
        content="Original comment",
    )
    db.session.add(comment)
    db.session.commit()
    comment_id = comment.id

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/{comment_id}/edit",
        data={"content": "Updated comment"},
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 302
    updated_comment = db.session.get(Comment, comment_id)
    assert updated_comment.content == "Updated comment"


def test_edit_comment_not_owner(client, app):
    """Test that editing someone else's comment fails."""
    # Arrange
    owner = User(email="owner@example.com")
    editor = User(email="editor@example.com")
    db.session.add_all([owner, editor])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=owner.id)
    group.members.extend([owner, editor])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="owner@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"owner@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    comment = Comment(
        expense_id=expense.id,
        user_id=owner.id,
        content="Owner's comment",
    )
    db.session.add(comment)
    db.session.commit()
    comment_id = comment.id

    with client.session_transaction() as sess:
        sess["user_id"] = editor.id
        sess["user_email"] = editor.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/{comment_id}/edit",
        data={"content": "Hacked comment"},
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"You can only edit your own comments" in response.data
    comment = db.session.get(Comment, comment_id)
    assert comment.content == "Owner's comment"  # Unchanged


def test_delete_comment_success(client, app):
    """Test deleting own comment."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    comment = Comment(
        expense_id=expense.id,
        user_id=user.id,
        content="To be deleted",
    )
    db.session.add(comment)
    db.session.commit()
    comment_id = comment.id

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/{comment_id}/delete",
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 302
    deleted_comment = db.session.get(Comment, comment_id)
    assert deleted_comment is None


def test_delete_comment_not_owner(client, app):
    """Test that deleting someone else's comment fails."""
    # Arrange
    owner = User(email="owner@example.com")
    deleter = User(email="deleter@example.com")
    db.session.add_all([owner, deleter])
    db.session.commit()

    group = Group(name="Test Group", created_by_id=owner.id)
    group.members.extend([owner, deleter])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="owner@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"owner@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    comment = Comment(
        expense_id=expense.id,
        user_id=owner.id,
        content="Owner's comment",
    )
    db.session.add(comment)
    db.session.commit()
    comment_id = comment.id

    with client.session_transaction() as sess:
        sess["user_id"] = deleter.id
        sess["user_email"] = deleter.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/{comment_id}/delete",
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"You can only delete your own comments" in response.data
    comment = db.session.get(Comment, comment_id)
    assert comment is not None  # Still exists


def test_expense_detail_with_comments(client, app):
    """Test viewing expense detail page with comments."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    comment1 = Comment(
        expense_id=expense.id,
        user_id=user.id,
        content="First comment",
    )
    comment2 = Comment(
        expense_id=expense.id,
        user_id=user.id,
        content="Second comment",
    )
    db.session.add_all([comment1, comment2])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.get(f"/groups/{group.id}/expense/{expense.id}")

    # Assert
    assert response.status_code == 200
    assert b"Lunch" in response.data
    assert b"First comment" in response.data
    assert b"Second comment" in response.data


def test_expense_list_shows_comment_count(client, app):
    """Test that expense list shows comment count badge."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense1 = Expense(
        description="Expense with comments",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    expense2 = Expense(
        description="Expense without comments",
        amount=30.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 30.0}',
    )
    db.session.add_all([expense1, expense2])
    db.session.commit()

    # Add 2 comments to expense1
    comment1 = Comment(expense_id=expense1.id, user_id=user.id, content="Comment 1")
    comment2 = Comment(expense_id=expense1.id, user_id=user.id, content="Comment 2")
    db.session.add_all([comment1, comment2])
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.get(f"/groups/{group.id}")

    # Assert
    assert response.status_code == 200
    assert b"2 comments" in response.data
    assert b"Expense with comments" in response.data
    assert b"Expense without comments" in response.data
    # Should show comment badge only for expense with comments
    # Count occurrences of "X comments" pattern (not just "comments" word)
    import re
    comment_badge_pattern = rb'\d+\s+comments?'
    matches = re.findall(comment_badge_pattern, response.data)
    assert len(matches) == 1  # Only one expense has comments


def test_create_comment_requires_login(client, app):
    """Test that unauthenticated users cannot create comments."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    # Act - no session set
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment",
        data={"content": "Test comment"},
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    # Should redirect to login or show error
    comment = Comment.query.filter_by(expense_id=expense.id).first()
    assert comment is None


def test_edit_comment_empty_content(client, app):
    """Test that editing comment with empty content fails."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    comment = Comment(
        expense_id=expense.id,
        user_id=user.id,
        content="Original comment",
    )
    db.session.add(comment)
    db.session.commit()
    comment_id = comment.id

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/{comment_id}/edit",
        data={"content": ""},
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Comment cannot be empty" in response.data
    comment = db.session.get(Comment, comment_id)
    assert comment.content == "Original comment"  # Unchanged


def test_edit_comment_not_found(client, app):
    """Test editing non-existent comment."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act - try to edit non-existent comment
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/99999/edit",
        data={"content": "Updated"},
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Comment not found" in response.data


def test_delete_comment_not_found(client, app):
    """Test deleting non-existent comment."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act - try to delete non-existent comment
    response = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/99999/delete",
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Comment not found" in response.data


def test_create_comment_expense_not_found(client, app):
    """Test creating comment on non-existent expense."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act
    response = client.post(
        f"/groups/{group.id}/expense/99999/comment",
        data={"content": "Test comment"},
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Expense not found" in response.data


def test_edit_comment_wrong_expense(client, app):
    """Test editing comment that belongs to different expense."""
    # Arrange
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()

    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    expense1 = Expense(
        description="Expense 1",
        amount=50.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    expense2 = Expense(
        description="Expense 2",
        amount=30.0,
        payer="user@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user@example.com": 30.0}',
    )
    db.session.add_all([expense1, expense2])
    db.session.commit()

    comment = Comment(
        expense_id=expense1.id,
        user_id=user.id,
        content="Comment on expense 1",
    )
    db.session.add(comment)
    db.session.commit()
    comment_id = comment.id

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    # Act - try to edit comment via wrong expense ID
    response = client.post(
        f"/groups/{group.id}/expense/{expense2.id}/comment/{comment_id}/edit",
        data={"content": "Hacked"},
        follow_redirects=True,
    )

    # Assert
    assert response.status_code == 200
    assert b"Comment does not belong to this expense" in response.data


def test_expense_detail_group_not_found(client, app):
    """Test expense_detail handles group not found error."""
    # Arrange
    from extensions import db
    
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()
    
    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=99999,  # Non-existent group
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email
    
    # Act
    response = client.get(f"/groups/99999/expense/{expense.id}", follow_redirects=True)
    
    # Assert
    assert response.status_code == 200
    assert b"Group not found" in response.data


def test_expense_detail_not_member(client, app):
    """Test expense_detail requires group membership."""
    # Arrange
    from extensions import db
    
    user1 = User(email="user1@example.com")
    user2 = User(email="user2@example.com")
    db.session.add_all([user1, user2])
    db.session.commit()
    
    group = Group(name="Test Group", created_by_id=user1.id)
    group.members.append(user1)  # user2 is not a member
    db.session.add(group)
    db.session.commit()
    
    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user1@example.com",
        group_id=group.id,
        split_type="equal",
        split_details='{"user1@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess["user_id"] = user2.id
        sess["user_email"] = user2.email
    
    # Act
    response = client.get(f"/groups/{group.id}/expense/{expense.id}", follow_redirects=True)
    
    # Assert
    assert response.status_code == 200
    assert b"You are not a member of this group" in response.data


def test_expense_detail_expense_not_found(client, app):
    """Test expense_detail handles expense not found error."""
    # Arrange
    from extensions import db
    
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()
    
    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email
    
    # Act
    response = client.get(f"/groups/{group.id}/expense/99999", follow_redirects=True)
    
    # Assert
    assert response.status_code == 200
    assert b"Expense not found" in response.data


def test_expense_detail_wrong_group(client, app):
    """Test expense_detail handles expense from wrong group."""
    # Arrange
    from extensions import db
    
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()
    
    group1 = Group(name="Test Group 1", created_by_id=user.id)
    group2 = Group(name="Test Group 2", created_by_id=user.id)
    group1.members.append(user)
    group2.members.append(user)
    db.session.add_all([group1, group2])
    db.session.commit()
    
    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="user@example.com",
        group_id=group1.id,  # Expense belongs to group1
        split_type="equal",
        split_details='{"user@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email
    
    # Act - try to access expense from group1 via group2 URL
    response = client.get(f"/groups/{group2.id}/expense/{expense.id}", follow_redirects=True)
    
    # Assert
    assert response.status_code == 200
    assert b"Expense does not belong to this group" in response.data


def test_expense_detail_empty_emails(client, app):
    """Test expense_detail handles expense with no emails (edge case)."""
    # Arrange
    from extensions import db
    
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()
    
    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()
    
    # Create expense with empty split_details and no comments
    # This tests the empty all_emails case (lines 483-484)
    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="",  # Empty payer
        group_id=group.id,
        split_type="equal",
        split_details='{}',  # Empty split details - no participants
    )
    db.session.add(expense)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email
    
    # Act
    response = client.get(f"/groups/{group.id}/expense/{expense.id}")
    
    # Assert
    assert response.status_code == 200
    assert b"Lunch" in response.data


def test_expense_detail_fallback_email(client, app):
    """Test expense_detail uses email as fallback when user not found."""
    # Arrange
    from extensions import db
    
    user = User(email="user@example.com")
    db.session.add(user)
    db.session.commit()
    
    group = Group(name="Test Group", created_by_id=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()
    
    # Create expense with payer email that doesn't have a user record
    expense = Expense(
        description="Lunch",
        amount=50.0,
        payer="nonexistent@example.com",  # Email without user record
        group_id=group.id,
        split_type="equal",
        split_details='{"nonexistent@example.com": 50.0}',
    )
    db.session.add(expense)
    db.session.commit()
    
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email
    
    # Act
    response = client.get(f"/groups/{group.id}/expense/{expense.id}")
    
    # Assert
    assert response.status_code == 200
    assert b"Lunch" in response.data
    # Should use email as fallback when user not found

