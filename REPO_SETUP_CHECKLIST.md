# Repository Setup Checklist

**Complete this BEFORE your team starts development**

---

## ✅ Local Setup

### 1. Create `develop` Branch

```bash
# Make sure you're on main and up to date
git checkout main
git pull origin main

# Create develop branch
git checkout -b develop

# Push to GitHub
git push -u origin develop
```

**Expected output:**
```
Total 0 (delta 0), reused 0 (delta 0), pack-reused 0
To https://github.com/PradHolla/CS-555-A-Course-Project.git
 * [new branch]      develop -> develop
branch 'develop' set up to track 'origin/develop'.
```

✅ **Verify:** Go to GitHub → Branches → Should see `main` and `develop`

---

## ✅ GitHub Settings

### 2. Set Up Branch Protection for `main`

**Steps:**
1. Go to: https://github.com/PradHolla/CS-555-A-Course-Project/settings/branches
2. Click "Add branch protection rule"
3. Branch name pattern: `main`
4. Enable these settings:
   - ✅ **Require a pull request before merging**
     - Require approvals: **1**
     - Dismiss stale pull request approvals when new commits are pushed
   - ✅ **Require status checks to pass before merging**
     - Search and add these checks (they'll appear after first CI run):
       - `test (3.9, ubuntu-latest)`
       - `test (3.10, ubuntu-latest)`
       - `test (3.11, ubuntu-latest)`
       - `test (3.12, ubuntu-latest)`
     - ✅ Require branches to be up to date before merging
   - ✅ **Require conversation resolution before merging**
   - ✅ **Include administrators** (you should also follow the rules!)
5. Click "Create" at the bottom

✅ **Verify:** You should see a green shield icon next to `main` branch

### 3. Set Up Branch Protection for `develop`

**Steps:**
1. Click "Add branch protection rule" again
2. Branch name pattern: `develop`
3. Enable these settings:
   - ✅ **Require a pull request before merging**
     - Require approvals: **1**
   - ✅ **Require status checks to pass before merging**
     - Add same test checks as `main`
   - ✅ **Require conversation resolution before merging**
4. Click "Create"

✅ **Verify:** You should see a green shield icon next to `develop` branch

### 4. Change Default Branch to `develop`

**Steps:**
1. Go to: https://github.com/PradHolla/CS-555-A-Course-Project/settings
2. Scroll down to "Default branch"
3. Click the ⇄ switch icon
4. Select `develop` from dropdown
5. Click "Update"
6. Confirm by clicking "I understand, update the default branch"

✅ **Verify:** Default branch should now show `develop` (not `main`)

**Why this matters:** When teammates run `git clone`, they'll automatically be on `develop` branch.

### 5. Add Team Members as Collaborators

**Steps:**
1. Go to: https://github.com/PradHolla/CS-555-A-Course-Project/settings/access
2. Click "Add people"
3. Enter teammate's GitHub username or email
4. Select role: **Write** (allows push but not admin changes)
5. Click "Add [username] to this repository"
6. Repeat for each team member

✅ **Verify:** All team members appear in the Collaborators list

**They'll receive an invitation email** - make sure they accept it!

---

## ✅ Optional but Recommended

### 6. Create Project Board

**Steps:**
1. Go to: https://github.com/PradHolla/CS-555-A-Course-Project/projects
2. Click "New project"
3. Choose "Board" template
4. Name it: "CS-555 Sprint Board"
5. Add columns:
   - 📋 **To Do**
   - 🚧 **In Progress**
   - 👀 **In Review**
   - ✅ **Done**

✅ **Verify:** Board is visible under Projects tab

### 7. Create Initial Issues

Create some starter issues for your team:

**Example Issues:**

1. **Issue #1: Add expense category field**
   - Label: `enhancement`
   - Description: "Add a category field (Food, Transport, Entertainment, Other) to expense tracking"
   - Acceptance Criteria: Backend model updated, tests added, UI updated

2. **Issue #2: Add expense edit functionality**
   - Label: `enhancement`
   - Description: "Allow users to edit existing expenses"

3. **Issue #3: Improve expense split calculation display**
   - Label: `enhancement`
   - Description: "Show who owes what more clearly in the UI"

✅ **Verify:** Issues appear under Issues tab

### 8. Set Up Issue Templates (Optional)

**Steps:**
1. Go to: https://github.com/PradHolla/CS-555-A-Course-Project/settings
2. Click "Set up templates" under Issues
3. Add "Bug report" template
4. Add "Feature request" template
5. Commit to `develop` branch

---

## ✅ Verification Checklist

Before telling your team to start:

- [ ] `develop` branch exists on GitHub
- [ ] `main` branch has protection rules (1 approval, CI checks)
- [ ] `develop` branch has protection rules (1 approval, CI checks)
- [ ] Default branch is set to `develop`
- [ ] All team members added as collaborators
- [ ] All team members accepted invitation
- [ ] GitHub Actions CI is working (check Actions tab)
- [ ] Project board created (optional)
- [ ] Initial issues created (optional)

---

## 📢 Share with Team

Once setup is complete, share this with your team:

```
🎉 Repository is ready for development!

📖 Read the workflow: TEAM_WORKFLOW.md

🚀 Get started:
1. Clone repo: git clone https://github.com/PradHolla/CS-555-A-Course-Project.git
2. Install UV: see TEAM_WORKFLOW.md
3. Run: uv sync
4. Verify: uv run pytest -v
5. Start coding! Follow the 9-step process in TEAM_WORKFLOW.md

📋 Pick a ticket from: https://github.com/PradHolla/CS-555-A-Course-Project/issues
```

---

## 🆘 Troubleshooting

**Problem:** Can't push to `main` - "protected branch"
- ✅ **Expected!** You must create a PR, never push directly to `main`

**Problem:** CI checks not showing up in branch protection
- Run a workflow first (push any branch)
- Wait for it to complete
- Then the check names will appear in the dropdown

**Problem:** Teammate can't push - "permission denied"
- Make sure they accepted the collaborator invitation (check email)
- Verify they're listed under Settings → Collaborators
- Make sure they have "Write" access (not "Read")

**Problem:** `develop` branch not showing as default
- Check Settings → General → Default branch
- Click the switch icon and select `develop`
- Confirm the change

---

## ✅ Done!

Your repository is now ready for team development! 🎉

Delete this file once setup is complete, or keep it for reference.
