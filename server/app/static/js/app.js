// ===========================================
// Port Scanner Delta Reporter - Application JS
// ===========================================

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  // -----------------------------
  // Theme Handling
  // -----------------------------

  // Helper – set theme + storage + icon
  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-bs-theme", theme);
    localStorage.setItem("theme", theme);

    const themeIcon = document.querySelector("#theme-toggle i");
    if (themeIcon) {
      themeIcon.classList.remove(theme === "dark" ? "bi-sun" : "bi-moon");
      themeIcon.classList.add(theme === "dark" ? "bi-moon" : "bi-sun");
    }
  };

  const current = document.documentElement.getAttribute("data-bs-theme");
  applyTheme(current); // updates icon & checkbox
  const themeToggle = document.querySelector("#theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const next =
        document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      applyTheme(next);
    });
  }

  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", (e) => {
    // Only auto-switch if the user has *not* manually chosen a theme
    if (!localStorage.getItem("theme")) {
      applyTheme(e.matches ? "dark" : "light");
    }
  });

  // -----------------------------
  // Auto-dismiss Bootstrap alerts
  // -----------------------------
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 5000);
  });

  // -----------------------------
  // Bootstrap Tooltips
  // -----------------------------
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl));

  // Explicit tooltip for Help FAB (since it also opens a modal)
  const helpFab = document.getElementById("help-fab");
  const helpModal = document.getElementById("helpModal");

  if (helpFab) {
    new bootstrap.Tooltip(helpFab, {
      title: "Help / User Manual",
      placement: "left",
    });
  }

  if (helpFab && helpModal) {
    helpModal.addEventListener("shown.bs.modal", () => helpFab.classList.add("open"));
    helpModal.addEventListener("hidden.bs.modal", () => helpFab.classList.remove("open"));
  }

  // -----------------------------
  // Server-Sent Events (SSE)
  // -----------------------------
  const initSSE = () => {
    try {
      const eventSource = new EventSource("/api/stream");

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("📡 SSE:", data);

          // Handle redirect events
          if (data.type === "redirect") {
            console.log("🔄 Redirecting to:", data.url);
            window.location.href = data.url;
            return;
          }

          // Handle regular alerts
          if (data.message) {
            showAlert(data.message, data.type);
          }
        } catch (err) {
          console.error("Error parsing SSE event:", err);
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE connection error:", err);
        // Optionally: retry connection after delay
      };
    } catch (err) {
      console.error("Failed to initialize SSE:", err);
    }
  };

  // -----------------------------
  // Alert Display Function
  // -----------------------------
  const showAlert = (message, type = "info") => {
    const container = document.getElementById("alert-container") || createAlertContainer();

    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${type} fade show`;
    alertDiv.textContent = message;

    container.appendChild(alertDiv);

    // Auto-remove after 5s
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alertDiv);
      bsAlert.close();
    }, 5000);
  };

  const createAlertContainer = () => {
    const container = document.createElement("div");
    container.id = "alert-container";
    container.style.position = "fixed";
    container.style.top = "1rem";
    container.style.right = "1rem";
    container.style.zIndex = "1055"; // above modals
    document.body.appendChild(container);
    return container;
  };
  document.querySelectorAll(".utc-time").forEach((el) => {
    const raw = el.getAttribute("datetime");
    if (!raw) return;
    if (raw == "None") return;
    // If it's a naive datetime (no timezone info), assume UTC for consistency
    const utcString = raw.match(/(Z|[+-]\d{2}:\d{2})$/) ? raw : `${raw}Z`;

    const localDate = new Date(utcString);

    // Format for readability
    const formatted = localDate.toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    // Replace text content
    el.textContent = formatted;

    // Optional: tooltip showing original UTC
    el.title = `UTC: ${utcString}`;
  });

  // -----------------------------
  // Initialize SSE Connection
  // -----------------------------
  initSSE();
});

// ===========================================
// Utility Functions
// ===========================================

function formatTimestamp(timestamp) {
  return new Date(timestamp).toLocaleString();
}

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function formatDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
  if (days < 7) return `${days} day${days > 1 ? "s" : ""} ago`;

  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
