# Team Development Workflow - CS-555 Expense Splitter

## 🎯 Quick Start

**The 9-Step Process:**

1. **Pick a ticket** (full-stack feature)
2. **Write backend test** (TDD - test first!)
3. **Implement backend** (make test pass)
4. **Build frontend UI** (keep it simple)
5. **Test end-to-end** (open browser, test manually)
6. **Take screenshots** (if you changed UI)
7. **Create ONE PR** (backend + frontend together)
8. **Get review** (wait for approval)
9. **Merge!** (squash and merge)

**Key Rules:**
- Never commit directly to `main`
- All tests must pass (80%+ coverage)
- Use conventional commits (`feat:`, `fix:`, etc.)
- Include screenshots if UI changed

---

## 📋 Initial Setup (Do This First)

### 1. Clone the Repository
```bash
git clone https://github.com/PradHolla/CS-555-A-Course-Project.git
cd CS-555-A-Course-Project
```

### 2. Install UV Package Manager
```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install Dependencies
```bash
uv sync
```

### 4. Verify Installation
```bash
# Run tests
uv run pytest -v

# Start the app
uv run python app.py
# Visit http://localhost:5000
```

### 5. Configure Git
```bash
# Set your identity
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

---

## 🌳 Branch Strategy

### Branch Types

- **`main`** - Production-ready code (protected, no direct commits)
- **`develop`** - Integration branch (protected, PR required)
- **`feature/feature-name`** - New features
- **`bugfix/bug-description`** - Bug fixes
- **`hotfix/critical-fix`** - Critical production fixes

### Creating a Feature Branch

```bash
# 1. Switch to develop and update
git checkout develop
git pull origin develop

# 2. Create your feature branch
git checkout -b feature/add-expense-categories

# 3. Work on your feature
# (write tests, write code)

# 4. Push to remote
git push origin feature/add-expense-categories
```

### Branch Naming Conventions

- **Feature**: `feature/add-expense-reports`
- **Bug Fix**: `bugfix/fix-split-calculation`
- **Hotfix**: `hotfix/security-patch`
- Use lowercase with hyphens
- Be descriptive but concise

---

## 🔄 Development Workflow (Full-Stack)

### Step-by-Step Process

When you pick up a ticket, follow these steps:

#### 1. Pick a Ticket (Full-Stack Feature)
- Choose a task from the project board
- Understand what needs to be done (backend + frontend)

#### 2. Write Backend Test (TDD)
- Open `tests/test_models.py` or `tests/test_routes.py`
- Write a test for the backend functionality
- Test should **fail** initially (Red phase)

Example:
```python
def test_delete_expense(client):
    """Test that expense can be deleted."""
    # Arrange
    expense = Expense(description="Test", amount=10, payer="Alice")
    db.session.add(expense)
    db.session.commit()
    
    # Act
    response = client.post(f'/expense/{expense.id}/delete')
    
    # Assert
    assert response.status_code == 302  # Redirect
    assert Expense.query.get(expense.id) is None
```

Run test (should fail):
```bash
uv run pytest tests/test_routes.py::test_delete_expense -v
```

#### 3. Implement Backend Code
- Write the backend code in `app.py` or `models.py`
- Make the test pass (Green phase)

Example:
```python
@app.route('/expense/<int:expense_id>/delete', methods=['POST'])
def delete_expense(expense_id):
    """Delete an expense by ID."""
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('expense_splitter'))
```

Run test again (should pass):
```bash
uv run pytest tests/test_routes.py::test_delete_expense -v
```

#### 4. Build Frontend UI
- Update the HTML templates to add/modify UI
- Keep it **simple** - just build on what exists
- Add basic styling if needed
- Add JavaScript if you need interactivity

Example:
```html
<!-- Add a delete button to the expense card -->
<form action="{{ url_for('delete_expense', expense_id=expense.id) }}" method="POST" style="display:inline;">
    <button type="submit" onclick="return confirm('Delete this expense?')">
        Delete
    </button>
</form>
```

#### 5. Test End-to-End
- Start the app: `uv run python app.py`
- Open in browser: http://localhost:5000
- Test your feature manually:
  - Does it work?
  - Any errors in console? (F12 → Console tab)
  - Does it look okay?

#### 6. Take Screenshots
- Take a screenshot showing your feature working
- If you changed the UI, show before/after
- Use Windows Snipping Tool: `Win+Shift+S`

#### 7. Create ONE PR with Everything
- Your PR includes:
  - Backend code ✅
  - Backend tests ✅
  - Frontend UI ✅
  - Screenshots (if UI changed) ✅

#### 8. Get Review
- Wait for teammate to review
- Address feedback if any
- Make changes if requested

