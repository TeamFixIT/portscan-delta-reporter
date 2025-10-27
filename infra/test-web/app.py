from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)

# Configuration for the 5 Docker socat services
SOCAT_SERVICES = ["socat1", "socat2", "socat3", "socat4", "socat5"]

# Track PIDs by service and port
port_processes = {}  # {service_name: {port: pid}}


def docker_exec(container, command):
    """Execute a command in a docker container"""
    try:
        result = subprocess.run(
            ["docker", "exec", container, "sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


@app.route("/")
def index():
    """Serve the main HTML page"""
    return send_from_directory(".", "index.html")


@app.route("/assets/<filename>")
def serve_asset(filename):
    """Serve static assets from the assets directory"""
    return send_from_directory("./assets", filename)


@app.route("/api/services", methods=["GET"])
def get_services():
    """Get list of all socat services"""
    services = []
    for service in SOCAT_SERVICES:
        success, output, error = docker_exec(service, "echo 'alive'")
        services.append(
            {
                "name": service,
                "status": "running" if success else "stopped",
            }
        )
    return jsonify({"status": "success", "services": services}), 200


@app.route("/api/ports/open", methods=["POST"])
def open_port():
    """Open a port on a specific service"""
    data = request.get_json()
    service = data.get("service")
    port = data.get("port")

    if not service or not port:
        return jsonify({"error": "Service name and port required"}), 400

    if service not in SOCAT_SERVICES:
        return jsonify({"error": f"Service {service} not found"}), 404

    try:
        port = int(port)
        if port < 1 or port > 65535:
            return jsonify({"error": "Port must be between 1 and 65535"}), 400
    except ValueError:
        return jsonify({"error": "Invalid port number"}), 400

    # Check if port is already open
    if service not in port_processes:
        port_processes[service] = {}

    if port in port_processes[service]:
        return jsonify({"error": f"Port {port} is already open on {service}"}), 400

    # Start socat in background and get PID
    command = f"socat TCP-LISTEN:{port},fork,reuseaddr SYSTEM:echo & echo $!"
    success, output, error = docker_exec(service, command)

    if success and output.strip():
        pid = output.strip()
        port_processes[service][port] = pid
        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Port {port} opened on {service}",
                    "service": service,
                    "port": port,
                    "pid": pid,
                }
            ),
            200,
        )
    else:
        return jsonify({"error": f"Failed to open port: {error}"}), 500


@app.route("/api/ports/close", methods=["POST"])
def close_port():
    """Close a port on a specific service"""
    data = request.get_json()
    service = data.get("service")
    port = data.get("port")

    if not service or not port:
        return jsonify({"error": "Service name and port required"}), 400

    if service not in SOCAT_SERVICES:
        return jsonify({"error": f"Service {service} not found"}), 404

    try:
        port = int(port)
    except ValueError:
        return jsonify({"error": "Invalid port number"}), 400

    # Kill the process
    if service in port_processes and port in port_processes[service]:
        pid = port_processes[service][port]
        command = f"kill {pid}"
        docker_exec(service, command)
        del port_processes[service][port]
        message = f"Closed port {port} on {service} (PID: {pid})"
    else:
        # Try to kill it anyway by finding the process
        command = f"pkill -f 'socat.*LISTEN:{port}'"
        docker_exec(service, command)
        message = f"Attempted to close port {port} on {service}"

    return (
        jsonify(
            {"status": "success", "message": message, "service": service, "port": port}
        ),
        200,
    )


@app.route("/api/ports/open-multiple", methods=["POST"])
def open_multiple_ports():
    """Open multiple ports on a specific service"""
    data = request.get_json()
    service = data.get("service")
    ports = data.get("ports", [])

    if not service or not isinstance(ports, list):
        return jsonify({"error": "Service name and ports array required"}), 400

    if service not in SOCAT_SERVICES:
        return jsonify({"error": f"Service {service} not found"}), 404

    if service not in port_processes:
        port_processes[service] = {}

    results = []
    for port in ports:
        try:
            port = int(port)
            if port in port_processes[service]:
                results.append({"port": port, "status": "already_open"})
            else:
                command = (
                    f"socat TCP-LISTEN:{port},fork,reuseaddr SYSTEM:echo & echo $!"
                )
                success, output, error = docker_exec(service, command)
                if success and output.strip():
                    pid = output.strip()
                    port_processes[service][port] = pid
                    results.append({"port": port, "status": "opened", "pid": pid})
                else:
                    results.append({"port": port, "status": "failed", "error": error})
        except ValueError:
            results.append({"port": port, "status": "invalid"})

    return jsonify({"status": "success", "service": service, "results": results}), 200


@app.route("/api/ports/close-all", methods=["POST"])
def close_all_ports():
    """Close all open ports on a specific service or all services"""
    data = request.get_json()
    service = data.get("service")

    if service:
        # Close all ports on a specific service
        if service not in SOCAT_SERVICES:
            return jsonify({"error": f"Service {service} not found"}), 404

        closed = []
        if service in port_processes:
            for port, pid in list(port_processes[service].items()):
                command = f"kill {pid}"
                docker_exec(service, command)
                closed.append(port)
            port_processes[service] = {}

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Closed {len(closed)} ports on {service}",
                    "service": service,
                    "closed_ports": closed,
                }
            ),
            200,
        )
    else:
        # Close all ports on all services
        results = []
        for svc in SOCAT_SERVICES:
            closed = []
            if svc in port_processes:
                for port, pid in list(port_processes[svc].items()):
                    command = f"kill {pid}"
                    docker_exec(svc, command)
                    closed.append(port)
                port_processes[svc] = {}
            results.append(
                {"service": svc, "closed_ports": closed, "count": len(closed)}
            )

        return jsonify({"status": "success", "results": results}), 200


@app.route("/api/ports/status", methods=["GET"])
def get_status():
    """Get status of all open ports"""
    service = request.args.get("service")

    if service:
        # Get status for a specific service
        if service not in SOCAT_SERVICES:
            return jsonify({"error": f"Service {service} not found"}), 404

        open_ports = list(port_processes.get(service, {}).keys())
        return (
            jsonify(
                {
                    "status": "success",
                    "service": service,
                    "open_ports": open_ports,
                    "count": len(open_ports),
                }
            ),
            200,
        )
    else:
        # Get status for all services
        all_status = []
        for svc in SOCAT_SERVICES:
            open_ports = list(port_processes.get(svc, {}).keys())
            all_status.append(
                {
                    "service": svc,
                    "open_ports": open_ports,
                    "count": len(open_ports),
                }
            )

        return jsonify({"status": "success", "services": all_status}), 200


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
