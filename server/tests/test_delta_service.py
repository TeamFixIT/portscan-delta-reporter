from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.services.delta_service import DeltaReportService


@dataclass
class StubResult:
    id: int
    scan_id: int
    parsed_results: dict
    total_open_ports: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


def test_calculate_delta_is_deterministic():
    baseline = StubResult(
        id=1,
        scan_id=10,
        parsed_results={
            "10.0.0.1": {
                "hostname": "host-1",
                "state": "up",
                "open_ports": [22, 80],
                "port_details": {
                    "22": {"protocol": "tcp", "name": "ssh", "product": "OpenSSH"},
                    "80": {"protocol": "tcp", "name": "http", "product": "nginx"},
                },
            },
            "10.0.0.2": {
                "hostname": "host-2",
                "state": "up",
                "open_ports": [443],
                "port_details": {
                    "443": {"protocol": "tcp", "name": "https", "product": "nginx"}
                },
            },
        },
        total_open_ports=3,
        started_at=datetime(2026, 2, 4, tzinfo=timezone.utc),
        completed_at=datetime(2026, 2, 4, 1, tzinfo=timezone.utc),
    )
    current = StubResult(
        id=2,
        scan_id=10,
        parsed_results={
            "10.0.0.1": {
                "hostname": "host-1",
                "state": "up",
                "open_ports": [22, 8080],
                "port_details": {
                    "22": {
                        "protocol": "tcp",
                        "name": "ssh",
                        "product": "OpenSSH",
                        "version": "9.0",
                    },
                    "8080": {"protocol": "tcp", "name": "http-alt", "product": ""},
                },
            },
            "10.0.0.3": {
                "hostname": "host-3",
                "state": "up",
                "open_ports": [443],
                "port_details": {
                    "443": {"protocol": "tcp", "name": "https", "product": "caddy"}
                },
            },
        },
        total_open_ports=3,
        started_at=datetime(2026, 2, 4, 2, tzinfo=timezone.utc),
        completed_at=datetime(2026, 2, 4, 3, tzinfo=timezone.utc),
    )

    delta = DeltaReportService()._calculate_delta(baseline, current)

    assert delta["delta"]["new_up_hosts"] == ["10.0.0.3"]
    assert delta["delta"]["new_down_hosts"] == ["10.0.0.2"]
    assert [item["port"] for item in delta["delta"]["added_ports"]] == [8080, 443]
    assert [item["port"] for item in delta["delta"]["removed_ports"]] == [80, 443]
    assert delta["summary"]["new_ports_count"] == 2
    assert delta["summary"]["closed_ports_count"] == 2
    assert delta["summary"]["changed_services_count"] == 1
    assert delta["report"]["scan_id"] == 10
    assert delta["scan_window"]["baseline_completed_at"].endswith("+00:00")
