from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.decorators import login_required
from models import Group
from extensions import db

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')

@groups_bp.route('/')
@login_required
def list_groups():
    """Display all groups."""
    groups = Group.query.order_by(Group.created_at.desc()).all()
    return render_template('groups/index.html', groups=groups)

@groups_bp.route('/create', methods=['POST'])
@login_required
def create_group():
    """Create a new group with input validation and error handling."""
    name = request.form.get('name', '').strip()
    members = request.form.get('members', '').strip()

    # Validate inputs
    if not name or not members:
        flash('Group name and members are required.', 'error')
        return redirect(url_for('groups.list_groups')), 400

    try:
        group = Group(name=name, members=members)
        db.session.add(group)
        db.session.commit()
        flash('Group created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to create group. Please try again.', 'error')
        return redirect(url_for('groups.list_groups')), 400

    return redirect(url_for('groups.list_groups'))
