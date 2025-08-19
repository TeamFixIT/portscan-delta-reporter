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
- **Flask** (optional web interface)
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
- Recommended: Virtual environment

### Installation

```bash
# Clone repository
git clone https://github.com/your-username/portscan-delta-reporter.git
cd portscan-delta-reporter

# Set up virtual environment
python -m venv venv
source venv/bin/activate   # (Linux/macOS)
venv\Scripts\activate      # (Windows)

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# Run initial baseline scan
python main.py --init --targets targets.txt

# Run a delta scan and generate report
python main.py --scan --report pdf
```

---

## Folder Structure

```
portscan-delta-reporter/
├── data/              # Baseline + scan results
├── reports/           # Generated reports
├── scripts/           # Core scan + compare logic
├── web/               # Optional Flask web interface
├── requirements.txt   # Dependencies
├── main.py            # Entry point
└── README.md          # Project documentation
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
