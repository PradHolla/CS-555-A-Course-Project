# Continuous Integration (CI) Guide

This document explains the GitHub Actions CI/CD pipeline configured for the SSW555 Example Project.

## Table of Contents
- [Overview](#overview)
- [CI Workflows](#ci-workflows)
- [Running CI Locally](#running-ci-locally)
- [Customizing CI](#customizing-ci)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

## Overview

This project uses **GitHub Actions** for continuous integration. Every push and pull request automatically triggers tests, linting, and security checks.

### What Gets Tested?

✅ **Tests** - All pytest unit and integration tests
✅ **Linting** - Code style and quality checks with Ruff
✅ **Security** - Security vulnerability scanning with Bandit
✅ **Coverage** - Code coverage reporting with pytest-cov
✅ **Build** - Verify the application starts successfully
✅ **Multi-platform** - Tests run on Linux, macOS, and Windows
✅ **Multi-version** - Tests run on Python 3.9, 3.10, 3.11, 3.12

## CI Workflows

### 1. Main CI Workflow (`.github/workflows/ci.yml`)

This is the comprehensive CI pipeline that runs on every push and pull request.

**Jobs:**

#### `test` - Run Tests
- **Matrix strategy**: Tests across multiple OS and Python versions
- **Runs on**: Ubuntu, macOS, Windows
- **Python versions**: 3.9, 3.10, 3.11, 3.12
- **Steps**:
  1. Checkout code
  2. Set up Python
  3. Install uv package manager
  4. Install dependencies with `uv sync`
  5. Run tests with pytest
  6. Generate coverage report (Ubuntu + Python 3.11 only)
  7. Upload coverage to Codecov (optional)

#### `lint` - Code Quality
- **Runs on**: Ubuntu latest
- **Python version**: 3.11
- **Steps**:
  1. Check code formatting with Ruff
  2. Lint code for errors and style issues

#### `security` - Security Checks
- **Runs on**: Ubuntu latest
- **Python version**: 3.11
- **Steps**:
  1. Run Bandit security scanner
  2. Upload security report as artifact

#### `build` - Verify Build
- **Runs on**: Ubuntu latest
- **Depends on**: test, lint jobs must pass first
- **Steps**:
  1. Install dependencies
  2. Start Flask app
  3. Verify app responds to HTTP requests

**Trigger conditions:**
```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
```

### 2. Quick Test Workflow (`.github/workflows/quick-test.yml`)

A lightweight, fast CI check for rapid feedback.

**Features:**
- Runs only on Ubuntu with Python 3.11
- Skips matrix testing for speed
- Runs core tests only
- Completes in ~1-2 minutes

**Use case:** Quick validation during development

## Running CI Locally

Before pushing code, you can run the same checks locally:

### 1. Run Tests

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv pip install pytest-cov
uv run pytest --cov=. --cov-report=term --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 2. Run Linting

```bash
# Install dev dependencies
uv pip install ruff

# Check code formatting
uv run ruff format --check .

# Auto-format code
uv run ruff format .

# Lint code
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .
```

### 3. Run Security Check

```bash
# Install bandit
uv pip install bandit

# Run security scan
uv run bandit -r . -f screen

# Generate JSON report
uv run bandit -r . -f json -o bandit-report.json
```

### 4. Verify App Starts

```bash
# Start the app
uv run python app.py

# In another terminal, test it
curl http://localhost:5000
```

### 5. Install All Dev Dependencies

```bash
# Install development dependencies
uv pip install ".[dev]"

# Or sync everything
uv sync --all-extras
```

## Customizing CI

### Adding New Test Environments

Edit `.github/workflows/ci.yml`:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ['3.9', '3.10', '3.11', '3.12', '3.13']  # Add 3.13
```

### Changing Trigger Branches

```yaml
on:
  push:
    branches: [ main, develop, feature/* ]  # Add feature branches
  pull_request:
    branches: [ main ]
```

### Adding Scheduled Runs

Run CI daily at midnight UTC:

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
```

### Making Steps Required

Remove `continue-on-error: true` to make steps mandatory:

```yaml
- name: Run linter (ruff)
  run: uv run ruff check .
  # Remove: continue-on-error: true
```

### Adding New Jobs

Example: Add a deploy job that runs after successful build:

```yaml
deploy:
  runs-on: ubuntu-latest
  needs: [build]
  if: github.ref == 'refs/heads/main'

  steps:
    - name: Deploy to production
      run: echo "Deploying to production..."
```

## Troubleshooting

### Tests Pass Locally But Fail in CI

**Common causes:**

1. **Database path differences**
   - Use `tmp_path` fixture in tests (already configured)
   - Avoid hardcoded paths

2. **Environment variables**
   - Set environment variables in workflow:
   ```yaml
   - name: Run tests
     env:
       FLASK_ENV: testing
     run: uv run pytest -v
   ```

3. **Platform-specific code**
   - Check if code works on all OS (Windows uses `\` for paths)
   - Use `pathlib` instead of string concatenation

### Workflow Not Triggering

1. Check branch name matches trigger condition
2. Ensure `.github/workflows/` directory is in root
3. Verify YAML syntax is correct
4. Check GitHub Actions is enabled in repository settings

### Slow CI Runs

**Optimization tips:**

1. **Cache dependencies:**
   Already enabled with `enable-cache: true` in setup-uv action

2. **Skip unnecessary jobs:**
   ```yaml
   if: "!contains(github.event.head_commit.message, '[skip ci]')"
   ```

3. **Reduce matrix size:**
   ```yaml
   strategy:
     matrix:
       os: [ubuntu-latest]  # Only Ubuntu
       python-version: ['3.11']  # Only one Python version
   ```

4. **Use quick-test workflow:**
   Push to feature branches trigger quick-test only

### Coverage Upload Fails

The Codecov upload is marked as `continue-on-error: true`, so it won't fail the build.

To enable Codecov:
1. Sign up at [codecov.io](https://codecov.io)
2. Add repository
3. Add `CODECOV_TOKEN` to GitHub Secrets:
   - Go to repository Settings → Secrets and variables → Actions
   - Add new secret: `CODECOV_TOKEN`
   - Paste token from Codecov

## Advanced Configuration

### Branch Protection Rules

Require CI to pass before merging:

1. Go to repository **Settings** → **Branches**
2. Add rule for `main` branch
3. Check **Require status checks to pass before merging**
4. Select required checks:
   - `test`
   - `lint`
   - `build`

### Adding Code Coverage Badge

After setting up Codecov:

```markdown
![Coverage](https://codecov.io/gh/yourusername/SSW555-Example-Project/branch/main/graph/badge.svg)
```

### Running CI on Forks

By default, CI runs on pull requests from forks but with limited permissions.

To allow secrets in forks (use carefully):
```yaml
on:
  pull_request_target:  # Has access to secrets
```

⚠️ **Security warning:** Only use `pull_request_target` if you trust contributors

### Caching Build Artifacts

Cache Python packages across runs:

```yaml
- name: Cache uv packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-uv-
```

(Already handled by `setup-uv` action with `enable-cache: true`)

### Adding Deployment

Deploy on successful merge to main:

```yaml
deploy:
  runs-on: ubuntu-latest
  needs: [test, lint, build]
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'

  steps:
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.14
      with:
        heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
        heroku_app_name: "your-app-name"
        heroku_email: "your-email@example.com"
```

### Conditional Job Execution

Run security checks only on main branch:

```yaml
security:
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'
```

Skip CI on documentation changes:

```yaml
on:
  push:
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

### Parallel Testing

Split tests into multiple jobs for speed:

```yaml
test:
  strategy:
    matrix:
      test-group: [models, routes, integration]
  steps:
    - name: Run test group
      run: uv run pytest tests/test_${{ matrix.test-group }}.py
```

## CI Best Practices

### 1. Keep CI Fast
- Target: < 5 minutes for quick feedback
- Use caching aggressively
- Run slow tests nightly only

### 2. Make Tests Deterministic
- Use fixed random seeds
- Mock time-dependent code
- Avoid flaky network calls

### 3. Fail Fast
- Put fastest checks first (linting)
- Run tests in parallel
- Stop on first failure in PR checks

### 4. Clear Error Messages
```python
# Good
assert user.email == "test@example.com", f"Expected test@example.com, got {user.email}"

# Bad
assert user.email == "test@example.com"
```

### 5. Version Pin Critical Dependencies
```toml
dependencies = [
    "flask>=3.1.2,<4.0",  # Pin major version
    "pytest>=8.2",
]
```

### 6. Monitor CI Health
- Set up notifications for failed builds
- Review CI metrics monthly
- Keep dependencies updated

## GitHub Actions Marketplace

Useful actions to enhance CI:

- **[super-linter](https://github.com/github/super-linter)** - Lint multiple languages
- **[dependency-review-action](https://github.com/actions/dependency-review-action)** - Check for vulnerable dependencies
- **[github-action-benchmark](https://github.com/benchmark-action/github-action-benchmark)** - Track performance
- **[pytest-github-actions-annotate-failures](https://github.com/utgwkk/pytest-github-actions-annotate-failures)** - Annotate test failures

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.com/)