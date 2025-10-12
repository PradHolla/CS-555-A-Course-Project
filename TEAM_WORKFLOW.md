# Team Development Workflow - CS-555 Expense Splitter

## 🎯 Quick Overview

- We follow **Test-Driven Development (TDD)**
- All code must pass **CI/CD checks** before merging
- **Never commit directly to `main`**
- Use **Pull Requests** for all changes
- Aim for **80%+ test coverage**

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

## 🔄 Daily Development Workflow

### Morning Routine

- [ ] Pull latest changes from `develop`
  ```bash
  git checkout develop
  git pull origin develop
  ```

- [ ] Create or switch to your feature branch
  ```bash
  git checkout -b feature/my-feature
  # or
  git checkout feature/my-feature
  ```

- [ ] Rebase on latest develop (if needed)
  ```bash
  git rebase develop
  ```

### Development Cycle (TDD Approach)

#### Step 1: Write Test First
- Open `tests/test_models.py` or `tests/test_routes.py`
- Write a test for the feature you're about to build
- Test should **fail** initially (Red phase)

Example:
```python
def test_expense_with_category(app):
    """Test that Expense model can store category."""
    # Arrange
    expense = Expense(
        description="Lunch",
        amount=15.50,
        payer="Alice",
        participants="Alice, Bob",
        category="Food"
    )
    
    # Act
    db.session.add(expense)
    db.session.commit()
    
    # Assert
    stored = Expense.query.first()
    assert stored.category == "Food"
```

#### Step 2: Run Test (Should Fail)
```bash
uv run pytest tests/test_models.py::test_expense_with_category -v
```

#### Step 3: Write Minimum Code to Pass Test
- Implement the feature in `app.py`, `models.py`, or templates
- Write only enough code to make the test pass (Green phase)

#### Step 4: Run Test Again (Should Pass)
```bash
uv run pytest tests/test_models.py::test_expense_with_category -v
```

#### Step 5: Refactor
- Clean up code
- Remove duplication
- Improve readability
- Run tests again to ensure nothing broke

#### Step 6: Repeat
- Write next test
- Make it pass
- Refactor

### Before Every Commit

Run these checks in order:

```bash
# 1. Format code
uv run ruff format .

# 2. Check linting
uv run ruff check .

# 3. Run all tests
uv run pytest -v

# 4. Check test coverage
uv run pytest --cov=. --cov-report=term

# 5. Security scan (optional but recommended)
uv run bandit -r .
```

### Committing Changes

- [ ] Use conventional commit messages
  ```bash
  git add .
  git commit -m "feat: add expense category feature"
  ```

- [ ] Commit message format:
  - `feat:` - New feature
  - `fix:` - Bug fix
  - `test:` - Adding tests
  - `docs:` - Documentation changes
  - `refactor:` - Code refactoring
  - `style:` - Code formatting
  - `chore:` - Maintenance tasks

### Pushing Changes

```bash
# Push to your feature branch
git push origin feature/my-feature
```

### End of Day

- [ ] Commit your work (even if incomplete)
- [ ] Push to remote for backup
- [ ] Update task status on project board

---

## 🔍 Pull Request Process

### Creating a Pull Request

1. **Push your branch**
   ```bash
   git push origin feature/my-feature
   ```

2. **Go to GitHub repository**
   - Click "Pull Requests" tab
   - Click "New Pull Request"

3. **Fill out PR template**
   - **Title**: Clear, descriptive title
   - **Description**: What does this PR do?
   - **Testing**: How did you test it?
   - **Screenshots**: If UI changes

4. **PR Checklist**
   - [ ] Tests added for new functionality
   - [ ] All tests pass locally
   - [ ] Code formatted with Ruff
   - [ ] No linting errors
   - [ ] Documentation updated
   - [ ] No commented-out code
   - [ ] Database migrations included (if applicable)

### Example PR Description

```markdown
## Description
Adds expense category feature allowing users to categorize expenses (Food, Transport, Entertainment, etc.)

## Changes
- Added `category` field to Expense model
- Updated expense form to include category dropdown
- Added tests for category functionality
- Updated documentation

## Testing
- Added 5 new unit tests (all passing)
- Tested manually on all expense pages
- Test coverage: 85%

## Screenshots
[Attach screenshots if UI changed]
```

### After Creating PR

- **GitHub Actions CI will automatically**:
  - ✅ Run all tests on 3 operating systems
  - ✅ Check code formatting
  - ✅ Run security scans
  - ✅ Generate coverage reports
  - ✅ Verify app builds

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

#### What to Check

- [ ] **Tests**: Are tests included and passing?
- [ ] **Coverage**: Does coverage meet 80% minimum?
- [ ] **Functionality**: Does the code do what it claims?
- [ ] **Style**: Does code follow Ruff style guide?
- [ ] **Security**: Any security vulnerabilities?
- [ ] **Performance**: Any performance issues?
- [ ] **Documentation**: Is code well-documented?
- [ ] **Database**: Are database queries optimized?
- [ ] **Error Handling**: Are errors handled properly?

#### Review Comment Types

Use these labels:

- **🚫 BLOCKING**: Must fix before merge
  ```markdown
  🚫 BLOCKING: Security vulnerability on line 45
  ```

- **💡 SUGGESTION**: Nice to have but not required
  ```markdown
  💡 SUGGESTION: Consider extracting this into a helper function
  ```

- **❓ QUESTION**: Need clarification
  ```markdown
  ❓ QUESTION: Why did you choose this approach over X?
  ```

- **✨ PRAISE**: Positive feedback
  ```markdown
  ✨ PRAISE: Great test coverage!
  ```

#### Review Turnaround Time

- Small PRs (< 100 lines): Within 4 hours
- Medium PRs (100-500 lines): Within 1 day
- Large PRs (> 500 lines): Within 2 days

### As an Author

#### Responding to Reviews

- [ ] Read all comments carefully
- [ ] Respond to every comment
- [ ] Make requested changes promptly
- [ ] Mark conversations as resolved after fixing
- [ ] Thank reviewers for their time
- [ ] Request re-review after changes

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
