#!/usr/bin/env python3
"""
Push-Based Port Scanner Client Agent

This client runs on Raspberry Pi 4 devices and performs network scanning
tasks as requested by the central server. It runs a web server to listen
for push-based scan requests from the server and returns complete results.
"""

import json
import logging
import socket
import subprocess
import sys
import time
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from queue import Queue
import yaml
import requests
import psutil
import nmap
from flask import Flask, request, jsonify
from werkzeug.serving import make_server
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress Flask's default logging for cleaner output
logging.getLogger("werkzeug").setLevel(logging.WARNING)


@dataclass
class ScanRequest:
    """Represents a scan request from the server"""

    scan_id: str
    task_id: str
    result_id: str
    targets: List[str]
    ports: str
    scan_type: str = "tcp"
    timeout: int = 300
    priority: int = 1
    scan_name: Optional[str] = None
    scan_arguments: Optional[str] = None


@dataclass
class ScanResult:
    """Represents the complete result of a port scan"""

    scan_id: str
    task_id: str
    result_id: str
    client_id: str
    scan_duration: float
    status: str  # 'in_progress', 'completed', 'failed'
    target_results: list  # List of target result dicts
    total_targets: int
    error_message: Optional[str] = None


class PortScannerClient:
    """Client agent for performing network scans"""

    def __init__(self, config_file: str = "config.yml"):
        self.client_id = self._get_client_id()
        self.hostname = socket.gethostname()
        self.config = self._load_config(config_file)
        self.nm = nmap.PortScanner()
        self.registered = False

        # Scan range (from config)
        self.scan_range = self.config.get("scan_range")

        # Thread pool for handling concurrent scans
        max_workers = self.config.get("max_concurrent_scans", 2)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_scans = {}  # scan_id -> Future

        # Flask app for receiving push requests
        self.app = Flask(__name__)
        self._setup_routes()

        # HTTP server
        self.server = None
        self.server_thread = None

        # Register with server on startup
        self._register_with_server()

        # Start heartbeat thread
        self._start_heartbeat()

    def _get_client_id(self) -> str:
        # Fallback to hostname
        return socket.gethostname()

    def _get_ip_address(self) -> str:
        """Get current IP address"""
        return "0.0.0.0"

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file"""
        default_config = {
            "server_url": "http://localhost:5000",
            "client_port": 8080,
            "heartbeat_interval": 60,
            "max_concurrent_scans": 2,
            "retry_attempts": 3,
            "retry_delay": 5,
            "client_host": "0.0.0.0",  # Listen on all interfaces
            "scan_range": None,  # Add scan_range to config
        }

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f)
                default_config.update(loaded_config)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")

        return default_config

    def _setup_routes(self):
        """Setup Flask routes for handling incoming requests"""

        @self.app.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint"""
            return jsonify(
                {
                    "status": "healthy",
                    "client_id": self.client_id,
                    "hostname": self.hostname,
                    "active_scans": len(self.active_scans),
                    "system_info": self.get_system_info(),
                }
            )

        @self.app.route("/scan", methods=["POST"])
        def receive_scan_request():
            """Receive scan request from server"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data provided"}), 400

                # Validate required fields
                required_fields = ["scan_id", "targets", "ports"]
                for field in required_fields:
                    if field not in data:
                        return (
                            jsonify({"error": f"Missing required field: {field}"}),
                            400,
                        )

                # Create scan request
                scan_request = ScanRequest(
                    scan_id=data.get("scan_id"),
                    task_id=data.get("task_id"),
                    result_id=data.get("result_id"),
                    targets=data.get("targets", []),
                    ports=data.get("ports", "1-1000"),
                    scan_type=data.get("scan_type", "T"),
                    timeout=data.get("timeout", 300),
                    priority=data.get("priority", 1),
                    scan_name=data.get("scan_name"),
                    scan_arguments=data.get("scan_arguments"),
                )
                # Check if scan already exists

                if scan_request.scan_id in self.active_scans:
                    print("Scan already running")
                    return (
                        jsonify(
                            {
                                "error": "Scan with this ID is already running",
                                "scan_id": scan_request.scan_id,
                            }
                        ),
                        409,
                    )

                # Submit scan to thread pool
                future = self.executor.submit(self.perform_scan, scan_request)
                self.active_scans[scan_request.scan_id] = future

                logger.info(f"Accepted scan request: {scan_request.scan_id}")

                return (
                    jsonify(
                        {
                            "message": "Scan request accepted",
                            "scan_id": scan_request.scan_id,
                            "status": "accepted",
                        }
                    ),
                    202,
                )

            except Exception as e:
                logger.error(f"Error processing scan request: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/scan/<scan_id>/cancel", methods=["POST"])
        def cancel_scan(scan_id):
            """Cancel a running scan"""
            try:
                if scan_id not in self.active_scans:
                    return jsonify({"error": "Scan not found"}), 404

                future = self.active_scans[scan_id]
                if future.cancel():
                    del self.active_scans[scan_id]
                    logger.info(f"Cancelled scan: {scan_id}")
                    return jsonify({"message": "Scan cancelled", "scan_id": scan_id})
                else:
                    return (
                        jsonify({"error": "Cannot cancel scan - already running"}),
                        409,
                    )

            except Exception as e:
                logger.error(f"Error cancelling scan: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/scans", methods=["GET"])
        def list_active_scans():
            """List all active scans"""
            try:
                scans = []
                for scan_id, future in list(self.active_scans.items()):
                    if future.done():
                        # Clean up completed scans
                        del self.active_scans[scan_id]
                    else:
                        scans.append(
                            {
                                "scan_id": scan_id,
                                "status": "running" if future.running() else "pending",
                            }
                        )

                return jsonify({"active_scans": scans, "count": len(scans)})

            except Exception as e:
                logger.error(f"Error listing scans: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/system", methods=["GET"])
        def system_info():
            """Get system information"""
            return jsonify(self.get_system_info())

    def _register_with_server(self) -> bool:
        """Register this client with the server"""
        max_attempts = self.config.get("retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 5)

        for attempt in range(max_attempts):
            try:
                url = f"{self.config['server_url']}/api/clients/register"
                data = {
                    "client_id": self.client_id,
                    "hostname": self.hostname,
                    "ip_address": self._get_ip_address(),
                    "scan_range": self.scan_range,
                    "client_port": self.config.get("client_port", 8080),
                    "capabilities": {
                        "max_concurrent_scans": self.config.get(
                            "max_concurrent_scans", 2
                        ),
                        "supported_scan_types": ["tcp", "udp", "syn"],
                        "nmap_version": (
                            nmap.__version__
                            if hasattr(nmap, "__version__")
                            else "unknown"
                        ),
                    },
                }

                response = requests.post(url, json=data, timeout=10)

                if response.status_code == 200:
                    logger.info(
                        f"Successfully registered with server as {self.client_id}"
                    )
                    self.registered = True
                    return True
                else:
                    logger.warning(
                        f"Registration failed with status {response.status_code}: {response.text}"
                    )

            except requests.exceptions.RequestException as e:
                logger.warning(f"Registration attempt {attempt + 1} failed: {e}")

            if attempt < max_attempts - 1:
                time.sleep(retry_delay)

        logger.error("Failed to register with server after all attempts")
        return False

    def _start_heartbeat(self):
        """Start heartbeat thread to maintain connection with server"""

        def heartbeat_loop():
            while True:
                try:
                    url = f"{self.config['server_url']}/api/clients/{self.client_id}/heartbeat"
                    data = {
                        "hostname": self.hostname,
                        "ip_address": self._get_ip_address(),
                        "client_port": self.config.get("client_port", 8080),
                        "active_scans": len(self.active_scans),
                        "system_info": self.get_system_info(),
                    }
                    response = requests.post(url, json=data, timeout=5)
                    if response.status_code == 200:
                        logger.debug("Heartbeat sent successfully")
                    else:
                        logger.debug(
                            f"Heartbeat failed with status: {response.status_code}"
                        )

                except Exception as e:
                    logger.debug(f"Heartbeat failed: {e}")

                time.sleep(self.config.get("heartbeat_interval", 60))

        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()

    def _extract_scan_data(self, target: str) -> Dict:
        """Extract scan data from nmap results for easier server processing"""
        try:
            if target not in self.nm.all_hosts():
                return {
                    "hostname": "",
                    "state": "down",
                    "open_ports": [],
                    "port_details": {},
                }

            # Get basic host information
            hostname = self.nm[target].hostname()
            state = self.nm[target].state()

            open_ports = []
            port_details = {}

            # Extract port information from all protocols
            for proto in self.nm[target].all_protocols():
                ports = self.nm[target][proto].keys()

                for port in sorted(ports):
                    port_info = self.nm[target][proto][port]
                    port_state = port_info.get("state", "unknown")

                    # Only include open ports in the list
                    if port_state == "open":
                        open_ports.append(port)

                        # Store detailed information for this port
                        port_details[str(port)] = {
                            "protocol": proto,
                            "state": port_state,
                            "name": port_info.get("name", "unknown"),
                            "product": port_info.get("product", ""),
                            "version": port_info.get("version", ""),
                            "extrainfo": port_info.get("extrainfo", ""),
                            "reason": port_info.get("reason", ""),
                            "conf": port_info.get("conf", ""),
                        }

            # Build result structure
            result = {
                "hostname": hostname,
                "state": state,
                "open_ports": sorted(open_ports),
                "port_details": port_details,
            }

            # Optionally add OS detection if available
            if hasattr(self.nm[target], "get") and "osmatch" in self.nm[target]:
                os_matches = self.nm[target]["osmatch"]
                if os_matches:
                    # Take the best match
                    result["os_detection"] = {
                        "name": os_matches[0].get("name", ""),
                        "accuracy": os_matches[0].get("accuracy", ""),
                    }

            return result

        except Exception as e:
            logger.error(f"Error extracting scan data for {target}: {e}")
            return {
                "hostname": "",
                "state": "error",
                "open_ports": [],
                "port_details": {},
                "error": str(e),
            }

    def perform_scan(self, scan_request: ScanRequest):
        """Perform a complete scan and send results to server"""
        start_time = time.time()

        try:
            logger.info(
                f"Starting scan {scan_request.scan_id} with {len(scan_request.targets)} targets"
            )

            # Build scan arguments
            scan_args = f"-s{scan_request.scan_type.upper()}"
            if scan_request.scan_arguments:
                scan_args += f" {scan_request.scan_arguments}"
            # Perform scan for all targets
            targets_str = " ".join(scan_request.targets)
            logger.info(f"Scanning targets: {targets_str}")
            logger.info(f"Ports: {scan_request.ports}")
            logger.info(f"Arguments: {scan_args}")

            self.nm.scan(
                hosts=targets_str,
                ports=scan_request.ports,
                arguments=scan_args,
            )

            scan_duration = time.time() - start_time

            # Build results structure
            parsed_results = {}
            summary_stats = {
                "total_targets": len(scan_request.targets),
                "scanned_targets": 0,
                "targets_up": 0,
                "targets_down": 0,
                "error_targets": 0,
                "total_open_ports": 0,
            }

            for target in scan_request.targets:
                try:
                    # Extract scan data
                    target_data = self._extract_scan_data(target)
                    parsed_results[target] = target_data

                    # Update summary statistics
                    if target_data["state"] == "up":
                        summary_stats["scanned_targets"] += 1
                        summary_stats["targets_up"] += 1
                        summary_stats["total_open_ports"] += len(
                            target_data["open_ports"]
                        )
                    elif target_data["state"] == "down":
                        summary_stats["scanned_targets"] += 1
                        summary_stats["targets_down"] += 1
                    elif target_data["state"] == "error":
                        summary_stats["error_targets"] += 1

                    # Log summary
                    open_ports_count = len(target_data["open_ports"])
                    logger.info(
                        f"Processed target {target}: {target_data['state']} - "
                        f"{open_ports_count} open ports"
                    )

                except Exception as e:
                    logger.error(f"Error processing results for target {target}: {e}")
                    parsed_results[target] = {
                        "hostname": "",
                        "state": "error",
                        "open_ports": [],
                        "port_details": {},
                        "error": str(e),
                    }
                    summary_stats["failed_targets"] += 1

            # Prepare result payload
            result_payload = {
                "scan_id": scan_request.scan_id,
                "task_id": scan_request.task_id,
                "result_id": scan_request.result_id,
                "client_id": self.client_id,
                "status": "completed",
                "scan_duration": scan_duration,
                "parsed_results": parsed_results,
                "summary_stats": summary_stats,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Send results to server
            success = self.send_scan_results(result_payload)

            if success:
                logger.info(
                    f"Scan {scan_request.scan_id} completed and sent in {scan_duration:.2f}s - "
                    f"{summary_stats['total_open_ports']} total open ports found"
                )
            else:
                logger.error(f"Failed to send results for scan {scan_request.scan_id}")

        except Exception as e:
            logger.error(f"Scan {scan_request.scan_id} failed: {e}")

            # Send failure status
            result_payload = {
                "scan_id": scan_request.scan_id,
                "task_id": scan_request.task_id,
                "result_id": scan_request.result_id,
                "status": "failed",
                "scan_duration": time.time() - start_time,
                "parsed_results": {},
                "summary_stats": {
                    "total_targets": len(scan_request.targets),
                    "up_targets": 0,
                    "down_targets": 0,
                    "failed_targets": len(scan_request.targets),
                    "total_open_ports": 0,
                },
                "error_message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.send_scan_results(result_payload)

        finally:
            # Clean up completed scan
            if scan_request.scan_id in self.active_scans:
                del self.active_scans[scan_request.scan_id]

    def send_scan_results(self, result_payload: Dict) -> bool:
        """Send structured scan results back to server"""
        max_attempts = self.config.get("retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 5)

        for attempt in range(max_attempts):
            try:
                url = f"{self.config['server_url']}/api/clients/{self.client_id}/results"  # TODO parse client_id here instead through payload

                # Use longer timeout for large payloads
                num_targets = len(result_payload.get("parsed_results", {}))
                timeout = max(30, num_targets * 0.5)

                response = requests.post(url, json=result_payload, timeout=timeout)

                if response.status_code == 200:
                    logger.info(
                        f"Successfully sent results for scan {result_payload['scan_id']} "
                        f"({num_targets} targets)"
                    )
                    return True
                else:
                    logger.warning(
                        f"Server returned status {response.status_code}: "
                        f"{response.text[:200]}"
                    )

            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed to send results: {e}")

            if attempt < max_attempts - 1:
                time.sleep(retry_delay)

        logger.error(
            f"Failed to send results after {max_attempts} attempts "
            f"for scan {result_payload['scan_id']}"
        )
        return False

    def get_system_info(self) -> Dict:
        """Get system information for monitoring"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent,
                "network_io": (
                    psutil.net_io_counters()._asdict()
                    if psutil.net_io_counters()
                    else {}
                ),
                "uptime": time.time() - psutil.boot_time(),
                "load_average": (
                    list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else []
                ),
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}

    def start_server(self):
        """Start the Flask web server"""
        try:
            host = self.config.get("client_host", "0.0.0.0")
            port = self.config.get("client_port", 8080)

            # Create server
            self.server = make_server(host, port, self.app, threaded=True)

            # Start server in a separate thread
            def run_server():
                logger.info(f"Client HTTP server starting on {host}:{port}")
                self.server.serve_forever()

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()

            logger.info(
                f"Client ready to receive scan requests on http://{host}:{port}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False

    def stop_server(self):
        """Stop the Flask web server"""
        if self.server:
            logger.info("Shutting down HTTP server...")
            self.server.shutdown()
            if self.server_thread:
                self.server_thread.join(timeout=5)

    def cleanup(self):
        """Cleanup resources before shutdown"""
        try:
            # Cancel all active scans
            logger.info(f"Cancelling {len(self.active_scans)} active scans...")
            for scan_id, future in list(self.active_scans.items()):
                future.cancel()

            # Shutdown executor with proper timeout handling
            self.executor.shutdown(wait=True)
            logger.info("Thread pool executor shutdown completed")

            # Stop HTTP server
            self.stop_server()

            # Mark client as offline (non-blocking)
            try:
                url = f"{self.config['server_url']}/api/clients/{self.client_id}"
                requests.put(url, json={"status": "offline"}, timeout=5)
                logger.info("Client marked as offline")
            except Exception as e:
                logger.warning(f"Failed to mark client as offline: {e}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def run(self):
        """Main client loop - now just keeps the service running"""
        logger.info(f"Port Scanner Client {self.client_id} starting...")
        logger.info(f"Server URL: {self.config['server_url']}")
        logger.info(f"Max concurrent scans: {self.config['max_concurrent_scans']}")

        # Ensure registration
        if not self.registered:
            logger.warning("Not registered with server, attempting registration...")
            if not self._register_with_server():
                logger.error("Cannot proceed without server registration")
                return False

        # Start the HTTP server
        if not self.start_server():
            logger.error("Failed to start HTTP server")
            return False

        try:
            # Keep the main thread alive and monitor
            while True:
                # Clean up completed scans
                completed_scans = []
                for scan_id, future in list(self.active_scans.items()):
                    if future.done():
                        completed_scans.append(scan_id)

                for scan_id in completed_scans:
                    del self.active_scans[scan_id]

                if completed_scans:
                    logger.debug(f"Cleaned up {len(completed_scans)} completed scans")

                # Wait before checking again - use a default value if not in config
                check_interval = self.config.get("check_interval", 10)
                time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.cleanup()

        return True


def main():
    """Entry point for the client agent"""
    import argparse

    parser = argparse.ArgumentParser(description="Push-Based Port Scanner Client Agent")
    parser.add_argument(
        "--config",
        default="config.yml",
        help="Path to configuration file (default: config.yml)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--server", help="Override server URL from config")
    parser.add_argument("--port", type=int, help="Override client port from config")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create client
    try:
        client = PortScannerClient(args.config)
    except Exception as e:
        logger.error(f"Failed to create client: {e}")
        sys.exit(1)

    # Override server URL if provided
    if args.server:
        client.config["server_url"] = args.server
        logger.info(f"Using server URL: {args.server}")

    # Override port if provided
    if args.port:
        client.config["client_port"] = args.port
        logger.info(f"Using client port: {args.port}")

    # Run client
    try:
        success = client.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
