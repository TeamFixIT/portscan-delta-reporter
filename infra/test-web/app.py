from flask import Flask, jsonify, render_template, request
import subprocess
import os
import re
from functools import wraps

app = Flask(__name__)
SUBNET = "172.20.0.0/16"
CHAIN_NAME = "PORT_MANAGER"

# Port validation
MIN_PORT = 1024
MAX_PORT = 65535


def validate_port(port):
    """Validate port number is in acceptable range"""
    if not isinstance(port, int) or port < MIN_PORT or port > MAX_PORT:
        return False
    return True


def init_iptables():
    """Initialize custom iptables chain"""
    # Create custom chain if it doesn't exist
    subprocess.run(
        f"iptables -N {CHAIN_NAME} 2>/dev/null || true", shell=True, capture_output=True
    )

    # Link custom chain to INPUT if not already linked
    check_cmd = f"iptables -C INPUT -j {CHAIN_NAME} 2>/dev/null"
    result = subprocess.run(check_cmd, shell=True, capture_output=True)
    if result.returncode != 0:
        subprocess.run(
            f"iptables -I INPUT -j {CHAIN_NAME}", shell=True, capture_output=True
        )


def run_command(cmd):
    """Execute shell command safely"""
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True, timeout=5
        )
        return {"success": True, "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/open/<int:port>", methods=["POST"])
def open_port(port):
    if not validate_port(port):
        return (
            jsonify(
                {"error": f"Invalid port. Must be between {MIN_PORT} and {MAX_PORT}"}
            ),
            400,
        )

    # Remove DROP rule if it exists (using -D with -C to check first)
    check_cmd = f"iptables -C {CHAIN_NAME} -p tcp --dport {port} -s {SUBNET} -j DROP 2>/dev/null"
    check_result = subprocess.run(check_cmd, shell=True, capture_output=True)

    if check_result.returncode == 0:
        # Rule exists, remove it
        cmd = f"iptables -D {CHAIN_NAME} -p tcp --dport {port} -s {SUBNET} -j DROP"
        result = run_command(cmd)
        if result["success"]:
            return jsonify({"message": f"Port {port} opened for {SUBNET}"})
        else:
            return (
                jsonify({"error": f"Error opening port {port}: {result['error']}"}),
                500,
            )
    else:
        return jsonify({"message": f"Port {port} already open for {SUBNET}"})


@app.route("/close/<int:port>", methods=["POST"])
def close_port(port):
    if not validate_port(port):
        return (
            jsonify(
                {"error": f"Invalid port. Must be between {MIN_PORT} and {MAX_PORT}"}
            ),
            400,
        )

    # Check if rule already exists to prevent duplicates
    check_cmd = f"iptables -C {CHAIN_NAME} -p tcp --dport {port} -s {SUBNET} -j DROP 2>/dev/null"
    check_result = subprocess.run(check_cmd, shell=True, capture_output=True)

    if check_result.returncode == 0:
        return jsonify({"message": f"Port {port} already closed for {SUBNET}"})

    # Add DROP rule
    cmd = f"iptables -A {CHAIN_NAME} -p tcp --dport {port} -s {SUBNET} -j DROP"
    result = run_command(cmd)

    if result["success"]:
        return jsonify({"message": f"Port {port} closed for {SUBNET}"})
    else:
        return jsonify({"error": f"Error closing port {port}: {result['error']}"}), 500


@app.route("/status/<int:port>", methods=["GET"])
def status_port(port):
    if not validate_port(port):
        return (
            jsonify(
                {"error": f"Invalid port. Must be between {MIN_PORT} and {MAX_PORT}"}
            ),
            400,
        )

    cmd = f"iptables -C {CHAIN_NAME} -p tcp --dport {port} -s {SUBNET} -j DROP 2>/dev/null"
    result = subprocess.run(cmd, shell=True, capture_output=True)
    status = "closed" if result.returncode == 0 else "open"

    return jsonify({"port": port, "status": status, "subnet": SUBNET})


@app.route("/list", methods=["GET"])
def list_rules():
    """List all current port rules"""
    cmd = f"iptables -L {CHAIN_NAME} -n --line-numbers"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        return jsonify({"rules": result.stdout})
    else:
        return jsonify({"error": "Failed to list rules"}), 500


if __name__ == "__main__":
    # Set default policy
    os.system("iptables -P INPUT ACCEPT")

    # Initialize custom chain
    init_iptables()

    app.run(host="0.0.0.0", port=5000)
