from flask import Blueprint, render_template, request, redirect, url_for
from utils.decorators import login_required
from models import Group
from extensions import db

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')

@groups_bp.route('/')
@login_required
def list_groups():
    """Display all groups."""
    groups = Group.query.all()
    return render_template('groups/index.html', groups=groups)

@groups_bp.route('/create', methods=['POST'])
@login_required
def create_group():
    """Create a new group."""
    name = request.form.get('name')
    members = request.form.get('members')
    group = Group(name=name, members=members)
    db.session.add(group)
    db.session.commit()
    return redirect(url_for('groups.list_groups'))
