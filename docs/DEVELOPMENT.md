# 🔧 Development Guide

This guide covers development workflows, best practices, and advanced features for the Student Starter Pack.

## Development Setup

### Environment Configuration

Create a `.env` file for environment-specific settings:

```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
DEBUG=True
```

Load environment variables in `app.py`:

```python
from dotenv import load_dotenv
import os

load_dotenv()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
```

Install python-dotenv:
```bash
uv add python-dotenv
```

### Debug Mode

The app runs in debug mode by default during development:

```python
if __name__ == '__main__':
    app.run(debug=True)
```

Debug mode provides:
- Auto-reload on code changes
- Detailed error pages
- Interactive debugger in the browser

### Development Server

```bash
# Standard way
python app.py

# Using uv
uv run python app.py

# Using Flask CLI
export FLASK_APP=app.py
flask run

# Custom port
flask run --port=8000

# Listen on all interfaces
flask run --host=0.0.0.0
```

## Project Architecture

### MVC Pattern

The project follows a simplified MVC (Model-View-Controller) pattern:

- **Models** (`models.py`): Database schema and data logic
- **Views** (`templates/`): HTML presentation layer
- **Controllers** (`app.py`): Route handlers and business logic

### File Organization

```
app.py              # Routes and application logic
models.py           # Database models
extensions.py       # Shared extensions (SQLAlchemy)
templates/          # Jinja2 templates
├── base.html       # Base layout
└── apps/           # Module-specific templates
static/             # Static assets
└── css/
    └── style.css   # Global styles
```

### Separation of Concerns

As your project grows, consider this structure:

```
app/
├── __init__.py           # App factory
├── models/
│   ├── __init__.py
│   ├── habit.py
│   ├── mood.py
│   └── ...
├── routes/
│   ├── __init__.py
│   ├── habits.py
│   ├── mood.py
│   └── ...
├── templates/
└── static/
```

## Adding Authentication

### Using Flask-Login

Install Flask-Login:

```bash
uv add flask-login
```

Create a User model:

```python
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
```

Configure Flask-Login in `app.py`:

```python
from flask_login import LoginManager, login_user, logout_user, login_required

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

Protect routes:

```python
@app.route('/habit-tracker')
@login_required
def habit_tracker():
    # Only authenticated users can access
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    return render_template('apps/habit_tracker/index.html', habits=habits)
```

## Form Handling

### Using Flask-WTF

Install Flask-WTF:

```bash
uv add flask-wtf
```

Create form classes:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class HabitForm(FlaskForm):
    name = StringField('Habit Name',
        validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Description',
        validators=[Length(max=500)])
    submit = SubmitField('Add Habit')
```

Use in routes:

```python
@app.route('/habit-tracker', methods=['GET', 'POST'])
def habit_tracker():
    form = HabitForm()
    if form.validate_on_submit():
        habit = Habit(name=form.name.data, description=form.description.data)
        db.session.add(habit)
        db.session.commit()
        flash('Habit added successfully!', 'success')
        return redirect(url_for('habit_tracker'))

    habits = Habit.query.all()
    return render_template('apps/habit_tracker/index.html', form=form, habits=habits)
```

### CSRF Protection

Flask-WTF provides CSRF protection automatically. Configure in `app.py`:

```python
app.config['SECRET_KEY'] = 'your-secret-key'
```

Add CSRF token to forms:

```html
<form method="POST">
    {{ form.csrf_token }}
    {{ form.name.label }} {{ form.name }}
    {{ form.submit }}
</form>
```

## Testing

The complete testing workflow—including project fixtures, common commands, and tips for writing new tests—lives in [`docs/TESTING.md`](TESTING.md). Use that guide when you need detailed instructions or examples.

Quick checks to run before you push:

```bash
uv run pytest -v
uv run pytest -k "habit"  # Target a subset during development
```

Need to adjust or trim tests after removing modules? Head to the **Customizing Tests** section in [`docs/TESTING.md`](TESTING.md) for the exact steps.

## Continuous Integration

GitHub Actions is already configured for this project. For an overview of what runs in CI, how to read results, and which commands mirror the pipeline locally, see [`CI_QUICKSTART.md`](../CI_QUICKSTART.md). That guide also links to the full CI reference and troubleshooting tips if a workflow fails.

## API Development

### Creating RESTful APIs

Add JSON endpoints:

```python
from flask import jsonify

@app.route('/api/habits', methods=['GET'])
def api_get_habits():
    habits = Habit.query.all()
    return jsonify([{
        'id': h.id,
        'name': h.name,
        'description': h.description,
        'created_at': h.created_at.isoformat()
    } for h in habits])

@app.route('/api/habits', methods=['POST'])
def api_create_habit():
    data = request.get_json()
    habit = Habit(name=data['name'], description=data.get('description', ''))
    db.session.add(habit)
    db.session.commit()
    return jsonify({'id': habit.id, 'name': habit.name}), 201
```

### CORS Support

For frontend applications on different domains:

```bash
uv add flask-cors
```

```python
from flask_cors import CORS

CORS(app)
# Or specific routes:
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
```

## Performance Optimization

### Query Optimization

```python
# Eager loading relationships
habits = Habit.query.options(db.joinedload(Habit.user)).all()

# Pagination
page = request.args.get('page', 1, type=int)
habits = Habit.query.paginate(page=page, per_page=20)
```

### Caching

Install Flask-Caching:

```bash
uv add flask-caching
```

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/habits')
@cache.cached(timeout=60)
def habits():
    # This view will be cached for 60 seconds
    habits = Habit.query.all()
    return render_template('habits.html', habits=habits)
```

## Debugging Tips

### Using Python Debugger

Add breakpoints in your code:

```python
import pdb; pdb.set_trace()
```

### Logging

Configure logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)

app.logger.info('Application started')
app.logger.debug('Debug message')
app.logger.error('Error occurred')
```

### Flask Debug Toolbar

Install debug toolbar:

```bash
uv add flask-debugtoolbar
```

```python
from flask_debugtoolbar import DebugToolbarExtension

app.config['SECRET_KEY'] = 'dev-key'
toolbar = DebugToolbarExtension(app)
```

## Deployment Preparation

### Production Configuration

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}

app.config.from_object(config[os.environ.get('FLASK_ENV', 'development')])
```

### WSGI Server

For production, use Gunicorn:

```bash
uv add gunicorn
```

Run with:

```bash
gunicorn app:app
```

Create `Procfile` for Heroku:

```
web: gunicorn app:app
```

## Code Quality

### Linting

```bash
uv add ruff
ruff check .
ruff format .
```

### Type Checking

```bash
uv add mypy
mypy app.py
```

## Learning Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)
- [Real Python Flask Tutorials](https://realpython.com/tutorials/flask/)
