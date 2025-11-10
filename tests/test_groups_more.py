"""Additional tests to increase coverage for routes/groups.py.

These tests exercise leave_group, notifications read, expense deletion/edit flows,
comment CRUD and custom-split validation branches.
"""

from extensions import db
from models import Comment, Expense, Group, GroupNotification, User


def test_leave_group_creator_cannot_leave(client, app):
    creator = User(email="leave_creator@example.com")
    db.session.add(creator)
    db.session.commit()

    group = Group(name="LeaveGroup", created_by_id=creator.id)
    group.members.append(creator)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email

    resp = client.post(f"/groups/{group.id}/leave", follow_redirects=True)
    assert resp.status_code == 200
    # The route flashes a message that the creator cannot leave
    assert b"The group creator cannot leave the group" in resp.data
    assert db.session.get(Group, group.id) is not None


def test_mark_notification_read_marks_user(client, app):
    # Create creator + member and a notification
    creator = User(email="n_creator@example.com")
    member = User(email="n_member@example.com")
    db.session.add_all([creator, member])
    db.session.commit()

    group = Group(name="NotifyGroup", created_by_id=creator.id)
    group.members.extend([creator, member])
    db.session.add(group)
    db.session.commit()

    note = GroupNotification(
        group_id=group.id, notification_type="expense_deleted", description="x", read_by="[]"
    )
    db.session.add(note)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = member.id
        sess["user_email"] = member.email

    resp = client.post(f"/groups/{group.id}/notification/{note.id}/read", follow_redirects=False)
    assert resp.status_code in (302, 303, 307)

    # reload and check read_by contains member.id
    refreshed = db.session.get(GroupNotification, note.id)
    import json

    read_by = json.loads(refreshed.read_by)
    assert member.id in read_by


def test_delete_expense_creates_notification_and_removes_expense(client, app):
    creator = User(email="d_creator@example.com")
    member = User(email="d_member@example.com")
    db.session.add_all([creator, member])
    db.session.commit()

    group = Group(name="DGroup", created_by_id=creator.id)
    group.members.extend([creator, member])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="ToDelete",
        amount=5.0,
        payer=creator.email,
        group_id=group.id,
        split_type="equal",
        split_details='{"d_creator@example.com":5.0}',
        participants=creator.email,
    )
    db.session.add(expense)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email

    resp = client.post(f"/groups/{group.id}/expense/{expense.id}/delete", follow_redirects=False)
    assert resp.status_code in (302, 303, 307)

    # expense removed
    assert db.session.get(Expense, expense.id) is None

    # a GroupNotification should have been created
    gn = GroupNotification.query.filter_by(
        group_id=group.id, notification_type="expense_deleted"
    ).first()
    assert gn is not None


def test_comment_crud(client, app):
    creator = User(email="c_creator@example.com")
    db.session.add(creator)
    db.session.commit()

    group = Group(name="CGroup", created_by_id=creator.id)
    group.members.append(creator)
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="CExpense",
        amount=7.0,
        payer=creator.email,
        group_id=group.id,
        split_type="equal",
        split_details='{"c_creator@example.com":7.0}',
        participants=creator.email,
    )
    db.session.add(expense)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email

    # create comment
    resp = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment",
        data={"content": "Nice"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303, 307)
    comment = Comment.query.filter_by(expense_id=expense.id).first()
    assert comment is not None

    # edit comment
    resp = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/{comment.id}/edit",
        data={"content": "Updated"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303, 307)
    refreshed = db.session.get(Comment, comment.id)
    assert refreshed.content == "Updated"

    # delete comment
    resp = client.post(
        f"/groups/{group.id}/expense/{expense.id}/comment/{comment.id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303, 307)
    assert db.session.get(Comment, comment.id) is None


def test_edit_expense_creates_notification_and_updates(client, app):
    payer = User(email="e_payer@example.com")
    p2 = User(email="e_p2@example.com")
    db.session.add_all([payer, p2])
    db.session.commit()

    group = Group(name="EGroup", created_by_id=payer.id)
    group.members.extend([payer, p2])
    db.session.add(group)
    db.session.commit()

    expense = Expense(
        description="Old",
        amount=20.0,
        payer=payer.email,
        group_id=group.id,
        split_type="equal",
        split_details='{"e_payer@example.com":20.0}',
        participants=payer.email,
    )
    db.session.add(expense)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    data = {
        "description": "NewDesc",
        "amount": "30.00",
        "payer": payer.email,
        "split_type": "equal",
        # send participants as list
        "participants": [payer.email, p2.email],
    }

    resp = client.post(
        f"/groups/{group.id}/expense/{expense.id}/edit", data=data, follow_redirects=False
    )
    assert resp.status_code in (302, 303, 307)

    updated = db.session.get(Expense, expense.id)
    assert updated.description == "NewDesc"

    gn = GroupNotification.query.filter_by(
        group_id=group.id, notification_type="expense_edited"
    ).first()
    assert gn is not None


def test_group_expenses_custom_split_validation(client, app):
    payer = User(email="cust_payer@example.com")
    p2 = User(email="cust_p2@example.com")
    db.session.add_all([payer, p2])
    db.session.commit()

    group = Group(name="CustGroup", created_by_id=payer.id)
    group.members.extend([payer, p2])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    # invalid custom amounts (non-numeric)
    bad_data = {
        "description": "BadCustom",
        "amount": "50",
        "payer": payer.email,
        "split_type": "custom",
        f"custom_amount_{payer.email}": "abc",
    }
    resp = client.post(f"/groups/{group.id}", data=bad_data, follow_redirects=True)
    assert resp.status_code == 200
    assert (
        b"Invalid amount" in resp.data
        or b"Please specify amounts for at least one participant" in resp.data
    )

    # valid custom split
    good_data = {
        "description": "GoodCustom",
        "amount": "100",
        "payer": payer.email,
        "split_type": "custom",
        f"custom_amount_{payer.email}": "60",
        f"custom_amount_{p2.email}": "40",
    }

    resp = client.post(f"/groups/{group.id}", data=good_data, follow_redirects=False)
    assert resp.status_code in (302, 303, 307)
    exp = Expense.query.filter_by(description="GoodCustom", group_id=group.id).first()
    assert exp is not None
