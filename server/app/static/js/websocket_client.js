/**
 * WebSocket Client for bidirectional communication
 */

class WebSocketClient {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.connectionHealth = "disconnected";
    this.heartbeatInterval = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000;
    this.callbacks = {};

    this.init();
  }

  init() {
    // Initialize Socket.IO connection
    this.socket = io({
      reconnection: true,
      reconnectionDelay: this.reconnectDelay,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.setupEventHandlers();
    this.startHeartbeat();
  }

  setupEventHandlers() {
    // Connection events
    this.socket.on("connect", () => {
      console.log("WebSocket connected");
      this.connected = true;
      this.connectionHealth = "healthy";
      this.reconnectAttempts = 0;
      this.updateHealthIndicator();
      this.triggerCallback("connected");
    });

    this.socket.on("disconnect", (reason) => {
      console.log("WebSocket disconnected:", reason);
      this.connected = false;
      this.connectionHealth = "disconnected";
      this.updateHealthIndicator();
      this.triggerCallback("disconnected", reason);
    });

    this.socket.on("connect_error", (error) => {
      console.error("WebSocket connection error:", error);
      this.reconnectAttempts++;
      this.connectionHealth = "error";
      this.updateHealthIndicator();
    });

    // Custom events
    this.socket.on("connected", () => {
      this.showFlash("Connected to server", "success");
    });

    this.socket.on("alert", (data) => {
      this.handleAlert(data);
    });

    this.socket.on("heartbeat_ack", () => {
      this.connectionHealth = "healthy";
      this.updateHealthIndicator();
    });

    this.socket.on("health_status", (data) => {
      this.handleHealthStatus(data);
    });
  }

  startHeartbeat() {
    // Send heartbeat every 15 seconds
    this.heartbeatInterval = setInterval(() => {
      if (this.connected) {
        this.socket.emit("heartbeat", {
          timestamp: new Date().toISOString(),
        });
      }
    }, 15000);
  }

  handleAlert(data) {
    this.showAlert(data.message, data.category);
    this.triggerCallback("alert", data);
  }

  handleHealthStatus(data) {
    this.connectionHealth = data.status;
    this.updateHealthIndicator();
    this.triggerCallback("health_status", data);
  }

  showAlert(message, category = "info") {
    const container = document.getElementById("websocket-alerts");

    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-bg-${
      category === "error" ? "danger" : category
    } border-0 show`;
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.setAttribute("aria-atomic", "true");

    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    `;

    container.appendChild(toast);

    // Automatically remove toast after 5 seconds
    setTimeout(() => {
      toast.classList.remove("show");
      toast.classList.add("hide");
      setTimeout(() => toast.remove(), 500);
    }, 5000);
  }

  updateHealthIndicator() {
    // Update health indicator in the UI
    const indicator = document.getElementById("websocket-health");
    if (indicator) {
      const statusColors = {
        healthy: "success",
        degraded: "warning",
        disconnected: "danger",
        error: "danger",
      };

      const statusLabels = {
        healthy: "Connected",
        degraded: "Degraded",
        disconnected: "Disconnected",
        error: "Error",
      };

      const color = statusColors[this.connectionHealth] || "secondary";
      const label = statusLabels[this.connectionHealth] || "Unknown";

      indicator.outerHTML = `
                <span class="badge bg-${color}">
                     ${label}
                </span>
            `;
    }
  }

  requestHealth() {
    if (this.connected) {
      this.socket.emit("request_health");
    }
  }

  subscribe(channel) {
    if (this.connected) {
      this.socket.emit("subscribe", { channel: channel });
    }
  }

  unsubscribe(channel) {
    if (this.connected) {
      this.socket.emit("unsubscribe", { channel: channel });
    }
  }

  on(event, callback) {
    if (!this.callbacks[event]) {
      this.callbacks[event] = [];
    }
    this.callbacks[event].push(callback);
  }

  triggerCallback(event, data) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach((callback) => callback(data));
    }
  }

  getConnectionStatus() {
    return {
      connected: this.connected,
      health: this.connectionHealth,
      reconnectAttempts: this.reconnectAttempts,
    };
  }

  disconnect() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}

// Initialize WebSocket client when DOM is ready
let wsClient = null;

document.addEventListener("DOMContentLoaded", function () {
  wsClient = new WebSocketClient();

  // Make it globally accessible
  window.wsClient = wsClient;

  // Request health status every 30 seconds
  setInterval(() => {
    if (wsClient.connected) {
      wsClient.requestHealth();
    }
  }, 30000);
});
