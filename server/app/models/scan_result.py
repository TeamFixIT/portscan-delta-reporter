from datetime import datetime
from app import db
from typing import Dict, Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON


class ScanResult(db.Model):
    """
    Aggregated scan results from all clients
    Single table that consolidates results from multiple clients
    """

    __tablename__ = "scan_results"

    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    scan_id = db.Column(
        db.Integer, db.ForeignKey("scans.id"), nullable=False, index=True
    )

    # Overall status
    status = db.Column(db.String(32), default="pending", index=True)

    # Breakdown of scan data for easy querying
    # Structure: {
    #   "192.168.1.1": {
    #       "hostname": "router.local",
    #       "state": "up",
    #       "open_ports": [53, 80, 443],
    #       "port_details": {
    #           "53": {"name": "domain", "product": "", "version": ""},
    #           "80": {"name": "http", "product": "nginx", "version": "1.18"}
    #       }
    #   }
    # }
    parsed_results = db.Column(db.JSON, default=dict)

    # Summary statistics
    total_targets = db.Column(db.Integer, default=0)
    completed_targets = db.Column(db.Integer, default=0)
    failed_targets = db.Column(db.Integer, default=0)
    total_open_ports = db.Column(db.Integer, default=0)

    # Contributing clients
    contributing_clients = db.Column(
        db.JSON, default=list
    )  # List of client_ids that contributed

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<ScanResult {self.result_id} - {self.status} ({self.completed_targets}/{self.total_targets})>"

    def update(self, result_data: Dict) -> bool:
        """
        Update scan result with data from a client

        Args:
            result_data: Dictionary containing scan results from client

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            target = result_data.get("target")
            print(target)
            client_id = result_data.get("client_id")
            status = result_data.get("status", "completed")
            if not target or not client_id:
                return False

            # Initialize target_results and parsed_results if needed
            if self.target_results is None:
                self.target_results = {}
            if self.parsed_results is None:
                self.parsed_results = {}

            # Store complete result with full nmap output
            self.target_results[target] = {
                "client_id": client_id,
                "timestamp": result_data.get(
                    "timestamp", datetime.utcnow().isoformat()
                ),
                "status": status,
                "nmap_output": result_data.get("nmap_output", {}),
                "error_message": result_data.get("error_message"),
            }
            print(self.target_results[target])

            # Parse and store breakdown for easy querying
            if status == "completed" and "nmap_output" in result_data:
                self.parsed_results[target] = self._parse_nmap_output(
                    result_data["nmap_output"]
                )
                self.completed_targets += 1
            else:
                self.failed_targets += 1

            # Update contributing clients list
            if self.contributing_clients is None:
                self.contributing_clients = []
            if client_id not in self.contributing_clients:
                self.contributing_clients.append(client_id)

            # Update statistics
            self._update_statistics()

            # Update timestamps
            if not self.started_at:
                self.started_at = datetime.utcnow()

            # Check if all targets are complete
            if self.completed_targets + self.failed_targets >= self.total_targets:
                self.complete()

            # Mark as modified to trigger JSON update
            db.session.add(self)
            db.session.commit()

            return True

        except Exception as e:
            db.session.rollback()
            print(f"Error updating scan result: {e}")
            return False

    def _parse_nmap_output(self, nmap_output: Dict) -> Dict:
        """
        Parse nmap output into a simplified structure for querying

        Args:
            nmap_output: Raw nmap output dictionary

        Returns:
            Dict: Parsed data structure
        """
        parsed = {
            "hostname": nmap_output.get("hostname", ""),
            "state": nmap_output.get("state", "unknown"),
            "open_ports": [],
            "port_details": {},
        }

        # Extract port information
        protocols = nmap_output.get("protocols", {})
        for protocol, ports in protocols.items():
            for port, details in ports.items():
                if details.get("state") == "open":
                    parsed["open_ports"].append(int(port))
                    parsed["port_details"][port] = {
                        "protocol": protocol,
                        "name": details.get("name", ""),
                        "product": details.get("product", ""),
                        "version": details.get("version", ""),
                        "extrainfo": details.get("extrainfo", ""),
                    }

        parsed["open_ports"].sort()
        return parsed

    def _update_statistics(self):
        """Update summary statistics based on current results"""
        total_ports = 0

        for target, data in (self.parsed_results or {}).items():
            total_ports += len(data.get("open_ports", []))

        self.total_open_ports = total_ports

    def mark_target_failed(
        self, target: str, client_id: str, error_message: str
    ) -> bool:
        """
        Mark a specific target as failed

        Args:
            target: Target IP address
            client_id: ID of the client that failed
            error_message: Error message describing the failure

        Returns:
            bool: True if marked successfully
        """
        try:
            if self.target_results is None:
                self.target_results = {}

            self.target_results[target] = {
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "failed",
                "nmap_output": {},
                "error_message": error_message,
            }

            self.failed_targets += 1

            # Update contributing clients
            if self.contributing_clients is None:
                self.contributing_clients = []
            if client_id not in self.contributing_clients:
                self.contributing_clients.append(client_id)

            # Check if scan should be completed
            if self.completed_targets + self.failed_targets >= self.total_targets:
                self.complete()

            db.session.add(self)
            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Error marking target as failed: {e}")
            return False

    def mark_complete(self):
        """Mark the overall scan as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()

        if self.started_at:
            self.total_duration = (self.completed_at - self.started_at).total_seconds()

        db.session.add(self)
        db.session.commit()

    def mark_failed(self, error_message: Optional[str] = None):
        """
        Mark the overall scan as failed

        Args:
            error_message: Optional error message
        """
        self.status = "failed"
        self.completed_at = datetime.utcnow()

        if self.started_at:
            self.total_duration = (self.completed_at - self.started_at).total_seconds()

        db.session.add(self)
        db.session.commit()

    def get_target_result(self, target: str) -> Optional[Dict]:
        """
        Get result for a specific target

        Args:
            target: Target IP address

        Returns:
            Dict or None: Target result if found
        """
        if self.target_results:
            return self.target_results.get(target)
        return None

    def get_parsed_result(self, target: str) -> Optional[Dict]:
        """
        Get parsed result for a specific target

        Args:
            target: Target IP address

        Returns:
            Dict or None: Parsed result if found
        """
        if self.parsed_results:
            return self.parsed_results.get(target)
        return None

    def get_all_open_ports(self) -> Dict[str, list]:
        """
        Get all open ports grouped by target

        Returns:
            Dict mapping target IPs to lists of open ports
        """
        result = {}
        if self.parsed_results:
            for target, data in self.parsed_results.items():
                result[target] = data.get("open_ports", [])
        return result

    def to_dict(self) -> Dict:
        """Convert scan result to dictionary"""
        return {
            "id": self.id,
            "result_id": self.result_id,
            "scan_id": self.scan_id,
            "status": self.status,
            "total_targets": self.total_targets,
            "completed_targets": self.completed_targets,
            "failed_targets": self.failed_targets,
            "total_open_ports": self.total_open_ports,
            "contributing_clients": self.contributing_clients,
            "parsed_results": self.parsed_results,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_summary_dict(self) -> Dict:
        """Convert scan result to summary dictionary (without full nmap data)"""
        return {
            "id": self.id,
            "result_id": self.result_id,
            "scan_id": self.scan_id,
            "status": self.status,
            "total_targets": self.total_targets,
            "completed_targets": self.completed_targets,
            "failed_targets": self.failed_targets,
            "total_open_ports": self.total_open_ports,
            "contributing_clients": self.contributing_clients,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "total_duration": self.total_duration,
        }
