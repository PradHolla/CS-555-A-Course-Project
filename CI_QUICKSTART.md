# CI Quick Start Guide 🚀

Your GitHub Actions CI is ready to go! Here's what you need to know:

## What Happens Automatically

Every time you push code or create a pull request:

✅ **Tests run** - All 25+ tests execute on 3 operating systems
✅ **Code quality checks** - Ruff linter validates your code style
✅ **Security scans** - Bandit checks for security vulnerabilities
✅ **Build verification** - Flask app starts successfully
✅ **Coverage reports** - Code coverage tracked (optional Codecov integration)

**Total: ~50 automated checks per push!**

## First Push

1. **Update README badges** (replace `yourusername`):
   ```markdown
   ![CI](https://github.com/YOUR_USERNAME/SSW555-Example-Project/workflows/CI/badge.svg)
   ![Tests](https://github.com/YOUR_USERNAME/SSW555-Example-Project/workflows/Quick%20Test/badge.svg)
   ```

2. **Commit and push:**
   ```bash
   git add .
   git commit -m "Add GitHub Actions CI"
   git push
   ```

3. **View results:**
   - Go to **Actions** tab in your GitHub repository
   - Watch your CI pipeline run!

## CI Status

### On GitHub
- **Actions tab** - See all workflow runs
- **Pull Requests** - CI status shown on each PR
- **README badges** - Quick status overview

### Badges Meaning
- 🟢 **Passing** - All checks passed
- 🔴 **Failing** - Some checks failed
- 🟡 **Running** - CI in progress

## Run Checks Locally (Before Pushing)

```bash
# Install dev tools
uv pip install ".[dev]"

# Run tests
uv run pytest -v

# Check code style
uv run ruff check .

# Format code
uv run ruff format .

# Security scan
uv run bandit -r .
```

## CI Workflows

### 1. Main CI (`ci.yml`)
- **Comprehensive testing** on multiple OS and Python versions
- **Duration:** ~5-10 minutes
- **When:** Every push/PR to main or develop

### 2. Quick Test (`quick-test.yml`)
- **Fast feedback** with core tests only
- **Duration:** ~1-2 minutes
- **When:** Every push/PR to main or develop

## Enable Branch Protection (Recommended)

Require CI to pass before merging:

1. Go to **Settings** → **Branches**
2. Add rule for `main` branch
3. Check **Require status checks to pass before merging**
4. Select: `test`, `lint`, `build`
5. Save

## Optional: Codecov Setup

Track code coverage over time:

1. Sign up at [codecov.io](https://codecov.io)
2. Connect your repository
3. Add `CODECOV_TOKEN` to GitHub Secrets
4. Coverage badge will appear automatically

## Need Help?

- 📖 **Full CI Guide:** [docs/CI.md](docs/CI.md)
- 🔧 **GitHub Actions Setup:** [.github/README.md](.github/README.md)
- 🐛 **Troubleshooting:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

**That's it!** Your CI is now running automatically. 🎉

Push code and watch the magic happen in the Actions tab!
