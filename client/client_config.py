#!/usr/bin/env python3
"""
Port Scanner Client Configuration Wizard
"""
import sys
from pathlib import Path
import yaml


def configure():
    """Interactive configuration wizard for the client"""
    try:
        import questionary
    except ImportError:
        print("Error: questionary not installed. Install with: pip install questionary")
        return 1

    cfg_path = Path.cwd() / "config.yml"

    print("\n" + "=" * 60)
    print("Port Scanner Client Configuration Wizard")
    print("=" * 60 + "\n")

    # Check if config exists
    if cfg_path.exists():
        if not questionary.confirm(
            "config.yml already exists. Overwrite?", default=False
        ).ask():
            print("Configuration cancelled.")
            return 0

    # Ask questions
    try:
        answers = questionary.prompt(
            [
                {
                    "type": "text",
                    "name": "server_url",
                    "message": "Server URL:",
                    "default": "http://localhost:5000",
                },
                {
                    "type": "text",
                    "name": "client_port",
                    "message": "Client listening port:",
                    "default": "8080",
                },
                {
                    "type": "text",
                    "name": "client_host",
                    "message": "Client bind host:",
                    "default": "0.0.0.0",
                },
                {
                    "type": "text",
                    "name": "chunk_size",
                    "message": "Chunk size (targets per chunk):",
                    "default": "1",
                },
                {
                    "type": "text",
                    "name": "per_target_timeout",
                    "message": "Per-target timeout (seconds):",
                    "default": "120",
                },
                {
                    "type": "text",
                    "name": "progress_report_interval",
                    "message": "Progress report interval (seconds):",
                    "default": "10",
                },
                {
                    "type": "text",
                    "name": "heartbeat_interval",
                    "message": "Heartbeat interval (seconds):",
                    "default": "60",
                },
                {
                    "type": "text",
                    "name": "check_approval_interval",
                    "message": "Check approval interval (seconds):",
                    "default": "30",
                },
                {
                    "type": "text",
                    "name": "retry_attempts",
                    "message": "Retry attempts:",
                    "default": "3",
                },
                {
                    "type": "text",
                    "name": "retry_delay",
                    "message": "Retry delay (seconds):",
                    "default": "5",
                },
                {
                    "type": "text",
                    "name": "scan_range",
                    "message": "Scan range (CIDR):",
                    "default": "192.168.0.0/24",
                },
                {
                    "type": "text",
                    "name": "client_id",
                    "message": "Optional client ID (leave blank to auto-detect):",
                    "default": "",
                },
                {
                    "type": "text",
                    "name": "hostname",
                    "message": "Optional hostname (leave blank to auto-detect):",
                    "default": "",
                },
            ]
        )
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
        return 0

    if not answers:
        print("Configuration cancelled.")
        return 0

    # Convert numeric strings to integers
    numeric_fields = [
        "client_port",
        "chunk_size",
        "per_target_timeout",
        "progress_report_interval",
        "heartbeat_interval",
        "check_approval_interval",
        "retry_attempts",
        "retry_delay",
    ]

    for field in numeric_fields:
        if field in answers and answers[field]:
            try:
                answers[field] = int(answers[field])
            except ValueError:
                pass

    # Remove empty values
    data = {k: v for k, v in answers.items() if v and v != ""}

    # Write config
    try:
        cfg_path.write_text(
            yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
        )
        print(f"\n✓ Configuration saved to {cfg_path}")
        print("\nYou can now run: portscanner-client")
        return 0
    except Exception as e:
        print(f"\n✗ Error writing config: {e}")
        return 1


def main():
    """Entry point wrapper"""
    sys.exit(configure())


if __name__ == "__main__":
    main()
