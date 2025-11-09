# Port Scanner Delta Reporter — *TeamFixIT Legacy Project*
--------------------------------
| **Version:** | `v1.0.0-alpha`                                                       |
| ------------ | -------------------------------------------------------------------- |
| **Status:**  | *Archived (Demo & Portfolio Purposes Only)*                          |
| **License:** | MIT                                                                  |
| **Authors:** | *TeamFixIT — Murdoch University, Bachelor of Information Technology* |

---

## Overview

**Port Scanner Delta Reporter** represents the culmination of our capstone project at **Murdoch University**, developed by **TeamFixIT** — a small but passionate group of aspiring cybersecurity professionals.

Built with **Flask**, this system was designed to **record, compare, and visualise port scan results over time**, providing clear insight into changes in network exposure and configuration drift.

Though now archived, this repository stands as a **symbol of growth, teamwork, and technical excellence**, reflecting the dedication and problem-solving spirit that brought TeamFixIT together.

---

## Project Vision

In a world where network visibility is critical, *Port Scanner Delta Reporter* was created to:

* Simplify **tracking changes** in open ports and services between scans
* Offer a **web-based dashboard** for viewing deltas and history
* Enable **forensic insight** into evolving network surfaces
* Lay the groundwork for a **modular, scalable** security monitoring platform

This project showcases not just our technical proficiency — but our ability to **collaborate, plan, and execute** a complete software lifecycle.

---

## Tech Stack

| Component           | Description               |
| ------------------- | ------------------------- |
| **Language**        | Python 3.9+               |
| **Framework**       | Flask                     |
| **Database**        | SQLAlchemy + SQLite (dev) |
| **Frontend**        | HTML / CSS / Bootstrap    |
| **Deployment**      | Gunicorn / systemd        |
| **Version Control** | Git + GitHub              |

---

## Core Features

* Modular Flask architecture (blueprints, routes, models, services)
* Delta reporting — track differences between port scan results
* Scheduled scan management via background jobs
* Role-based admin system
* Database migration & seeding commands
* CLI utilities for setup, admin creation, and database resets

---

## Quick Start (For Demo Purposes)
```bash
git clone https://github.com/TeamFixIT/portscan-delta-reporter.git
cd portscan-delta-reporter
```
### Server Setup
```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -e .
cp .env.example .env
flask setup
flask create-admin
portscanner-server
```
### Client Setup (New Terminal)
```bash
cd client
python3 -m venv venv
source venv/bin/activate
pip install -e .
portscanner-client-config
portscanner-client
```


Then visit:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## Project Structure

```
server/
├── app/
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   └── templates/
├── run.py
├── pyproject.toml
├── .env.example
└── README.md
```

---

## TeamFixIT — The People Behind the Project

This project would not exist without the creativity, resilience, and collaboration of its contributors:

| Name                       | Role                         | Contribution                                                                                                                                            |
| -------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Jared Stanbrook**        | Project Activity Coordinator | Lead developer and architect; implemented most backend code, integrations, and system logic; coordinated software design and development direction.     |
| **Numan Sayyed**           | Secretary                    | Supported project documentation and organisation; contributed to meeting notes and version tracking.                                                    |
| **Joey Kennedy**           | Communications Officer       | Assisted with UI design and Flask templates; helped coordinate collaboration and document flow between members.                                         |
| **Andrew Percy**           | Software Coordinator         | Contributed to technical diagrams and research; assisted with software design decisions influenced by Jared’s architecture.                             |
| **Solomon Spilsbury-Slee** | Document Controller          | Led creation and structuring of project documentation; ensured consistency across deliverables; collaborated closely with Joey and Jared for alignment. |
| **Louis Wang**             | Security Coordinator         | Contributed to documentation and research on security considerations within the project.                                                                |


---

## Project Legacy

> *"Port Scanner Delta Reporter taught us how to think like engineers, plan like professionals, and collaborate like a real team."*

This project became more than just a deliverable — it was a **shared journey** of late nights, debugging marathons, and creative breakthroughs.
It inspired TeamFixIT’s founding principles:

> **Integrity, Curiosity, and Teamwork.**

As we archive this repository, we do so with immense pride — as a public record of what passion and persistence can create.

---

## License

This project is released under the **MIT License**.
You are welcome to explore, learn from, and adapt our work — with attribution to **TeamFixIT**.

---

## Final Words

> “Failure is only the start of programming it’s a lot about getting hit down and getting back up and tying again!”
> — *Jared Stanbrook, 04/10/2025*