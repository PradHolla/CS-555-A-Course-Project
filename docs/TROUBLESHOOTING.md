# 🚨 Troubleshooting Guide

Common issues and their solutions when working with the Student Starter Pack.

## Installation Issues

### `uv: command not found`

**Problem**: The `uv` package manager is not installed.

**Solution**: Install uv using the official installer:

```bash
# On Unix/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, restart your terminal or run:
```bash
source ~/.bashrc  # or ~/.zshrc
```

### Python Version Issues

**Problem**: Python version is too old (< 3.9).

**Solution**: Install Python 3.9 or higher:

```bash
# Check current version
python --version

# On macOS with Homebrew
brew install python@3.11

# On Ubuntu/Debian
sudo apt update
sudo apt install python3.11

# On Windows
# Download from python.org
```

### Dependency Installation Fails

**Problem**: `uv sync` fails with dependency conflicts.

**Solution**:

```bash
# Clear cache and retry
uv cache clean
uv sync

# Or use pip as fallback
pip install -r requirements.txt
```

## Runtime Issues

### Port 5000 Already in Use

**Problem**: Another application is using port 5000.

**Solution 1**: Kill the process using port 5000:

```bash
# On Unix/macOS
lsof -ti:5000 | xargs kill -9

# On Windows
netstat -ano | findstr :5000
taskkill /PID <process_id> /F
```

**Solution 2**: Change the port in `app.py`:

```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)
```

### Database Locked Error

**Problem**: `database is locked` or `OperationalError`.

**Causes**:
- Multiple instances of the app running
- SQLite browser tool has the database open
- Previous process crashed while holding a lock

**Solution**:

```bash
# 1. Stop all running instances
pkill -f "python app.py"

# 2. Close any SQLite browser tools

# 3. If problem persists, backup and recreate database
cp app.db app.db.backup
rm app.db
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'flask'`

**Solution**: Ensure virtual environment is activated:

```bash
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows

# Verify activation (should show .venv in path)
which python
```

If still not working, reinstall dependencies:

```bash
uv sync --force
```

## Database Issues

### Tables Not Created

**Problem**: Accessing routes shows "no such table" error.

**Solution**: Initialize the database:

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Schema Mismatch After Model Changes

**Problem**: Added a field to a model but getting errors about missing columns.

**Solution**: Reset the database (development only):

```bash
rm app.db
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

For production, use migrations (see [DATABASE.md](DATABASE.md)).

### Foreign Key Constraint Failed

**Problem**: Error when deleting records with relationships.

**Solution**: Enable foreign key constraints in SQLite:

```python
# In app.py
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

Or delete dependent records first:

```python
# Delete related records before deleting parent
habit = Habit.query.get(1)
HabitLog.query.filter_by(habit_id=habit.id).delete()
db.session.delete(habit)
db.session.commit()
```

## Template Issues

### Template Not Found

**Problem**: `TemplateNotFound: apps/habit_tracker/index.html`

**Solution**: Verify template path:

```bash
# Check file exists
ls templates/apps/habit_tracker/index.html

# Check Flask template folder configuration
python -c "from app import app; print(app.template_folder)"
```

### Static Files Not Loading

**Problem**: CSS or images not loading.

**Solution**:

1. Check file path in template:
```html
<!-- Correct -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

<!-- Incorrect -->
<link rel="stylesheet" href="/static/css/style.css">
```

2. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)

3. Verify file exists:
```bash
ls static/css/style.css
```

## Form Submission Issues

### Form Data Not Saving

**Problem**: Form submits but data doesn't appear in database.

**Debugging steps**:

```python
@app.route('/habit-tracker', methods=['POST'])
def habit_tracker():
    # Add debugging
    print("Form data:", request.form)
    print("Method:", request.method)

    if request.method == 'POST':
        name = request.form.get('name')
        print(f"Creating habit: {name}")

        habit = Habit(name=name)
        db.session.add(habit)

        try:
            db.session.commit()
            print("Commit successful")
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
```

Common causes:
- Missing `db.session.commit()`
- Form field names don't match `request.form.get('name')`
- Database constraint violations

### POST Request Results in 405 Error

**Problem**: `Method Not Allowed (405)` when submitting form.

**Solution**: Ensure route accepts POST:

```python
# Wrong
@app.route('/habit-tracker')

# Correct
@app.route('/habit-tracker', methods=['GET', 'POST'])
```

## Performance Issues

### Slow Page Loading

**Problem**: Pages take a long time to load.

**Solutions**:

1. Check for N+1 query problems:
```python
# Bad - N+1 queries
habits = Habit.query.all()
for habit in habits:
    print(habit.user.username)  # Separate query for each habit

# Good - Eager loading
habits = Habit.query.options(db.joinedload(Habit.user)).all()
```

2. Add pagination for large datasets:
```python
page = request.args.get('page', 1, type=int)
habits = Habit.query.paginate(page=page, per_page=20)
```

3. Enable query logging to identify slow queries:
```python
app.config['SQLALCHEMY_ECHO'] = True
```

### Memory Issues

**Problem**: Application consumes too much memory.

**Solution**: Close database sessions properly:

```python
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()
```

## Development Issues

### Changes Not Reflecting

**Problem**: Code changes don't appear when refreshing browser.

**Solutions**:

1. Ensure debug mode is enabled:
```python
app.run(debug=True)
```

2. Hard refresh browser (Ctrl+Shift+R)

3. Check if you're editing the right file:
```bash
pwd  # Verify current directory
```

4. Restart the development server

### Syntax Errors Not Showing

**Problem**: Getting generic 500 errors without details.

**Solution**: Enable debug mode and check terminal output:

```python
app.run(debug=True)
```

Or check logs:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Git Issues

### Accidentally Committed Database

**Problem**: `app.db` was committed to git.

**Solution**:

```bash
# Remove from git but keep locally
git rm --cached app.db

# Add to .gitignore
echo "app.db" >> .gitignore
echo "*.db" >> .gitignore

# Commit the changes
git add .gitignore
git commit -m "Remove database from version control"
```

### Merge Conflicts in Database

**Problem**: Git conflicts in `app.db`.

**Solution**: Database files shouldn't be in git. Remove and use migrations instead:

```bash
# Keep your local version
git checkout --ours app.db

# Or keep their version
git checkout --theirs app.db

# Better: Don't track database files
echo "*.db" >> .gitignore
git rm --cached app.db
```

## Deployment Issues

### Application Won't Start on Server

**Problem**: App works locally but fails on deployment.

**Checklist**:

1. Check Python version matches:
```bash
python --version
```

2. Verify all dependencies installed:
```bash
pip list
```

3. Set production configuration:
```bash
export FLASK_ENV=production
export SECRET_KEY=your-production-secret
```

4. Use a production WSGI server:
```bash
gunicorn app:app
```

5. Check logs for specific errors

### Static Files Not Loading in Production

**Problem**: CSS/JS work locally but not on server.

**Solution**: Configure static file serving:

For Heroku:
```python
# app.py
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
```

For nginx:
```nginx
location /static {
    alias /path/to/your/app/static;
}
```

## Getting More Help

If your issue isn't covered here:

1. **Check Flask documentation**: https://flask.palletsprojects.com/
2. **Search Stack Overflow**: https://stackoverflow.com/questions/tagged/flask
3. **Check application logs**: Look for error messages in terminal output
4. **Enable debug mode**: Get detailed error pages
5. **Add print statements**: Debug your code step by step

## Reporting Bugs

When reporting issues, include:

1. Python version (`python --version`)
2. Operating system
3. Full error message and traceback
4. Steps to reproduce the issue
5. What you've already tried
