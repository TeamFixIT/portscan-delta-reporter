import os
import nmap
import schedule
import time
import socket
import psutil
import netifaces
from datetime import datetime

# Initialize scanner
nm = nmap.PortScanner()

def show_system_info():
    print("="*50)
    print("📡 Network Scanner - System Information")
    print("="*50)
    print(f"Timestamp       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Hostname        : {socket.gethostname()}")
    print(f"Local IP        : {socket.gethostbyname(socket.gethostname())}")
    
    # Get network interface info
    print("\nAvailable Interfaces:")
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            ip_info = addrs[netifaces.AF_INET][0]
            print(f"  - {iface}")
            print(f"      IP Address   : {ip_info.get('addr')}")
            print(f"      Netmask      : {ip_info.get('netmask')}")
            print(f"      Broadcast    : {ip_info.get('broadcast')}")
    
    # CPU and memory info (optional but useful for context)
    print("\nSystem Resources:")
    print(f"  CPU Cores       : {psutil.cpu_count(logical=True)}")
    print(f"  CPU Usage       : {psutil.cpu_percent(interval=1)}%")
    print(f"  Memory Usage    : {psutil.virtual_memory().percent}%")
    print("="*50)
    print("\n")

def run_scan(target, ports, output_dir="scan_results"):
    """Run nmap scan and save results to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"scan_{timestamp}.txt")

    print(f"[INFO] Running scan against {target} on ports {ports}...")

    try:
        nm.scan(hosts=target, ports=ports, arguments="-sV")  # service detection
    except Exception as e:
        print(f"[ERROR] Scan failed: {e}")
        return

    with open(output_file, "w") as f:
        for host in nm.all_hosts():
            f.write(f"Host: {host} ({nm[host].hostname()})\n")
            f.write(f"State: {nm[host].state()}\n")
            for proto in nm[host].all_protocols():
                lport = nm[host][proto].keys()
                for port in sorted(lport):
                    state = nm[host][proto][port]['state']
                    name = nm[host][proto][port]['name']
                    f.write(f"Port: {port}\tState: {state}\tService: {name}\n")
            f.write("\n")

    print(f"[INFO] Scan complete. Results saved to {output_file}")

def main():
    show_system_info()
    print("🔍 Ready to run network scan...")
    target = input("Enter target IP or subnet (e.g. 192.168.1.0/24): ").strip()
    ports = input("Enter ports to scan (e.g. 22,80,443 or 1-1024): ").strip()
    interval = int(input("Enter scan interval in minutes: ").strip())

    # Schedule job
    schedule.every(interval).minutes.do(run_scan, target=target, ports=ports)

    print(f"[INFO] Scheduled scan every {interval} minutes for {target}:{ports}")

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
