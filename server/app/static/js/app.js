// Application JavaScript for Port Scanner Delta Reporter

document.addEventListener("DOMContentLoaded", function () {
  (() => {
    "use strict";

    // Get stored theme from localStorage
    const getStoredTheme = () => localStorage.getItem("theme") || "light";

    // Set theme in localStorage
    const setStoredTheme = (theme) => localStorage.setItem("theme", theme);

    // Apply theme by setting data-bs-theme on <html>
    const setTheme = (theme) => {
      document.documentElement.setAttribute("data-bs-theme", theme);
      // Update button icon
      const themeIcon = document.querySelector("#theme-toggle i");
      if (themeIcon) {
        themeIcon.classList.remove(theme === "dark" ? "bi-sun" : "bi-moon");
        themeIcon.classList.add(theme === "dark" ? "bi-moon" : "bi-sun");
      }
    };

    // initialise theme on page load
    window.addEventListener("DOMContentLoaded", () => {
      const theme = getStoredTheme();
      setTheme(theme);

      // Toggle theme on button click
      const themeToggle = document.querySelector("#theme-toggle");
      if (themeToggle) {
        themeToggle.addEventListener("click", () => {
          const currentTheme =
            document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
          setStoredTheme(currentTheme);
          setTheme(currentTheme);
        });
      }
    });
  })();
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // initialise tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Initialize tooltip for Help FAB explicitly (since it also triggers a modal)
  const helpFab = document.getElementById("help-fab");
  if (helpFab) {
    new bootstrap.Tooltip(helpFab, { title: "Help / User Manual", placement: "left" });
  }

  // === Theme Toggle ===
  const toggle = document.getElementById("theme-toggle");
  const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)");
  const savedTheme = localStorage.getItem("theme");

  // Apply saved or system-preferred theme
  if (savedTheme === "dark" || (!savedTheme && prefersDarkScheme.matches)) {
    document.body.classList.add("dark-theme");
    toggle.innerHTML = '<i class="bi bi-sun"></i>';
  } else {
    document.body.classList.remove("dark-theme");
    toggle.innerHTML = '<i class="bi bi-moon"></i>';
  }

  // Toggle theme on button click
  toggle.addEventListener("click", () => {
    document.body.classList.toggle("dark-theme");
    const isDark = document.body.classList.contains("dark-theme");
    toggle.innerHTML = isDark ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon"></i>';
    localStorage.setItem("theme", isDark ? "dark" : "light");
  });

  // Enlarge help icon when Help modal is open
  const helpModalEl = document.getElementById("helpModal");
  if (helpFab && helpModalEl) {
    helpModalEl.addEventListener("shown.bs.modal", () => helpFab.classList.add("open"));
    helpModalEl.addEventListener("hidden.bs.modal", () => helpFab.classList.remove("open"));
  }

  // === Real-time client status updates (placeholder for WebSocket) ===
  function updateClientStatus() {
    // TODO: Implement WebSocket connection for real-time updates
    console.log("Client status update check");
  }

  // Check for updates every 30 seconds
  setInterval(updateClientStatus, 30000);
});

// === Utility functions ===
function formatTimestamp(timestamp) {
  return new Date(timestamp).toLocaleString();
}

function formatDuration(seconds) {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  } else if (seconds < 3600) {
    return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  } else {
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  }
}

// Format Date
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