#### 9. Merge!
- Once approved and CI passes
- Squash and merge to main
- Delete your feature branch

---

## 📝 Before Every Commit

Run these checks:

```bash
# 1. Format code
uv run ruff format .

# 2. Check linting
uv run ruff check .

# 3. Run all tests
uv run pytest -v

# 4. Check test coverage (should be 80%+)
uv run pytest --cov=. --cov-report=term
```

All green? ✅ You're ready to commit!

### Committing Changes

Use conventional commit messages:

```bash
git add .
git commit -m "feat: add delete expense button"
```

**Commit message format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `test:` - Adding tests
- `docs:` - Documentation
- `refactor:` - Code cleanup
- `style:` - Formatting
- `chore:` - Maintenance

### Pushing Changes

```bash
# Push to your feature branch
git push origin feature/my-feature
```

### End of Day

---

## 🔍 Pull Request Process

### Before Creating PR

Make sure you've done these:

- [ ] All tests pass: `uv run pytest -v`
- [ ] Code formatted: `uv run ruff format .`
- [ ] No linting errors: `uv run ruff check .`
- [ ] Coverage is 80%+: `uv run pytest --cov=.`
- [ ] Tested the feature manually in browser
- [ ] Screenshots ready (if you changed UI)

### Creating a Pull Request

1. **Push your branch**
   ```bash
   git push origin feature/my-feature
   ```

2. **Go to GitHub**
   - Click "Pull Requests" tab
   - Click "New Pull Request"

3. **Fill out PR description**
   
   Use this template:

   ```markdown
   ## Description
   Brief description of what this PR does
   
   ## Changes
   - Added delete expense functionality
   - Added tests for delete endpoint
   - Added delete button to UI
   
   ## Testing
   - All tests pass ✅
   - Tested manually in browser ✅
   - Coverage: 85%
   
   ## Screenshots
   [Paste screenshot here if UI changed]
   ```

4. **Submit & Wait**
   - GitHub Actions CI will automatically:
     - ✅ Run all tests on multiple OS
     - ✅ Check code formatting
     - ✅ Run security scans
     - ✅ Generate coverage reports
   
   - Wait for teammate to review
   - Address any feedback
   - Once approved + CI passes → Merge!

---

- **Wait for**:
  - All CI checks to pass (green checkmarks)
  - At least 1 code review approval
  - No merge conflicts

### Addressing Review Comments

1. **Read all comments carefully**

2. **Respond to each comment**:
   - Acknowledge feedback
   - Explain your reasoning
   - Ask clarifying questions

3. **Make requested changes**:
   ```bash
   # Make changes to your code
   git add .
   git commit -m "fix: address review comments"
   git push origin feature/my-feature
   ```

4. **Re-request review** after pushing changes

5. **Don't take feedback personally** - it's about code quality!

---

## ✅ Testing Requirements

### Minimum Coverage Targets

- **Overall**: 80%+
- **Models**: 90%+
- **Routes**: 85%+
- **Critical logic** (calculations): 100%

### Test Types to Write

#### 1. Unit Tests (`test_models.py`)
- Test database models
- Test data validation
- Test constraints

Example:
```python
def test_expense_requires_amount(app):
    """Test that Expense model raises error when amount is None."""
    expense = Expense(description="Test", amount=None, payer="Alice")
    db.session.add(expense)
    
    with pytest.raises(IntegrityError):
        db.session.commit()
    
    db.session.rollback()
```

#### 2. Integration Tests (`test_routes.py`)
- Test HTTP endpoints
- Test form submissions
- Test redirects

Example:
```python
def test_expense_splitter_post_creates_expense(client):
    """Test that POST /expense-splitter creates expense."""
    data = {
        'description': 'Lunch',
        'amount': '25.00',
        'payer': 'Alice',
        'participants': 'Alice, Bob'
    }
    
    response = client.post('/expense-splitter', data=data)
    
    assert response.status_code == 302
    expense = Expense.query.first()
    assert expense is not None
    assert expense.amount == 25.00
```

#### 3. Edge Case Tests
Always test:
- Empty strings
- Null/None values
- Negative numbers
- Very large numbers
- Invalid data types
- Special characters
- Concurrent operations

### Running Tests

```bash
# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/test_models.py -v

# Run specific test
uv run pytest tests/test_models.py::test_expense_with_category -v

# Run tests matching pattern
uv run pytest -k "expense" -v

# Run with coverage
uv run pytest --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Test Naming Convention

Format: `test_<what>_<condition>_<expected>`

Examples:
- `test_expense_splitter_get_returns_ok`
- `test_expense_with_invalid_amount_raises_error`
- `test_empty_participants_list_handled_correctly`

### AAA Pattern (Required)

All tests must follow **Arrange-Act-Assert** pattern:

```python
def test_example(client):
    """Clear description of what is being tested."""
    # Arrange - Set up test data
    data = {'key': 'value'}
    
    # Act - Perform the action
    response = client.post('/endpoint', data=data)
    
    # Assert - Verify the result
    assert response.status_code == 200
