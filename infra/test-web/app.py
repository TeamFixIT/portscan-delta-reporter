from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import subprocess
import signal
import os

app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    """Serve the main HTML page"""
    return send_from_directory(".", "index.html")


@app.route("/assets/<filename>")
def serve_asset(filename):
    """Serve static assets from the assets directory"""
    return send_from_directory("./assets", filename)


# Dictionary to track PIDs of socat processes by port
port_processes = {}


def start_port_listener(port):
    """Start a socat listener on the specified port"""
    try:
        # Start socat in background and capture PID
        process = subprocess.Popen(
            ["socat", f"TCP-LISTEN:{port},fork,reuseaddr", "SYSTEM:echo"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        port_processes[port] = process.pid
        return True, process.pid
    except Exception as e:
        return False, str(e)


def stop_port_listener(port):
    """Stop the socat listener on the specified port"""
    try:
        if port in port_processes:
            pid = port_processes[port]
            os.kill(pid, signal.SIGTERM)
            del port_processes[port]
            return True, f"Closed port {port} (PID: {pid})"
        else:
            # Try to find and kill the process anyway
            subprocess.run(["pkill", "-f", f"socat.*LISTEN:{port}"], check=False)
            return True, f"Attempted to close port {port}"
    except Exception as e:
        return False, str(e)


@app.route("/api/ports/open", methods=["POST"])
def open_port():
    """Open a port"""
    data = request.get_json()
    port = data.get("port")

    if not port:
        return jsonify({"error": "Port number required"}), 400

    try:
        port = int(port)
        if port < 1 or port > 65535:
            return jsonify({"error": "Port must be between 1 and 65535"}), 400
    except ValueError:
        return jsonify({"error": "Invalid port number"}), 400

    if port in port_processes:
        return jsonify({"error": f"Port {port} is already open"}), 400

    success, result = start_port_listener(port)

    if success:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Port {port} opened",
                    "port": port,
                    "pid": result,
                }
            ),
            200,
        )
    else:
        return jsonify({"error": f"Failed to open port: {result}"}), 500


@app.route("/api/ports/close", methods=["POST"])
def close_port():
    """Close a port"""
    data = request.get_json()
    port = data.get("port")

    if not port:
        return jsonify({"error": "Port number required"}), 400

    try:
        port = int(port)
    except ValueError:
        return jsonify({"error": "Invalid port number"}), 400

    success, result = stop_port_listener(port)

    if success:
        return jsonify({"status": "success", "message": result, "port": port}), 200
    else:
        return jsonify({"error": f"Failed to close port: {result}"}), 500


@app.route("/api/ports/open-multiple", methods=["POST"])
def open_multiple_ports():
    """Open multiple ports at once"""
    data = request.get_json()
    ports = data.get("ports", [])

    if not ports or not isinstance(ports, list):
        return jsonify({"error": "Ports array required"}), 400

    results = []
    for port in ports:
        try:
            port = int(port)
            if port in port_processes:
                results.append({"port": port, "status": "already_open"})
            else:
                success, pid = start_port_listener(port)
                if success:
                    results.append({"port": port, "status": "opened", "pid": pid})
                else:
                    results.append(
                        {"port": port, "status": "failed", "error": str(pid)}
                    )
        except ValueError:
            results.append({"port": port, "status": "invalid"})

    return jsonify({"status": "success", "results": results}), 200


@app.route("/api/ports/close-all", methods=["POST"])
def close_all_ports():
    """Close all open ports"""
    closed = []
    for port in list(port_processes.keys()):
        success, result = stop_port_listener(port)
        if success:
            closed.append(port)

    return (
        jsonify(
            {
                "status": "success",
                "message": f"Closed {len(closed)} ports",
                "closed_ports": closed,
            }
        ),
        200,
    )


@app.route("/api/ports/status", methods=["GET"])
def get_status():
    """Get status of all open ports"""
    return (
        jsonify(
            {
                "status": "success",
                "open_ports": list(port_processes.keys()),
                "count": len(port_processes),
            }
        ),
        200,
    )


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
