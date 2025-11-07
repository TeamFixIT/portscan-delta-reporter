---
layout: default
title: Installation
parent: Client
nav_order: 1
---

# Client Installation Guide
{: .no_toc }

Complete installation guide for the Port Scanner Client Agent.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

Before installing the client agent, ensure your system meets these requirements:

### Required Software

- **Python 3.9 or higher**
- **Nmap** - Network scanning tool

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 512MB | 1GB+ |
| Disk Space | 1GB | 2GB+ |
| Network | Basic connectivity | Stable connection to server |

### Operating Systems

Tested and supported on:
- Ubuntu 20.04+ / Debian 10+
- macOS 11+ (Big Sur and later)
- Raspberry Pi OS (Bullseye and later)

---

## Install Nmap

The client requires `nmap` to be installed on your system.

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install nmap
```

### macOS

```bash
brew install nmap
```

### Verify Installation

```bash
nmap --version
```

You should see output like:
```
Nmap version 7.80 ( https://nmap.org )
```

---

## Quick Start

The fastest way to get started:

```bash
# 1. Install the package
pip install .

# 2. Run the configuration wizard
portscanner-client-config

# 3. Start the client
portscanner-client
```

---

## Detailed Installation

### Step 1: Create Virtual Environment

It's recommended to use a virtual environment to isolate dependencies:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate     # On Windows
```

### Step 2: Install the Client Package

#### Option A: Install from Source (Development)

```bash
pip install -e .
```

This creates an editable installation, useful for development.

#### Option B: Install with Development Dependencies

```bash
pip install -e ".[dev]"
```

Includes testing and development tools.

#### Option C: Regular Installation

```bash
pip install .
```

Standard installation for production use.

### Step 3: Verify Installation

Check that the commands are available:

```bash
portscanner-client --help
portscanner-client-config --help
```