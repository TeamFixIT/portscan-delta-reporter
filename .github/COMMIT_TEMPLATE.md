# AI Commit Message Template

This template is designed for commit message generation.

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

## AI Instructions for Commit Messages

### 1. Analyse the Changes

- Review modified files and their content
- Identify the primary purpose of the changes
- Determine the most appropriate type and scope
- Consider the impact on users and other developers

### 2. Type Selection

Choose the most appropriate type:

- **feat**: New functionality that adds value to users
- **fix**: Resolves a bug or issue
- **docs**: Documentation updates, README changes
- **style**: Code formatting, whitespace, no logic changes
- **refactor**: Code restructuring without changing functionality
- **perf**: Performance improvements
- **test**: Adding or modifying tests
- **build**: Build system, dependencies, packaging changes
- **ci**: CI/CD pipeline modifications
- **chore**: Maintenance tasks, tooling updates
- **revert**: Reverting previous commits

### 3. Scope Guidelines

Select the most relevant scope:

- **server**: Flask backend, API, database models
- **client**: Raspberry Pi scanning client code
- **infra**: Docker, systemd, deployment configuration
- **docs**: Documentation files, README updates
- **models**: Database schemas, SQLAlchemy models
- **api**: REST endpoints, request/response handling
- **ui**: Templates, CSS, JavaScript, user interface
- **auth**: Authentication, authorization, user management
- **scan**: Network scanning logic, nmap integration
- **report**: Delta reporting, PDF generation
- **config**: Configuration files, environment setup

### 4. Subject Line Rules

- Use imperative mood (add, fix, update, remove)
- Start with lowercase letter
- No period at the end
- Maximum 50 characters
- Be specific and descriptive
- Focus on WHAT was done, not HOW

### 5. Body Guidelines (when needed)

Include body for:

- Complex changes requiring explanation
- Breaking changes
- Non-obvious decisions
- Context for future developers

Format:

- Wrap at 72 characters
- Explain WHY and WHAT, not HOW
- Use bullet points for multiple items
- Reference related issues or PRs

### 6. Footer Format

Include when applicable:

- `Closes #123` or `Fixes #456` for issue references
- `BREAKING CHANGE: description` for breaking changes
- `Co-authored-by: Name <email>` for collaboration

## Project-Specific Context

### Technology Stack

- **Backend**: Flask, SQLAlchemy, Flask-Login, SocketIO
- **Frontend**: Jinja2 templates, Bootstrap, vanilla JS
- **Client**: Python, nmap, psutil, netifaces
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Infrastructure**: Docker, systemd services

### Key Features

- Network port scanning via Raspberry Pi clients
- MAC address-based host tracking for dynamic IPs
- Delta reporting between scan results
- Real-time client-server communication
- PDF/CSV report generation
- Web dashboard for monitoring

### Common Change Patterns

- Adding new scan functionality
- Improving delta detection algorithms
- Updating client-server communication
- Enhancing web dashboard features
- Database schema modifications
- Configuration and deployment updates

## Example Commit Messages

### Good Examples

```
feat(scan): add port range validation for client requests

Implement validation logic to ensure port ranges are within
acceptable limits (1-65535) and properly formatted before
sending scan tasks to Raspberry Pi clients.

Closes #42
```

```
fix(client): resolve MAC address detection on newer Pi models

The netifaces library returns different interface names on
Pi 4 Model B Rev 1.5. Updated detection logic to handle
various interface naming patterns.
```

```
docs: update installation guide with separate venv setup

Add instructions for creating isolated virtual environments
for server and client components to prevent dependency
conflicts during deployment.
```

```
refactor(models): optimize database queries for large scan results

Replace N+1 queries with eager loading for scan results and
associated port data. Improves dashboard loading time by ~60%
for datasets with 1000+ scan results.
```

### Avoid These Patterns

- `fix: bug fixes`
- `update: various changes`
- `feat: new stuff`
- `chore: cleanup`
- `refactor: code improvements`

## AI Decision Tree

When writing commits, follow this decision tree:

1. **What files changed?**

   - Server files → scope: server/api/models/ui
   - Client files → scope: client/scan
   - Config files → scope: infra/config
   - Docs → scope: docs

2. **What type of change?**

   - New functionality → feat
   - Bug resolution → fix
   - Code organization → refactor
   - Documentation → docs
   - Performance → perf

3. **Does it need a body?**

   - Complex logic changes → Yes
   - Breaking changes → Yes
   - Simple fixes → No
   - Configuration updates → Maybe

4. **Any issues referenced?**
   - Bug fixes → Include issue number
   - Feature implementation → Include feature request
   - General improvements → Optional

Use this template to generate consistent, informative commit messages that help the team understand the evolution of the codebase.
