# 🗄️ Database Management

This guide covers database operations, migrations, and schema management for the Student Starter Pack.

## Database Overview

The project uses:
- **ORM**: SQLAlchemy
- **Database**: SQLite (file-based, perfect for development)
- **Database File**: `app.db` (created automatically on first run)

## Database Models

### Current Models

Located in `models.py`:

#### Habit
```python
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_dates = db.Column(db.Text)  # JSON string of dates
```

#### MoodEntry
```python
class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Expense
```python
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_by = db.Column(db.String(100), nullable=False)
    participants = db.Column(db.Text)  # Comma-separated names
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Recipe
```python
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    prep_time = db.Column(db.Integer)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## Basic Operations

### Initialize Database

The database is created automatically on first run. To manually initialize:

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Reset Database

To completely reset the database (deletes all data):

```bash
# Delete the database file
rm app.db

# Recreate tables
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Backup Database

SQLite databases are just files, so backing up is simple:

```bash
# Create a backup
cp app.db app.db.backup

# Restore from backup
cp app.db.backup app.db
```

## Schema Modifications

### Adding New Fields

When you add fields to a model, you have two options:

#### Option 1: Simple Reset (Development Only)
Best for development when you don't have important data:

```bash
rm app.db
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

#### Option 2: Manual Migration
If you need to preserve data:

```python
# Example: Adding a 'category' field to Habit
import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Add the new column with a default value
cursor.execute('ALTER TABLE habit ADD COLUMN category VARCHAR(50) DEFAULT "general"')

conn.commit()
conn.close()
```

### Removing Models

If you remove a model from `models.py`:

1. Delete the corresponding table from the database:

```python
from app import app, db
from models import Habit  # Import the model to drop

with app.app_context():
    Habit.__table__.drop(db.engine)
```

2. Or simply reset the database to reflect the current schema.

## Advanced: Flask-Migrate

For production applications or complex schema changes, use Flask-Migrate.

### Installation

```bash
uv add flask-migrate
```

### Setup

Update `app.py`:

```python
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db.init_app(app)

# Add this line
migrate = Migrate(app, db)
```

### Initialize Migrations

```bash
flask db init
```

This creates a `migrations/` folder.

### Create Migration

After modifying models:

```bash
flask db migrate -m "Add category field to Habit"
```

This generates a migration script in `migrations/versions/`.

### Apply Migration

```bash
flask db upgrade
```

### Rollback Migration

```bash
flask db downgrade
```

### Migration Best Practices

1. **Review generated migrations**: Always check the auto-generated migration script before applying
2. **Test migrations**: Test on a copy of your database first
3. **Version control**: Commit migration files to git
4. **One migration per change**: Keep migrations focused and atomic

## Database Inspection

### Using SQLite CLI

```bash
# Open the database
sqlite3 app.db

# List all tables
.tables

# Show table schema
.schema habit

# Query data
SELECT * FROM habit;

# Exit
.quit
```

### Using Python

```python
from app import app, db
from models import Habit

with app.app_context():
    # Count records
    count = Habit.query.count()
    print(f"Total habits: {count}")

    # Get all records
    habits = Habit.query.all()
    for habit in habits:
        print(f"{habit.name}: {habit.description}")

    # Filter records
    recent_habits = Habit.query.filter(
        Habit.created_at >= datetime(2024, 1, 1)
    ).all()
```

## Production Considerations

### Using PostgreSQL

For production, switch from SQLite to PostgreSQL:

```bash
uv add psycopg2-binary
```

Update configuration:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/dbname'
```

### Connection Pooling

For better performance with concurrent users:

```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
}
```

### Database Security

1. **Never commit database files** to git (add `*.db` to `.gitignore`)
2. **Use environment variables** for database credentials
3. **Enable SSL** for remote database connections
4. **Regular backups** in production environments

## Common Database Queries

### Create

```python
from app import app, db
from models import Habit

with app.app_context():
    habit = Habit(name="Exercise", description="30 min daily")
    db.session.add(habit)
    db.session.commit()
```

### Read

```python
# Get by ID
habit = Habit.query.get(1)

# Get all
habits = Habit.query.all()

# Filter
habits = Habit.query.filter_by(name="Exercise").all()

# Order by
habits = Habit.query.order_by(Habit.created_at.desc()).all()

# Limit
habits = Habit.query.limit(10).all()
```

### Update

```python
habit = Habit.query.get(1)
habit.description = "Updated description"
db.session.commit()
```

### Delete

```python
habit = Habit.query.get(1)
db.session.delete(habit)
db.session.commit()
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common database-related issues and solutions.