```

---

## 🔒 Code Review Guidelines

### As a Reviewer

Check these things:

- [ ] **Tests**: Are tests included and passing?
- [ ] **Coverage**: Does coverage meet 80%+?
- [ ] **Functionality**: Does the code actually work?
- [ ] **Style**: Is code formatted properly?
- [ ] **Security**: Any obvious security issues?
- [ ] **Error Handling**: Are errors handled?
- [ ] **Screenshots**: If UI changed, are screenshots included?

**Leave helpful comments:**

- **🚫 BLOCKING**: Must fix before merge
- **💡 SUGGESTION**: Nice to have
- **❓ QUESTION**: Need clarification
- **✨ PRAISE**: Good work!

Example:
```markdown
🚫 BLOCKING: This will fail if expense is None. Add error handling.

💡 SUGGESTION: Consider using a constant for this value.

✨ PRAISE: Great test coverage!
```

### As an Author

When you get review feedback:

- [ ] Read all comments
- [ ] Respond to every comment
- [ ] Make requested changes
- [ ] Mark conversations as resolved
- [ ] Request re-review after changes

---

#### If You Disagree

- Explain your reasoning politely
- Provide evidence (benchmarks, documentation)
- Be open to discussion
- Let team lead make final decision if needed

---

## 🗃️ Database Changes

### When Modifying Database Schema

1. **Update model** (`models.py`)
   ```python
   class Expense(db.Model):
       # ... existing fields ...
       category = db.Column(db.String(50))  # New field
   ```

2. **Document the change**
   - Create migration note in commit message
   - Update schema documentation

3. **Reset local database**
   ```bash
   # Windows PowerShell
   Remove-Item -ErrorAction SilentlyContinue instance\app.db
   
   # Create fresh database
   uv run python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

4. **Update all tests** to use new fields

5. **Inform team** about database reset needed

### Migration Commit Message Format

```
feat: add category field to Expense model

BREAKING CHANGE: Database schema updated
Action required: Delete instance/app.db and recreate database

Changes:
- Added category field (String, 50 chars)
- Updated form to include category dropdown
- Added tests for new field
```

---

## 📝 Documentation Requirements

### Code Documentation

#### Functions/Methods
```python
def split_expense(amount: float, participants: list[str]) -> dict:
    """
    Split an expense equally among participants.
    
    Args:
        amount: Total expense amount in dollars
        participants: List of participant names
        
    Returns:
        Dictionary mapping participants to amounts owed
        
    Raises:
        ValueError: If amount is negative or participants empty
        
    Example:
        >>> split_expense(30.00, ['Alice', 'Bob', 'Charlie'])
        {'Alice': 10.00, 'Bob': 10.00, 'Charlie': 10.00}
    """
```

#### Classes
```python
class Expense(db.Model):
    """
    Model representing a shared expense.
    
    Attributes:
        id: Unique identifier
        description: What the expense was for
        amount: Total amount in dollars
        payer: Who paid the expense
        participants: Comma-separated list of people splitting
        category: Expense category (optional)
        created_at: When expense was recorded
    """
```

#### Complex Logic
```python
# Calculate share per person, rounding to 2 decimal places
# to avoid floating-point precision issues
share = round(expense.amount / len(participants), 2)
```

### Update Documentation When

- [ ] Adding new features
- [ ] Changing existing features
- [ ] Modifying database schema
- [ ] Changing API endpoints
- [ ] Updating dependencies

---

## 🚀 CI/CD (Automated Checks)

### What Happens Automatically

When you create a PR, GitHub Actions automatically:

1. **Runs tests** on 3 operating systems (Linux, macOS, Windows)
2. **Checks code formatting** with Ruff
3. **Runs security scan** with Bandit
4. **Generates coverage report**
5. **Verifies app builds** successfully

### CI Status

- 🟢 **All checks passed** - Ready to merge
- 🔴 **Some checks failed** - Fix issues
- 🟡 **Checks running** - Wait for completion

### If CI Fails

1. **Click on failed check** to see error details
2. **Fix the issue locally**:
   ```bash
   # Run the same check locally
   uv run pytest -v  # If tests failed
   uv run ruff check .  # If linting failed
   ```
3. **Commit and push fix**:
   ```bash
   git add .
   git commit -m "fix: resolve CI issues"
   git push origin feature/my-feature
   ```
4. **CI will re-run automatically**

### Branch Protection Rules

