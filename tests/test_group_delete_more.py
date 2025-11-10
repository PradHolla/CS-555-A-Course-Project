"""Additional tests to raise coverage for group routes."""

from models import Group, User


def test_delete_group_non_member_blocked(client, app):
    """Ensure a non-member cannot delete a group."""
    from extensions import db

    creator = User(email="c_nonmember@example.com")
    outsider = User(email="outsider@example.com")
    db.session.add_all([creator, outsider])
    db.session.commit()

    group = Group(name="NoDeleteGroup", created_by_id=creator.id)
    group.members.append(creator)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = outsider.id
        sess["user_email"] = outsider.email

    resp = client.post(f"/groups/{group.id}/delete", follow_redirects=True)
    # Should not delete
    assert db.session.get(Group, group.id) is not None
    assert resp.status_code == 200 or resp.status_code == 302


def test_delete_group_not_found_shows_error(client, app):
    """Posting delete for non-existent group should flash Group not found."""
    from extensions import db

    user = User(email="u_notfound@example.com")
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_email"] = user.email

    resp = client.post("/groups/999999/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Group not found" in resp.data


def test_delete_group_user_missing_defensive(client, app):
    """If the logged-in user is removed from DB mid-session, the delete should be handled gracefully."""
    from extensions import db

    creator = User(email="u_goner@example.com")
    db.session.add(creator)
    db.session.commit()

    group = Group(name="GonerGroup", created_by_id=creator.id)
    group.members.append(creator)
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = creator.id
        sess["user_email"] = creator.email
        # simulate deletion mid-session
        db.session.delete(creator)
        db.session.flush()

    resp = client.post(f"/groups/{group.id}/delete", follow_redirects=True)
    # login_required or defensive checks should redirect to login (200 page)
    assert resp.status_code == 200


def test_create_expense_notification_failure_continues(client, app, monkeypatch):
    """If notify_expense_participants raises, expense creation still succeeds."""
    from extensions import db
    from models import Expense

    payer = User(email="notif_fail_payer@example.com")
    other = User(email="notif_fail_other@example.com")
    db.session.add_all([payer, other])
    db.session.commit()

    group = Group(name="NotifFailGroup", created_by_id=payer.id)
    group.members.extend([payer, other])
    db.session.add(group)
    db.session.commit()

    # patch notification to raise
    def fake_notify(expense, participants):
        raise Exception("notify failed")

    monkeypatch.setattr("services.notification_service.notify_expense_participants", fake_notify)

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    data = {
        "description": "BrokenNotify",
        "amount": "20.00",
        "payer": payer.email,
        "split_type": "equal",
        "participants": [payer.email, other.email],
    }

    resp = client.post(f"/groups/{group.id}", data=data, follow_redirects=False)
    assert resp.status_code == 302
    expense = Expense.query.filter_by(description="BrokenNotify", group_id=group.id).first()
    assert expense is not None


def test_group_expenses_custom_split_validation(client, app):
    """Creating an expense with custom split that doesn't sum to total should be rejected."""
    from extensions import db

    payer = User(email="custom_payer@example.com")
    p2 = User(email="custom_p2@example.com")
    db.session.add_all([payer, p2])
    db.session.commit()

    group = Group(name="CustomGroup", created_by_id=payer.id)
    group.members.extend([payer, p2])
    db.session.add(group)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = payer.id
        sess["user_email"] = payer.email

    data = {
        "description": "Custom Expense",
        "amount": "50.00",
        "payer": payer.email,
        "split_type": "custom",
        f"custom_amount_{payer.email}": "10.00",
        f"custom_amount_{p2.email}": "10.00",  # total 20 != 50
    }

    resp = client.post(f"/groups/{group.id}", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"must equal total amount" in resp.data or b"must equal the total amount" in resp.data
