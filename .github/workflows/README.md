# GitHub Actions Workflows

This directory contains GitHub Actions workflows for Continuous Integration (CI).

## Workflows

### 1. CI Workflow (`ci.yml`)

**Full CI pipeline with comprehensive testing**

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**What it does:**
- ✅ Runs tests on Ubuntu, macOS, Windows
- ✅ Tests with Python 3.9, 3.10, 3.11, 3.12
- ✅ Generates code coverage reports
- ✅ Runs linting with Ruff
- ✅ Performs security scanning with Bandit
- ✅ Verifies app builds and starts

**Duration:** ~5-10 minutes

### 2. Quick Test Workflow (`quick-test.yml`)

**Lightweight, fast CI for rapid feedback**

**Triggers:**
- Same as CI workflow

**What it does:**
- ✅ Runs tests on Ubuntu with Python 3.11
- ✅ Verifies app starts

**Duration:** ~1-2 minutes

## First-Time Setup

### 1. Enable GitHub Actions

GitHub Actions is enabled by default for public repositories. For private repositories:

1. Go to repository **Settings** → **Actions** → **General**
2. Under "Actions permissions", select **Allow all actions and reusable workflows**
3. Click **Save**

### 2. Update Badge URLs

In `README.md`, replace `yourusername` with your GitHub username:

```markdown
![CI](https://github.com/YOUR_USERNAME/SSW555-Example-Project/workflows/CI/badge.svg)
![Tests](https://github.com/YOUR_USERNAME/SSW555-Example-Project/workflows/Quick%20Test/badge.svg)
```

### 3. (Optional) Set Up Codecov

For code coverage reports:

1. Sign up at [codecov.io](https://codecov.io)
2. Connect your GitHub repository
3. Copy the upload token
4. Add to repository secrets:
   - Go to **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `CODECOV_TOKEN`
   - Value: Paste your token
5. Coverage badge will be available at:
   ```markdown
   ![Coverage](https://codecov.io/gh/yourusername/SSW555-Example-Project/branch/main/graph/badge.svg)
   ```

## Viewing CI Results

### On GitHub

1. Go to the **Actions** tab in your repository
2. Click on a workflow run to see details
3. Click on individual jobs to see logs

### Status Badges

The badges in README.md show the current status:
- ✅ Green = Passing
- ❌ Red = Failing
- 🟡 Yellow = In progress

### Pull Requests

CI status appears automatically on pull requests:
- All checks must pass before merging (if branch protection is enabled)
- Click "Details" next to each check to see logs

## Running Checks Locally

Before pushing, run the same checks locally:

```bash
# Install dev dependencies
uv pip install ".[dev]"

# Run tests
uv run pytest -v

# Run linter
uv run ruff check .

# Run formatter
uv run ruff format --check .

# Run security check
uv run bandit -r .
```

## Customization

### Change Trigger Branches

Edit the `on` section in workflow files:

```yaml
on:
  push:
    branches: [ main, develop, feature/* ]
  pull_request:
    branches: [ main ]
```

### Add/Remove Python Versions

Edit the matrix in `ci.yml`:

```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.11']  # Remove 3.10, 3.12
```

### Add/Remove Operating Systems

```yaml
strategy:
  matrix:
    os: [ubuntu-latest]  # Only Linux
```

### Make Checks Required

Remove `continue-on-error: true` from steps you want to be mandatory.

### Add New Jobs

Example: Add a deployment job:

```yaml
deploy:
  runs-on: ubuntu-latest
  needs: [build]
  if: github.ref == 'refs/heads/main'

  steps:
    - name: Deploy to production
      run: echo "Deploying..."
```

## Branch Protection

To require CI to pass before merging:

1. Go to **Settings** → **Branches**
2. Click **Add rule** or edit existing rule
3. Branch name pattern: `main`
4. Check **Require status checks to pass before merging**
5. Search and select required checks:
   - `test`
   - `lint`
   - `build`
6. Check **Require branches to be up to date before merging**
7. Click **Create** or **Save changes**

## Troubleshooting

### Workflow not running

- Check that workflow files are in `.github/workflows/`
- Verify YAML syntax (use [YAML Linter](https://www.yamllint.com/))
- Ensure branch name matches trigger conditions
- Check that Actions is enabled in repository settings

### Tests pass locally but fail in CI

- Check for hardcoded paths (use `pathlib`)
- Verify environment variables
- Check for platform-specific code (Windows vs Linux/Mac)
- Review CI logs for detailed error messages

### Slow CI runs

- Enable caching (already done)
- Reduce matrix size (fewer OS/Python versions)
- Use `quick-test.yml` for feature branches
- Run expensive checks nightly only

## Resources

- 📖 [Full CI/CD Documentation](../docs/CI.md)
- 🔧 [GitHub Actions Documentation](https://docs.github.com/en/actions)
- 🧪 [pytest Documentation](https://docs.pytest.org/)
- ✨ [Ruff Documentation](https://docs.astral.sh/ruff/)

---

**Questions?** See [docs/CI.md](../docs/CI.md) for comprehensive CI/CD guide.