**`main` branch is protected**:
- ❌ Cannot commit directly
- ✅ Must create PR
- ✅ Must pass all CI checks
- ✅ Must have 1 approval
- ❌ Cannot force push

---

## ⚡ Quick Reference Commands

### Git Commands
```bash
# Daily sync
git checkout develop && git pull

# Create feature branch
git checkout -b feature/my-feature

# Save work
git add . && git commit -m "feat: add feature"

# Push to remote
git push origin feature/my-feature

# Update from develop
git checkout develop && git pull
git checkout feature/my-feature
git rebase develop
```

### Testing Commands
```bash
# Run all tests
uv run pytest -v

# Run specific test
uv run pytest tests/test_models.py::test_name -v

# Run with coverage
uv run pytest --cov=. --cov-report=term

# Run tests matching pattern
uv run pytest -k "expense" -v
```

### Code Quality Commands
```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Security scan
uv run bandit -r .
```

### Development Commands
```bash
# Install dependencies
uv sync

# Start app
uv run python app.py

# Reset database
Remove-Item instance\app.db  # Windows
uv run python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

---

## 🆘 Common Issues & Solutions

### Issue: Tests fail locally but not in CI
**Solution**: 
- Ensure you're using same Python version as CI (3.11)
- Delete and recreate virtual environment: `uv sync --reinstall`
- Check for hardcoded paths or environment-specific code

### Issue: Merge conflicts
**Solution**:
```bash
# Update from develop
git checkout develop && git pull
git checkout feature/my-feature
git rebase develop

# Resolve conflicts in editor
# Then:
git add .
git rebase --continue
git push origin feature/my-feature --force-with-lease
```

### Issue: Accidentally committed to main
**Solution**:
```bash
# Create a branch from current main
git branch feature/my-changes

# Reset main to remote
git checkout main
git reset --hard origin/main

# Switch to new branch
git checkout feature/my-changes
git push origin feature/my-changes
```

### Issue: Tests pass locally but fail in CI
**Solution**:
- Check CI logs for exact error
- Ensure test database is isolated
- Check for platform-specific code (Windows vs Linux)
- Verify all dependencies in pyproject.toml

### Issue: Need to undo last commit
**Solution**:
```bash
# Undo commit but keep changes
git reset --soft HEAD~1

# Undo commit and discard changes
git reset --hard HEAD~1
```

---

## 📞 Getting Help

### When Stuck

1. **Check documentation**:
   - `README.md` - Project overview
   - `TESTING.md` - Testing guide
   - `CI.md` - CI/CD details
   - `TROUBLESHOOTING.md` - Common issues

2. **Search GitHub Issues**:
   - Someone may have had same problem

3. **Ask team**:
   - Post in team chat
   - Tag relevant person
   - Include error messages and what you tried

4. **Create GitHub Issue**:
   - Describe problem clearly
   - Include steps to reproduce
   - Attach error logs
   - Add relevant labels

### Support Channels

- **Technical Issues**: Create GitHub Issue
- **Process Questions**: Ask in team chat
- **Urgent Issues**: Contact team lead
- **General Questions**: Weekly team meeting

---

## ✅ Team Member Checklist

### First Week

- [ ] Complete initial setup (install uv, clone repo)
- [ ] Run tests successfully locally
- [ ] Start app and view in browser
- [ ] Read all documentation in `docs/` folder
- [ ] Create test feature branch
- [ ] Submit first PR (can be documentation update)
- [ ] Review another team member's PR
- [ ] Attend first team meeting

### Ongoing

- [ ] Follow TDD approach for all features
- [ ] Run pre-commit checks before every commit
- [ ] Write clear commit messages
- [ ] Keep PRs small (< 500 lines)
- [ ] Review PRs within 24 hours
- [ ] Update documentation with code changes
- [ ] Participate in code reviews
- [ ] Keep test coverage above 80%
- [ ] Communicate blockers early
- [ ] Update task status daily

---

## 🎯 Success Metrics

We measure success by:

- ✅ **Test Coverage**: Maintain > 80%
- ✅ **CI Pass Rate**: > 95%
- ✅ **PR Review Time**: < 24 hours average
- ✅ **Deployment Frequency**: At least weekly
- ✅ **Bug Rate**: < 5% of commits require hotfix
- ✅ **Code Quality**: Zero linting errors
- ✅ **Security**: Zero critical vulnerabilities

---

## 📅 Weekly Schedule

### Monday
- Team standup (15 min)
- Sprint planning (30 min)
- Review last week's metrics

### Tuesday - Thursday
- Daily async check-in
- Code review sessions
- Pair programming (optional)

### Friday
- Sprint demo (30 min)
- Retrospective (30 min)
- Plan next sprint
