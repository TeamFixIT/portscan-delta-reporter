import ipaddress
import argparse

def estimate_nmap_time(total_ips: int, alive_ips: int, total_ports: int, timing: int = 4) -> float:
    """
    Estimate Nmap scan duration (in seconds).
    """

    # probes/sec for discovery (rough estimates per -T)
    discovery_speeds = {
        0: 50,
        1: 100,
        2: 200,
        3: 500,
        4: 1000,
        5: 2000,
    }

    # parallel probes for port scans (rough estimates per -T)
    parallelism = {
        0: 10,
        1: 20,
        2: 50,
        3: 100,
        4: 200,
        5: 400,
    }

    avg_latency = 0.005  # 5ms

    probes_per_sec = discovery_speeds.get(timing, 500)
    discovery_time = total_ips / probes_per_sec

    par = parallelism.get(timing, 100)
    scan_time_per_host = (total_ports / par) * avg_latency

    total_time = discovery_time + (alive_ips * scan_time_per_host)

    overhead_factor = 5 if timing < 4 else 3
    return total_time * overhead_factor

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Estimate Nmap scan time",
        epilog="Example: python nmap_time_estimator.py -s 134.115.176.0/20 -a 5 -p 1000 -t 4"
    )
    parser.add_argument("-s", "--subnet", default="134.115.176.0/20", help="Subnet in CIDR notation (default: 134.115.176.0/20)")
    parser.add_argument("-a", "--percentage-alive", type=float, default=5.0, help="Estimated percentage of alive hosts (0-100, default: 5)")
    parser.add_argument("-p", "--total-ports", type=int, default=1000, help="Total number of ports to scan (default: 1000)")
    parser.add_argument("-t", "--timing", type=int, choices=range(0,6), default=4, help="Nmap timing template (0-5, default: 4)")

    args = parser.parse_args()

    # calculate total IPs in subnet
    network = ipaddress.ip_network(args.subnet, strict=False)
    total_ips = network.num_addresses

    # estimate alive hosts
    alive_ips = int(total_ips * (args.percentage_alive / 100.0))

    est_time = estimate_nmap_time(total_ips, alive_ips, args.total_ports, args.timing)

    print(f"Subnet: {args.subnet}")
    print(f"Total IPs: {total_ips}")
    print(f"Alive IPs (est): {alive_ips}")
    print(f"Ports per host: {args.total_ports}")
    print(f"Timing: -T{args.timing}")
    print(f"Estimated scan time: {est_time:.2f} seconds (~{est_time/60:.1f} minutes)")
