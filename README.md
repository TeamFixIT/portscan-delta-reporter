# PortScan Delta Reporter

PortScan Delta Reporter is a tool developed by **TeamFixIT** for Murdoch University. Its purpose is to automate network port scanning, track changes over time, and generate clear reports highlighting differences (deltas) between scans.

---

## Features

- **Automated Port Scanning** – Runs scans against defined hosts and IP ranges using `nmap`.
- **Baseline Storage** – Stores results from the first scan as a reference point.
- **Delta Detection** – Compares new scan results with the baseline to identify:
  - Newly opened ports
  - Closed ports
  - Service version changes
- **Reporting** – Generates human-readable reports in PDF/CSV/HTML.
- **Scheduling** – Supports automated recurring scans (via cron or scheduler).

---

## Tech Stack

- **Python** (backend logic)
- **nmap / python-nmap** (port scanning)
- **SQLite** (storing baseline + scan results)
- **Flask** (web interface)
- **ReportLab / Pandas** (report generation)

---

## Project Goals

This project is being built as part of an academic engagement with Murdoch University. The client, **Communications and Service Manager Jarren Beveridge**, requires a solution that:

- Clearly reports on network changes
- Provides actionable insights without excessive technical jargon
- Can be run and understood by non-technical stakeholders

---

## Getting Started

### Prerequisites

- Python 3.10+
- `nmap` installed on system
- Git

### Quick Setup

**For Server:**

```bash
cd server
./setup.sh
```

**For Client (Raspberry Pi):**

```bash
cd client
./setup.sh
```

### Manual Installation

**Server Setup:**

```bash
# Navigate to server directory
cd server

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python run.py init-db

# Start server
python run.py
```

**Client Setup:**

```bash
# Navigate to client directory
cd client

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit config
cp config.example.yml config.yml
# Edit config.yml with your server details

# Start client
python client_agent.py
```

---

## Folder Structure

```
/ (root)
├─ server/                        # Main server app (Flask)
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ models/                  # DB models (SQLAlchemy)
│  │  ├─ routes/                  # REST + web routes
│  │  ├─ templates/               # Jinja2/HTML templates for UI
│  │  ├─ static/                  # CSS/JS
│  │  ├─ utils/                   # helpers: validation, ip-clamp, delta
│  ├─ migrations/                 # alembic/flyway (if needed)
│  ├─ tests/
│  └─ requirements.txt
├─ client/                        # Pi4 scanning client
│  ├─ client_agent.py
│  ├─ config.example.yml
│  ├─ utils/
│  ├─ tests/
│  └─ requirements.txt
├─ infra/                         # k8s / systemd service files / docker-compose
├─ docs/                          # design docs, API spec
├─ output/                        # generated PDFs, reports
├─ scan_results/                  # JSON blobs (or can be outside repo)
├─ uploads/                       # uploaded files (if any)
├─ .github/                       # CI workflows
└─ README.md
```

---

## Roadmap

- [ ] Build core scanning + baseline storage
- [ ] Implement delta detection logic
- [ ] Add reporting engine
- [ ] Create Flask web dashboard
- [ ] Add scheduling support
- [ ] Polish UI/UX for client delivery

---

## License

This project is developed for academic purposes by **TeamFixIT**. Licensing details to be confirmed.

---

## Authors

- TeamFixIT (Murdoch University)
