#!/usr/bin/env python3
"""
Port Scanner Client Agent

This client runs on Raspberry Pi 4 devices and performs network scanning
tasks as requested by the central server. It communicates with the server
via HTTP/WebSocket to receive scan instructions and return results.
"""

import json
import logging
import socket
import subprocess
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import requests
import psutil
import netifaces
import nmap

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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


@dataclass
class ScanResult:
    """Represents the result of a port scan"""
    scan_id: str
    client_id: str
    timestamp: str
    target: str
    status: str
    open_ports: List[Dict]
    scan_duration: float
    error_message: Optional[str] = None


class PortScannerClient:
    """Client agent for performing network scans"""

    def __init__(self, config_file: str = "config.yml"):
        self.client_id = self._get_client_id()
        self.config = self._load_config(config_file)
        self.nm = nmap.PortScanner()

    def _get_client_id(self) -> str:
        """Generate unique client ID based on MAC address"""
        try:
            # Get the MAC address of the first active network interface
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                if interface != 'lo':  # Skip loopback
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_LINK in addrs:
                        mac = addrs[netifaces.AF_LINK][0]['addr']
                        return mac.replace(':', '').upper()
        except Exception as e:
            logger.warning(f"Could not get MAC address: {e}")

        # Fallback to hostname
        return socket.gethostname()

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file"""
        # For now, return default config
        # TODO: Implement YAML config loading
        return {
            'server_url': 'http://localhost:5000',
            'check_interval': 30,
            'max_concurrent_scans': 2
        }

    def perform_scan(self, scan_request: ScanRequest) -> ScanResult:
        """Perform a port scan based on the request"""
        start_time = time.time()

        try:
            logger.info(f"Starting scan {scan_request.scan_id} for target {scan_request.targets[0]}")

            # Perform the nmap scan
            target = scan_request.targets[0]  # Single target for now
            self.nm.scan(target, scan_request.ports, arguments=f'-s{scan_request.scan_type.upper()}')

            open_ports = []
            if target in self.nm.all_hosts():
                for port in self.nm[target]['tcp']:
                    port_info = self.nm[target]['tcp'][port]
                    if port_info['state'] == 'open':
                        open_ports.append({
                            'port': port,
                            'state': port_info['state'],
                            'service': port_info.get('name', 'unknown'),
                            'version': port_info.get('version', ''),
                            'product': port_info.get('product', '')
                        })

            scan_duration = time.time() - start_time

            return ScanResult(
                scan_id=scan_request.scan_id,
                client_id=self.client_id,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
                target=target,
                status='completed',
                open_ports=open_ports,
                scan_duration=scan_duration
            )

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return ScanResult(
                scan_id=scan_request.scan_id,
                client_id=self.client_id,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
                target=scan_request.targets[0] if scan_request.targets else 'unknown',
                status='failed',
                open_ports=[],
                scan_duration=time.time() - start_time,
                error_message=str(e)
            )

    def send_result(self, result: ScanResult) -> bool:
        """Send scan result back to server"""
        try:
            url = f"{self.config['server_url']}/api/scan-results"
            response = requests.post(
                url,
                json=asdict(result),
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Successfully sent result for scan {result.scan_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send result: {e}")
            return False

    def check_for_tasks(self) -> Optional[ScanRequest]:
        """Check server for new scan tasks"""
        try:
            url = f"{self.config['server_url']}/api/scan-tasks/{self.client_id}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                task_data = response.json()
                if task_data:
                    return ScanRequest(**task_data)

        except Exception as e:
            logger.error(f"Failed to check for tasks: {e}")

        return None

    def run(self):
        """Main client loop"""
        logger.info(f"Client {self.client_id} starting...")

        while True:
            try:
                # Check for new scan tasks
                scan_request = self.check_for_tasks()

                if scan_request:
                    # Perform the scan
                    result = self.perform_scan(scan_request)

                    # Send result back to server
                    self.send_result(result)

                # Wait before checking again
                time.sleep(self.config['check_interval'])

            except KeyboardInterrupt:
                logger.info("Client shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(self.config['check_interval'])


if __name__ == "__main__":
    client = PortScannerClient()
    client.run()
