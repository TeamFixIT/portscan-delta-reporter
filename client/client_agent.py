#!/usr/bin/env python3
"""
Port Scanner Client Agent

This client runs on Raspberry Pi 4 devices and performs network scanning
tasks as requested by the central server. It communicates with the server
via HTTP to receive scan instructions and return results progressively.
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
import netifaces
import nmap

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ScanRequest:
    """Represents a scan request from the server"""

    scan_id: str
    targets: List[str]
    ports: str
    scan_type: str = "tcp"
    timeout: int = 300
    priority: int = 1
    scan_name: Optional[str] = None
    scan_arguments: Optional[str] = None


@dataclass
class ScanResult:
    """Represents the result of a port scan"""

    scan_id: str
    client_id: str
    timestamp: str
    target: str
    status: str  # 'in_progress', 'completed', 'failed'
    open_ports: List[Dict]
    scan_duration: float
    error_message: Optional[str] = None
    partial_results: Optional[Dict] = None


class PortScannerClient:
    """Client agent for performing network scans"""

    def __init__(self, config_file: str = "config.yml"):
        self.client_id = self._get_client_id()
        self.hostname = socket.gethostname()
        self.config = self._load_config(config_file)
        self.nm = nmap.PortScanner()
        self.current_scan = None
        self.scan_thread = None
        self.result_queue = Queue()
        self.registered = False

        # Register with server on startup
        self._register_with_server()

        # Start heartbeat thread
        self._start_heartbeat()

    def _get_client_id(self) -> str:
        """Generate unique client ID based on MAC address"""
        try:
            # Get the MAC address of the first active network interface
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                if interface != "lo":  # Skip loopback
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_LINK in addrs:
                        mac = addrs[netifaces.AF_LINK][0]["addr"]
                        return mac.replace(":", "").upper()
        except Exception as e:
            logger.warning(f"Could not get MAC address: {e}")

        # Fallback to hostname
        return socket.gethostname()

    def _get_ip_address(self) -> str:
        """Get current IP address"""
        try:
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                if interface != "lo":
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        return addrs[netifaces.AF_INET][0]["addr"]
        except Exception:
            pass
        return "0.0.0.0"

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file"""
        default_config = {
            "server_url": "http://localhost:5000",
            "check_interval": 30,
            "heartbeat_interval": 60,
            "max_concurrent_scans": 2,
            "progress_update_interval": 10,
            "retry_attempts": 3,
            "retry_delay": 5,
        }

        try:
            with open(config_file, "r") as f:
                loaded_config = yaml.safe_load(f)
                default_config.update(loaded_config)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} not found, using defaults")
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")

        return default_config

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
                        f"Registration failed with status {response.status_code}"
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
                    }
                    requests.post(url, json=data, timeout=5)
                except Exception as e:
                    logger.debug(f"Heartbeat failed: {e}")

                time.sleep(self.config.get("heartbeat_interval", 60))

        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()

    def perform_progressive_scan(self, scan_request: ScanRequest):
        """Perform a scan with progressive updates"""
        start_time = time.time()
        all_results = {}

        try:
            for target in scan_request.targets:
                logger.info(f"Scanning target {target} for scan {scan_request.scan_id}")

                # Send initial in-progress update
                self._send_progress_update(
                    scan_request.scan_id, target, "in_progress", [], 0
                )

                # Perform the nmap scan
                scan_args = f"-s{scan_request.scan_type.upper()}"
                if scan_request.scan_arguments:
                    scan_args += f" {scan_request.scan_arguments}"

                # Use callback for progressive updates
                def callback(host, scan_result):
                    """Callback for nmap progress"""
                    if host in scan_result["scan"]:
                        open_ports = []
                        for proto in ["tcp", "udp"]:
                            if proto in scan_result["scan"][host]:
                                for port in scan_result["scan"][host][proto]:
                                    port_info = scan_result["scan"][host][proto][port]
                                    if port_info["state"] == "open":
                                        open_ports.append(
                                            {
                                                "port": port,
                                                "state": port_info["state"],
                                                "service": port_info.get(
                                                    "name", "unknown"
                                                ),
                                                "version": port_info.get("version", ""),
                                                "product": port_info.get("product", ""),
                                            }
                                        )

                        # Send progressive update
                        self._send_progress_update(
                            scan_request.scan_id,
                            host,
                            "in_progress",
                            open_ports,
                            time.time() - start_time,
                        )

                # Start scan with callback
                self.nm.scan(
                    hosts=target,
                    ports=scan_request.ports,
                    arguments=scan_args,
                    callback=callback,
                )

                # Collect final results for this target
                open_ports = []
                if target in self.nm.all_hosts():
                    for proto in ["tcp", "udp"]:
                        if proto in self.nm[target]:
                            for port in self.nm[target][proto]:
                                port_info = self.nm[target][proto][port]
                                if port_info["state"] == "open":
                                    open_ports.append(
                                        {
                                            "port": port,
                                            "state": port_info["state"],
                                            "service": port_info.get("name", "unknown"),
                                            "version": port_info.get("version", ""),
                                            "product": port_info.get("product", ""),
                                            "protocol": proto,
                                        }
                                    )

                all_results[target] = open_ports

                # Send completed update for this target if multi-target scan
                if len(scan_request.targets) > 1:
                    self._send_progress_update(
                        scan_request.scan_id,
                        target,
                        "in_progress",
                        open_ports,
                        time.time() - start_time,
                    )

            # Send final completed status for entire scan
            scan_duration = time.time() - start_time

            # Send final result for each target
            for target, ports in all_results.items():
                result = ScanResult(
                    scan_id=scan_request.scan_id,
                    client_id=self.client_id,
                    timestamp=datetime.utcnow().isoformat(),
                    target=target,
                    status="completed",
                    open_ports=ports,
                    scan_duration=scan_duration,
                )
                self.send_result(result)

            logger.info(
                f"Scan {scan_request.scan_id} completed in {scan_duration:.2f} seconds"
            )

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            # Send failure status
            result = ScanResult(
                scan_id=scan_request.scan_id,
                client_id=self.client_id,
                timestamp=datetime.utcnow().isoformat(),
                target=scan_request.targets[0] if scan_request.targets else "unknown",
                status="failed",
                open_ports=[],
                scan_duration=time.time() - start_time,
                error_message=str(e),
            )
            self.send_result(result)

    def _send_progress_update(
        self,
        scan_id: str,
        target: str,
        status: str,
        open_ports: List[Dict],
        duration: float,
    ):
        """Send progressive scan update to server"""
        try:
            url = f"{self.config['server_url']}/api/scan-results"
            data = {
                "scan_id": scan_id,
                "client_id": self.client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "target": target,
                "status": status,
                "open_ports": open_ports,
                "scan_duration": duration,
            }

            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                logger.debug(f"Progress update sent for {target}")
            else:
                logger.warning(
                    f"Failed to send progress update: {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Error sending progress update: {e}")

    def perform_scan(self, scan_request: ScanRequest) -> ScanResult:
        """Perform a basic port scan (backwards compatibility)"""
        start_time = time.time()

        try:

            logger.info(
                f"Starting scan {scan_request.scan_id} for target {scan_request.targets[0]}"
            )

            # Perform the nmap scan
            target = scan_request.targets[0]
            scan_args = f"-s{scan_request.scan_type.upper()}"
            if scan_request.scan_arguments:
                scan_args += f" {scan_request.scan_arguments}"

            self.nm.scan(target, scan_request.ports, arguments=scan_args)

            open_ports = []
            if target in self.nm.all_hosts():
                for proto in ["tcp", "udp"]:
                    if proto in self.nm[target]:
                        for port in self.nm[target][proto]:
                            port_info = self.nm[target][proto][port]
                            if port_info["state"] == "open":
                                open_ports.append(
                                    {
                                        "port": port,
                                        "state": port_info["state"],
                                        "service": port_info.get("name", "unknown"),
                                        "version": port_info.get("version", ""),
                                        "product": port_info.get("product", ""),
                                        "protocol": proto,
                                    }
                                )

            scan_duration = time.time() - start_time

            return ScanResult(
                scan_id=scan_request.scan_id,
                client_id=self.client_id,
                timestamp=datetime.utcnow().isoformat(),
                target=target,
                status="completed",
                open_ports=open_ports,
                scan_duration=scan_duration,
            )

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return ScanResult(
                scan_id=scan_request.scan_id,
                client_id=self.client_id,
                timestamp=datetime.utcnow().isoformat(),
                target=scan_request.targets[0] if scan_request.targets else "unknown",
                status="failed",
                open_ports=[],
                scan_duration=time.time() - start_time,
                error_message=str(e),
            )

    def send_result(self, result: ScanResult) -> bool:
        """Send scan result back to server"""
        max_attempts = self.config.get("retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 5)

        for attempt in range(max_attempts):
            try:
                url = f"{self.config['server_url']}/api/scan-results"
                response = requests.post(url, json=asdict(result), timeout=30)

                if response.status_code == 200:
                    logger.info(f"Successfully sent result for scan {result.scan_id}")
                    return True
                else:
                    logger.warning(f"Server returned status {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed to send result: {e}")

            if attempt < max_attempts - 1:
                time.sleep(retry_delay)

        logger.error(f"Failed to send result after {max_attempts} attempts")
        return False

    def check_for_tasks(self) -> Optional[ScanRequest]:
        """Check server for new scan tasks"""
        try:
            url = f"{self.config['server_url']}/api/scan-tasks/{self.client_id}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                task_data = response.json()
                if task_data:
                    return ScanRequest(
                        scan_id=task_data.get("scan_id"),
                        targets=task_data.get("targets", []),
                        ports=task_data.get("ports", "1-1000"),
                        scan_type=task_data.get("scan_type", "tcp"),
                        timeout=task_data.get("timeout", 300),
                        priority=task_data.get("priority", 1),
                        scan_name=task_data.get("scan_name"),
                        scan_arguments=task_data.get("scan_arguments"),
                    )
            elif response.status_code == 204:
                # No content - no tasks available
                logger.debug("No tasks available")
            else:
                logger.warning(f"Unexpected status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check for tasks: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking for tasks: {e}")

        return None

    def run_scan_async(self, scan_request: ScanRequest):
        """Run scan in a separate thread with progressive updates"""
        if self.scan_thread and self.scan_thread.is_alive():
            logger.warning("Previous scan still running, skipping new scan")
            return

        self.current_scan = scan_request
        self.scan_thread = threading.Thread(
            target=self.perform_progressive_scan, args=(scan_request,)
        )
        self.scan_thread.start()

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
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}

    def cleanup(self):
        """Cleanup resources before shutdown"""
        try:
            # Mark client as offline
            url = f"{self.config['server_url']}/api/clients/{self.client_id}"
            requests.put(url, json={"status": "offline"}, timeout=5)
            logger.info("Client marked as offline")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def run(self):
        """Main client loop"""
        logger.info(f"Client {self.client_id} starting...")
        logger.info(f"Server URL: {self.config['server_url']}")
        logger.info(f"Check interval: {self.config['check_interval']} seconds")

        # Ensure registration
        if not self.registered:
            logger.warning("Not registered with server, attempting registration...")
            if not self._register_with_server():
                logger.error("Cannot proceed without server registration")
                return

        consecutive_errors = 0
        max_consecutive_errors = 5

        while True:
            try:
                # Check if current scan is still running
                if self.scan_thread and self.scan_thread.is_alive():
                    logger.debug("Scan in progress, waiting...")
                else:
                    # Check for new scan tasks
                    scan_request = self.check_for_tasks()

                    if scan_request:
                        logger.info(f"Received scan task: {scan_request.scan_id}")

                        # Run scan with progressive updates
                        self.run_scan_async(scan_request)
                        consecutive_errors = 0  # Reset error counter on success
                    else:
                        logger.debug("No tasks available")

                # Wait before checking again

                time.sleep(self.config["check_interval"])

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                self.cleanup()
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Unexpected error in main loop: {e}")

                if consecutive_errors >= max_consecutive_errors:
                    logger.error(
                        f"Too many consecutive errors ({consecutive_errors}), exiting..."
                    )
                    self.cleanup()
                    sys.exit(1)

                # Exponential backoff on errors
                sleep_time = min(
                    self.config["check_interval"] * (2**consecutive_errors), 300
                )
                logger.info(f"Waiting {sleep_time} seconds before retry...")
                time.sleep(sleep_time)


def main():
    """Entry point for the client agent"""
    import argparse

    parser = argparse.ArgumentParser(description="Port Scanner Client Agent")
    parser.add_argument(
        "--config",
        default="config.yml",
        help="Path to configuration file (default: config.yml)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--server", help="Override server URL from config")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create client
    client = PortScannerClient(args.config)

    # Override server URL if provided
    if args.server:
        client.config["server_url"] = args.server
        logger.info(f"Using server URL: {args.server}")

    # Run client
    try:
        client.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
