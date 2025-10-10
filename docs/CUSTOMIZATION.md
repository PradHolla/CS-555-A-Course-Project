# 🎨 Customization Guide

This guide covers how to customize the Student Starter Pack for your specific project needs.

## Before You Begin

The Student Starter Pack ships with four complete modules. If you still need to pick your starting point or remove unused modules, follow the step-by-step instructions in [`QUICK_START.md`](QUICK_START.md) first. Once you have the modules you want to keep, come back here to tailor them to your project.

## Adding New Features

### Extending Database Models

Add new fields to existing models in `models.py`:

```python
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # New fields
    category = db.Column(db.String(50))
    priority = db.Column(db.Integer, default=1)
    target_frequency = db.Column(db.String(20))  # daily, weekly, etc.

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

After modifying models, reset the database (see [DATABASE.md](DATABASE.md)).

### Adding New Routes

Create new routes in `app.py`:

```python
@app.route('/new-feature', methods=['GET', 'POST'])
def new_feature():
    if request.method == 'POST':
        # Handle form submission
        data = request.form.get('data')
        # Process and save data
        db.session.commit()
        return redirect(url_for('new_feature'))

    # Render template with data
    return render_template('apps/new_feature/index.html')
```

### Creating New Templates

Create a new template folder and file:

```bash
mkdir -p templates/apps/new_feature
touch templates/apps/new_feature/index.html
```

Use the existing templates as references for structure and styling.

## Styling Customization

### Using Tailwind CSS

The project uses Tailwind CSS via CDN. You can use any Tailwind utility classes directly in your HTML:

```html
<div class="bg-blue-500 text-white p-4 rounded-lg">
    Custom styled element
</div>
```

### Module-Specific Styling

Each module has its own color scheme defined in the `<style>` block of its template. For example, the Habit Tracker uses:

```css
:root {
    --primary: #059669;
    --primary-dark: #047857;
    --accent: #10b981;
}
```

Modify these CSS variables to change the color scheme.

### Global Styles

Edit `static/css/style.css` for global styling that affects all modules.

### Custom CSS Classes

Add custom styles in the `<style>` blocks within your templates:

```html
<style>
.custom-class {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 1rem;
}
</style>
```

## Advanced Customization

### Adding Form Validation

Install Flask-WTF for form handling:

```bash
uv add flask-wtf
```

Create form classes:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class HabitForm(FlaskForm):
    name = StringField('Habit Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Add Habit')
```

### Adding User Authentication

Install Flask-Login:

```bash
uv add flask-login
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for implementation details.

### API Endpoints

Add RESTful API endpoints for mobile apps or JavaScript frontends:

```python
@app.route('/api/habits', methods=['GET'])
def api_habits():
    habits = Habit.query.all()
    return jsonify([{
        'id': h.id,
        'name': h.name,
        'description': h.description
    } for h in habits])
```

### Using Blueprints

As your app grows, organize routes using Flask Blueprints:

```python
from flask import Blueprint

habit_bp = Blueprint('habits', __name__, url_prefix='/habits')

@habit_bp.route('/')
def index():
    return render_template('apps/habit_tracker/index.html')

# In app.py:
app.register_blueprint(habit_bp)
```

## Best Practices

1. **Version Control**: Commit changes frequently with descriptive messages
2. **Testing**: Write tests for new features before deployment
3. **Documentation**: Update comments and docs as you customize
4. **Modularity**: Keep modules independent for easier maintenance
5. **Security**: Add CSRF protection and input validation for production use
