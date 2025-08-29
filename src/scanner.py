import os
import json
import nmap
import socket
import psutil
import netifaces
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ScanResult:
    """Data class for scan results"""
    host: str
    hostname: str
    state: str
    ports: List[Dict[str, Any]]
    timestamp: str
    scan_duration: float


@dataclass
class SystemInfo:
    """Data class for system information"""
    timestamp: str
    hostname: str
    local_ip: str
    interfaces: List[Dict[str, Any]]
    cpu_cores: int
    cpu_usage: float
    memory_usage: float


class NetworkScanner:
    """
    Professional network scanner class with enhanced functionality
    """
    def __init__(self, output_dir: str = "scan_results", log_level: str = "INFO"):
        """
        Initialize the NetworkScanner
        
        Args:
            output_dir (str): Directory to save scan results
            log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.nm = nmap.PortScanner()
        self.output_dir = output_dir
        self.logger = self._setup_logging(log_level)
        self._ensure_output_directory()
    
    def _setup_logging(self, log_level: str) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create console handler if no handlers exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _ensure_output_directory(self) -> None:
        """Ensure output directory exists"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Failed to create output directory: {e}")
            raise
    
    def get_system_info(self) -> SystemInfo:
        """
        Get comprehensive system information
        
        Returns:
            SystemInfo: System information data class
        """
        try:
            interfaces = []
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    ip_info = addrs[netifaces.AF_INET][0]
                    interfaces.append({
                        'name': iface,
                        'ip_address': ip_info.get('addr'),
                        'netmask': ip_info.get('netmask'),
                        'broadcast': ip_info.get('broadcast')
                    })
            
            return SystemInfo(
                timestamp=datetime.now().isoformat(),
                hostname=socket.gethostname(),
                local_ip=socket.gethostbyname(socket.gethostname()),
                interfaces=interfaces,
                cpu_cores=psutil.cpu_count(logical=True),
                cpu_usage=psutil.cpu_percent(interval=1),
                memory_usage=psutil.virtual_memory().percent
            )
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            raise
    
    def scan_target(self, target: str, ports: str, scan_args: str = "-sV") -> List[ScanResult]:
        """
        Perform network scan on target
        
        Args:
            target (str): Target IP or subnet (e.g., '192.168.1.0/24')
            ports (str): Ports to scan (e.g., '22,80,443' or '1-1024')
            scan_args (str): Additional nmap arguments
            
        Returns:
            List[ScanResult]: List of scan results
            
        Raises:
            Exception: If scan fails
        """
        start_time = datetime.now()
        self.logger.info(f"Starting scan: target={target}, ports={ports}")
        
        try:
            self.nm.scan(hosts=target, ports=ports, arguments=scan_args)
            scan_duration = (datetime.now() - start_time).total_seconds()
            
            results = []
            for host in self.nm.all_hosts():
                ports_data = []
                
                for proto in self.nm[host].all_protocols():
                    lport = self.nm[host][proto].keys()
                    for port in sorted(lport):
                        port_info = self.nm[host][proto][port]
                        ports_data.append({
                            'port': port,
                            'protocol': proto,
                            'state': port_info['state'],
                            'service': port_info['name'],
                            'product': port_info.get('product', ''),
                            'version': port_info.get('version', ''),
                            'extrainfo': port_info.get('extrainfo', '')
                        })
                
                result = ScanResult(
                    host=host,
                    hostname=self.nm[host].hostname(),
                    state=self.nm[host].state(),
                    ports=ports_data,
                    timestamp=datetime.now().isoformat(),
                    scan_duration=scan_duration
                )
                results.append(result)
            
            self.logger.info(f"Scan completed successfully. Found {len(results)} hosts")
            return results
            
        except Exception as e:
            self.logger.error(f"Scan failed: {e}")
            raise
    
    def save_results(self, results: List[ScanResult], filename: Optional[str] = None) -> str:
        """
        Save scan results to file
        
        Args:
            results (List[ScanResult]): Scan results to save
            filename (str, optional): Custom filename. If None, timestamp-based name is used
            
        Returns:
            str: Path to saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Convert dataclasses to dictionaries for JSON serialization
            results_dict = {
                'scan_metadata': {
                    'total_hosts': len(results),
                    'scan_time': datetime.now().isoformat(),
                    'scanner_version': '2.0'
                },
                'results': [asdict(result) for result in results]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Results saved to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            raise
    
    def load_results(self, filepath: str) -> List[ScanResult]:
        """
        Load scan results from file
        
        Args:
            filepath (str): Path to results file
            
        Returns:
            List[ScanResult]: Loaded scan results
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = []
            for result_data in data.get('results', []):
                result = ScanResult(**result_data)
                results.append(result)
            
            self.logger.info(f"Loaded {len(results)} results from {filepath}")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to load results: {e}")
            raise
    
    def get_scan_summary(self, results: List[ScanResult]) -> Dict[str, Any]:
        """
        Generate scan summary statistics
        
        Args:
            results (List[ScanResult]): Scan results
            
        Returns:
            Dict[str, Any]: Summary statistics
        """
        if not results:
            return {}
        
        total_hosts = len(results)
        active_hosts = len([r for r in results if r.state == 'up'])
        total_open_ports = sum(len([p for p in r.ports if p['state'] == 'open']) for r in results)
        
        services = {}
        for result in results:
            for port in result.ports:
                if port['state'] == 'open':
                    service = port['service']
                    services[service] = services.get(service, 0) + 1
        
        return {
            'total_hosts_scanned': total_hosts,
            'active_hosts': active_hosts,
            'total_open_ports': total_open_ports,
            'common_services': dict(sorted(services.items(), key=lambda x: x[1], reverse=True)[:10]),
            'scan_efficiency': f"{(active_hosts/total_hosts)*100:.1f}%" if total_hosts > 0 else "0%"
        }
    
    def validate_target(self, target: str) -> bool:
        """
        Validate target IP or subnet format
        
        Args:
            target (str): Target to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Basic validation - can be enhanced
            if '/' in target:  # CIDR notation
                ip, cidr = target.split('/')
                socket.inet_aton(ip)
                cidr_int = int(cidr)
                return 0 <= cidr_int <= 32
            else:  # Single IP
                socket.inet_aton(target)
                return True
        except (socket.error, ValueError):
            return False
    
    def validate_ports(self, ports: str) -> bool:
        """
        Validate port specification format
        
        Args:
            ports (str): Port specification to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if '-' in ports:  # Range
                start, end = ports.split('-')
                start_int, end_int = int(start), int(end)
                return 1 <= start_int <= end_int <= 65535
            elif ',' in ports:  # List
                port_list = [int(p.strip()) for p in ports.split(',')]
                return all(1 <= p <= 65535 for p in port_list)
            else:  # Single port
                port_int = int(ports)
                return 1 <= port_int <= 65535
        except ValueError:
            return False


# Example usage and testing
if __name__ == "__main__":
    scanner = NetworkScanner(log_level="DEBUG")
    
    # Display system info
    system_info = scanner.get_system_info()
    print("="*60)
    print("🔡 Network Scanner - System Information")
    print("="*60)
    print(f"Timestamp    : {system_info.timestamp}")
    print(f"Hostname     : {system_info.hostname}")
    print(f"Local IP     : {system_info.local_ip}")
    print(f"CPU Cores    : {system_info.cpu_cores}")
    print(f"CPU Usage    : {system_info.cpu_usage}%")
    print(f"Memory Usage : {system_info.memory_usage}%")
    print("="*60)
    
    # Interactive scanning (for testing)
    target = input("Enter target IP or subnet: ").strip()
    ports = input("Enter ports to scan: ").strip()
    
    if scanner.validate_target(target) and scanner.validate_ports(ports):
        try:
            results = scanner.scan_target(target, ports)
            filepath = scanner.save_results(results)
            summary = scanner.get_scan_summary(results)
            
            print(f"\nScan Summary:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
                
        except Exception as e:
            print(f"Scan failed: {e}")
    else:
        print("Invalid target or port specification")