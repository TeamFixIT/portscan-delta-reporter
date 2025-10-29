# services/alert_service.py
from datetime import datetime
from app import db
from app.models.alert import Alert

from app.logging_config import get_logger

logger = get_logger(__name__)

# Hardcoded critical ports for now (TODO: make user-configurable)
CRITICAL_PORTS = {
    22: {"service": "SSH", "criticality": "high"},
    23: {"service": "Telnet", "criticality": "high"},
    3389: {"service": "RDP", "criticality": "critical"},
    445: {"service": "SMB", "criticality": "high"},
    21: {"service": "FTP", "criticality": "medium"},
    3306: {"service": "MySQL", "criticality": "medium"},
    5900: {"service": "VNC", "criticality": "high"},
}


def check_for_critical_ports(scan_result_id: str, parsed_results: dict):
    """
    Check parsed scan results for critical ports and create or resolve alerts.
    """
    created_alerts, resolved_alerts = [], []

    # Find all active alerts for context
    active_alerts = Alert.query.filter(Alert.status.in_(["warned", "actioned"])).all()
    active_lookup = {(a.device_ip, a.port): a for a in active_alerts}

    # Track ports that are currently open per scan
    current_open_ports = {
        (ip, port)
        for ip, data in parsed_results.items()
        for port in data.get("open_ports", [])
    }

    # Create new alerts for new critical ports
    for ip, data in parsed_results.items():
        for port in data.get("open_ports", []):
            if port in CRITICAL_PORTS:
                info = CRITICAL_PORTS[port]
                key = (ip, port)

                # Skip if alert already exists
                if key in active_lookup:
                    continue

                alert = Alert(
                    device_ip=ip,
                    port=port,
                    service=info["service"],
                    criticality=info["criticality"],
                    message=f"Critical service {info['service']} detected open on {ip}:{port}",
                    scan_result_id=scan_result_id,
                )

                db.session.add(alert)
                created_alerts.append(alert)
                logger.warning(f"ALERT CREATED: {alert.message}")

                # TODO: trigger SSE/email notification
                # send_alert_via_email(alert)
                # send_sse_alert(alert)

    # Resolve alerts for ports that were open but now closed
    for (ip, port), alert in active_lookup.items():
        if (ip, port) not in current_open_ports and port in CRITICAL_PORTS:
            alert.mark_resolved()
            resolved_alerts.append(alert)
            logger.info(f"ALERT RESOLVED: {ip}:{port} closed — no longer critical")

            # TODO: send SSE/email notification of resolution
            # send_alert_resolution(alert)

    if created_alerts or resolved_alerts:
        db.session.commit()
        logger.info(
            f"Alerts updated: {len(created_alerts)} created, {len(resolved_alerts)} resolved"
        )
    else:
        logger.debug("No alert changes this cycle.")

    return created_alerts, resolved_alerts
