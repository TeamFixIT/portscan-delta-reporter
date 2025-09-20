# Contributing Guidelines

Welcome to the **Port Scan & Delta Reporter** project!  
We’re a team of 6 collaborating on this repo. To keep our workflow clean, please follow these rules:

---

## 🔀 Workflow

1. **Sync main**

   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a branch**

   - Use a descriptive name:
     - `feature/<short-description>`
     - `bugfix/<short-description>`
     - `docs/<short-description>`

   ```bash
   git checkout -b feature/add-authentication
   ```

3. **Commit changes**

   - Use the commit message template:
   - Reference `.github/COMMIT_TEMPLATE.md`

   - Follow the format: `<type>(<scope>): <subject>`
     - **Good:** `feat(server): add user authentication with Flask-Login`
     - **Good:** `fix(client): resolve MAC address detection on Pi4`
     - **Good:** `docs: update README with installation instructions`
     - **Bad:** `fixed stuff` or `Updated files`

4. **Push branch**

   ```bash
   git push origin feature/add-authentication
   ```

5. **Open a Pull Request**

   - Target: `main`
   - Fill in the PR template (if available).
   - Link related Issues (`Closes #12`).

6. **Code Review**

   - At least **1 reviewer must approve** (branch protection enforces this).
   - Resolve all conversations before merging.

7. **Merge**
   - Squash merge or rebase merge → no messy merge commits.
   - Only after all status checks pass.

---

## ✅ Code Standards

- Follow project coding style (linting, formatting).
- Document new functions/classes.
- Update tests if you add or change functionality.

---

## 🛡 Branch Protection Rules

- **No direct pushes to `main`**.
- **All changes must go through PRs**.
- **Force pushes and deletions are disabled**.

---

## 💬 Communication

- Use GitHub Issues to track bugs/features.
- Use Pull Request comments for code discussions.
- Tag the right people with `@username` when you need input.

---

Thanks for contributing! 🚀  
— The TeamFixIT Crew
