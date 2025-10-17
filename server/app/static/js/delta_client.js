// Configuration
let currentPage = 1;
let perPage = 10;
let onlyChanges = false;
let currentReportId = null;

// Show/Hide Loading
function showLoading(show = true) {
  document.getElementById("loadingSpinner").style.display = show ? "block" : "none";
  document.getElementById("reportsList").style.display = show ? "none" : "block";
}

// Update Summary Cards
function updateSummary(data) {
  document.getElementById("totalReports").textContent = data.total || 0;

  const withChanges = data.reports ? data.reports.filter((r) => r.has_changes).length : 0;
  document.getElementById("reportsWithChanges").textContent = withChanges;

  const totalNewHosts = data.reports
    ? data.reports.reduce((sum, r) => sum + (r.new_hosts_count || 0), 0)
    : 0;
  document.getElementById("totalNewHosts").textContent = totalNewHosts;

  const totalNewPorts = data.reports
    ? data.reports.reduce((sum, r) => sum + (r.new_ports_count || 0), 0)
    : 0;
  document.getElementById("totalNewPorts").textContent = totalNewPorts;
}

// Render Reports
function renderReports(data) {
  const container = document.getElementById("reportsList");
  const emptyState = document.getElementById("emptyState");

  if (!data.reports || data.reports.length === 0) {
    container.innerHTML = "";
    emptyState.style.display = "block";
    document.getElementById("paginationContainer").style.display = "none";

    if (onlyChanges) {
      document.getElementById("emptyStateMessage").textContent =
        "No reports with changes found. Try removing the filter.";
    } else {
      document.getElementById("emptyStateMessage").textContent =
        "Delta reports will appear here after your second scan completes.";
    }
    return;
  }

  emptyState.style.display = "none";

  container.innerHTML = data.reports
    .map(
      (report) => `
                <div class="col-lg-6 col-xl-4">
                    <div class="card report-card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-3">
                                <div>
                                    <h5 class="card-title mb-1">
                                        <i class="fas fa-file-alt text-primary me-2"></i>Report #${
                                          report.id
                                        }
                                    </h5>
                                    <small class="text-muted">
                                        <i class="far fa-clock me-1"></i>${formatDate(
                                          report.created_at
                                        )}
                                    </small>
                                </div>
                                <span class="change-indicator ${
                                  report.has_changes ? "has-changes" : "no-changes"
                                }">
                                    <i class="fas ${
                                      report.has_changes
                                        ? "fa-exclamation-circle"
                                        : "fa-check-circle"
                                    }"></i>
                                    ${report.has_changes ? "Changes" : "No Changes"}
                                </span>
                            </div>

                            <div class="row g-2 mb-3">
                                <div class="col-6">
                                    <div class="p-2 rounded bg-success bg-opacity-10 text-center">
                                        <div class="fs-4 fw-bold text-success">${
                                          report.new_hosts_count || 0
                                        }</div>
                                        <small class="text-muted">New Hosts</small>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 rounded bg-info bg-opacity-10 text-center">
                                        <div class="fs-4 fw-bold text-info">${
                                          report.new_ports_count || 0
                                        }</div>
                                        <small class="text-muted">New Ports</small>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 rounded bg-danger bg-opacity-10 text-center">
                                        <div class="fs-4 fw-bold text-danger">${
                                          report.closed_ports_count || 0
                                        }</div>
                                        <small class="text-muted">Closed Ports</small>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-2 rounded bg-warning bg-opacity-10 text-center">
                                        <div class="fs-4 fw-bold text-warning">${
                                          report.changed_services_count || 0
                                        }</div>
                                        <small class="text-muted">Changed Services</small>
                                    </div>
                                </div>
                            </div>

                            <div class="d-flex gap-2 flex-wrap mb-3">
                                <span class="badge badge-metric bg-secondary">
                                    <i class="fas fa-arrow-right me-1"></i>
                                    ${report.baseline_result_id} → ${report.current_result_id}
                                </span>
                                <span class="badge badge-metric bg-primary">
                                    <i class="fas fa-database me-1"></i>
                                    Scan #${report.scan_id}
                                </span>
                                <span class="badge badge-metric bg-info">
                                    <i class="fas fa-info-circle me-1"></i>
                                    ${report.status}
                                </span>
                            </div>

                            <div class="d-flex gap-2">
                                <button class="btn btn-sm btn-outline-primary flex-grow-1" onclick="viewReport(${
                                  report.id
                                })">
                                    <i class="fas fa-eye me-1"></i> View
                                </button>
                                <button class="btn btn-sm btn-outline-success" onclick="exportReport(${
                                  report.id
                                })">
                                    <i class="fas fa-download"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="confirmDelete(${
                                  report.id
                                })">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `
    )
    .join("");

  renderPagination(data);
}

// Render Pagination
function renderPagination(data) {
  const container = document.getElementById("pagination");
  const paginationContainer = document.getElementById("paginationContainer");

  if (data.pages <= 1) {
    paginationContainer.style.display = "none";
    return;
  }

  paginationContainer.style.display = "block";

  let html = "";

  // Previous
  html += `
                <li class="page-item ${!data.has_prev ? "disabled" : ""}">
                    <a class="page-link" href="#" onclick="changePage(${
                      data.current_page - 1
                    }); return false;">
                        <i class="fas fa-chevron-left"></i>
                    </a>
                </li>
            `;

  // Pages
  for (let i = 1; i <= data.pages; i++) {
    if (i === 1 || i === data.pages || (i >= data.current_page - 2 && i <= data.current_page + 2)) {
      html += `
                        <li class="page-item ${i === data.current_page ? "active" : ""}">
                            <a class="page-link" href="#" onclick="changePage(${i}); return false;">${i}</a>
                        </li>
                    `;
    } else if (i === data.current_page - 3 || i === data.current_page + 3) {
      html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
    }
  }

  // Next
  html += `
                <li class="page-item ${!data.has_next ? "disabled" : ""}">
                    <a class="page-link" href="#" onclick="changePage(${
                      data.current_page + 1
                    }); return false;">
                        <i class="fas fa-chevron-right"></i>
                    </a>
                </li>
            `;

  container.innerHTML = html;
}

// Update Report Count
function updateReportCount(data) {
  const start = (data.current_page - 1) * data.per_page + 1;
  const end = Math.min(data.current_page * data.per_page, data.total);
  document.getElementById("reportCount").textContent =
    data.total > 0 ? `Showing ${start}-${end} of ${data.total} reports` : "No reports found";
}

// Change Page
function changePage(page) {
  currentPage = page;
  loadReports();
}

// Load Reports from API
async function loadReports() {
  showLoading(true);

  try {
    const params = new URLSearchParams({
      page: currentPage,
      per_page: perPage,
      only_changes: onlyChanges,
    });

    const response = await fetch(`/api/scan/${SCAN_ID}/reports?${params}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    updateSummary(data);
    renderReports(data);
    updateReportCount(data);
  } catch (error) {
    console.error("Error loading reports:", error);
    showError("Failed to load delta reports. Please try again.");
  } finally {
    showLoading(false);
  }
}

// View Report Detail
async function viewReport(id) {
  currentReportId = id;
  const modal = new bootstrap.Modal(document.getElementById("reportDetailModal"));
  const modalBody = document.getElementById("modalBodyContent");

  // Show loading
  modalBody.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;

  modal.show();

  try {
    const response = await fetch(`/api/report/${id}?include_data=true`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const report = await response.json();

    modalBody.innerHTML = `
                    <div class="timeline">
                        <div class="timeline-item">
                            <h6 class="mb-2">Report Information</h6>
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <strong>Report ID:</strong> ${report.id}
                                </div>
                                <div class="col-md-6">
                                    <strong>Status:</strong> 
                                    <span class="badge bg-${
                                      report.status === "completed" ? "success" : "warning"
                                    }">
                                        ${report.status}
                                    </span>
                                </div>
                                <div class="col-md-6">
                                    <strong>Created:</strong> ${formatDate(report.created_at)}
                                </div>
                                <div class="col-md-6">
                                    <strong>Scan ID:</strong> ${report.scan_id}
                                </div>
                                <div class="col-md-6">
                                    <strong>Baseline Result:</strong> ${report.baseline_result_id}
                                </div>
                                <div class="col-md-6">
                                    <strong>Current Result:</strong> ${report.current_result_id}
                                </div>
                            </div>
                        </div>

                        ${
                          report.has_changes
                            ? `
                        <div class="timeline-item">
                            <h6 class="mb-3">Changes Detected</h6>
                            
                            ${
                              report.new_hosts && report.new_hosts.length > 0
                                ? `
                            <div class="mb-4">
                                <h6 class="text-success">
                                    <i class="fas fa-plus-circle me-1"></i> New Hosts (${
                                      report.new_hosts.length
                                    })
                                </h6>
                                <div class="table-responsive">
                                    <table class="table table-sm table-hover">
                                        <thead>
                                            <tr>
                                                <th>IP Address</th>
                                                <th>Hostname</th>
                                                <th>Ports</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${report.new_hosts
                                              .map(
                                                (host) => `
                                                <tr>
                                                    <td><code>${host.ip_address}</code></td>
                                                    <td>${host.hostname || "N/A"}</td>
                                                    <td>${host.port_count || 0}</td>
                                                </tr>
                                            `
                                              )
                                              .join("")}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            `
                                : ""
                            }

                            ${
                              report.new_ports && report.new_ports.length > 0
                                ? `
                            <div class="mb-4">
                                <h6 class="text-info">
                                    <i class="fas fa-door-open me-1"></i> New Ports (${
                                      report.new_ports.length
                                    })
                                </h6>
                                <div class="table-responsive">
                                    <table class="table table-sm table-hover">
                                        <thead>
                                            <tr>
                                                <th>Host</th>
                                                <th>Port</th>
                                                <th>Service</th>
                                                <th>State</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${report.new_ports
                                              .map(
                                                (port) => `
                                                <tr>
                                                    <td><code>${port.ip_address}</code></td>
                                                    <td><span class="badge bg-primary">${
                                                      port.port_number
                                                    }</span></td>
                                                    <td>${port.service_name || "unknown"}</td>
                                                    <td><span class="badge bg-success">${
                                                      port.state || "open"
                                                    }</span></td>
                                                </tr>
                                            `
                                              )
                                              .join("")}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            `
                                : ""
                            }

                            ${
                              report.closed_ports && report.closed_ports.length > 0
                                ? `
                            <div class="mb-4">
                                <h6 class="text-danger">
                                    <i class="fas fa-door-closed me-1"></i> Closed Ports (${
                                      report.closed_ports.length
                                    })
                                </h6>
                                <div class="table-responsive">
                                    <table class="table table-sm table-hover">
                                        <thead>
                                            <tr>
                                                <th>Host</th>
                                                <th>Port</th>
                                                <th>Previous Service</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${report.closed_ports
                                              .map(
                                                (port) => `
                                                <tr>
                                                    <td><code>${port.ip_address}</code></td>
                                                    <td><span class="badge bg-secondary">${
                                                      port.port_number
                                                    }</span></td>
                                                    <td>${port.previous_service || "unknown"}</td>
                                                </tr>
                                            `
                                              )
                                              .join("")}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            `
                                : ""
                            }

                            ${
                              report.changed_services && report.changed_services.length > 0
                                ? `
                            <div class="mb-4">
                                <h6 class="text-warning">
                                    <i class="fas fa-exchange-alt me-1"></i> Changed Services (${
                                      report.changed_services.length
                                    })
                                </h6>
                                <div class="table-responsive">
                                    <table class="table table-sm table-hover">
                                        <thead>
                                            <tr>
                                                <th>Host</th>
                                                <th>Port</th>
                                                <th>Previous Service</th>
                                                <th>Current Service</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${report.changed_services
                                              .map(
                                                (service) => `
                                                <tr>
                                                    <td><code>${service.ip_address}</code></td>
                                                    <td><span class="badge bg-primary">${
                                                      service.port_number
                                                    }</span></td>
                                                    <td>${
                                                      service.previous_service || "unknown"
                                                    }</td>
                                                    <td>${service.current_service || "unknown"}</td>
                                                </tr>
                                            `
                                              )
                                              .join("")}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            `
                                : ""
                            }

                        </div>
                        `
                            : `
                        <div class="timeline-item">
                            <div class="alert alert-info mb-0">
                                <i class="fas fa-info-circle me-2"></i>
                                No changes detected between the baseline and current scan results.
                            </div>
                        </div>
                        `
                        }
                    </div>
                `;
  } catch (error) {
    console.error("Error loading report details:", error);
    modalBody.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load report details. Please try again.
                    </div>
                `;
  }
}

// Export Single Report
async function exportReport(id) {
  try {
    const response = await fetch(`/api/report/${id}/export`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = `delta-report-${id}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showToast("Report exported successfully!", "success");
  } catch (error) {
    console.error("Error exporting report:", error);
    showToast("Failed to export report", "error");
  }
}

// Export All Reports
async function exportAllReports() {
  try {
    const params = new URLSearchParams({
      only_changes: onlyChanges,
    });

    const response = await fetch(`/api/scan/${SCAN_ID}/reports/export?${params}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = `all-delta-reports-scan-${SCAN_ID}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showToast("All reports exported successfully!", "success");
  } catch (error) {
    console.error("Error exporting all reports:", error);
    showToast("Failed to export reports", "error");
  }
}

// Confirm Delete
function confirmDelete(id) {
  currentReportId = id;
  const modal = new bootstrap.Modal(document.getElementById("deleteConfirmModal"));
  modal.show();
}

// Delete Report
async function deleteReport() {
  if (!currentReportId) return;

  try {
    const response = await fetch(`/api/report/${currentReportId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById("deleteConfirmModal"));
    modal.hide();

    // Reload reports
    loadReports();

    showToast("Report deleted successfully", "success");
  } catch (error) {
    console.error("Error deleting report:", error);
    showToast("Failed to delete report", "error");
  }
}

// Show Toast Notification
function showToast(message, type = "info") {
  // Create toast container if it doesn't exist
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container position-fixed top-0 end-0 p-3";
    container.style.zIndex = "9999";
    document.body.appendChild(container);
  }

  const toastId = "toast-" + Date.now();
  const bgColor =
    type === "success"
      ? "bg-success"
      : type === "error"
      ? "bg-danger"
      : type === "warning"
      ? "bg-warning"
      : "bg-info";

  const toastHTML = `
                <div id="${toastId}" class="toast align-items-center text-white ${bgColor} border-0" role="alert">
                    <div class="d-flex">
                        <div class="toast-body">
                            <i class="fas ${
                              type === "success"
                                ? "fa-check-circle"
                                : type === "error"
                                ? "fa-exclamation-circle"
                                : type === "warning"
                                ? "fa-exclamation-triangle"
                                : "fa-info-circle"
                            } me-2"></i>
                            ${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                </div>
            `;

  container.insertAdjacentHTML("beforeend", toastHTML);

  const toastElement = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
  toast.show();

  // Remove toast from DOM after it's hidden
  toastElement.addEventListener("hidden.bs.toast", () => {
    toastElement.remove();
  });
}

// Show Error Message
function showError(message) {
  const container = document.getElementById("reportsList");
  container.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-danger d-flex align-items-center" role="alert">
                        <i class="fas fa-exclamation-triangle fa-2x me-3"></i>
                        <div>
                            <h5 class="alert-heading mb-1">Error Loading Reports</h5>
                            <p class="mb-0">${message}</p>
                        </div>
                    </div>
                </div>
            `;
}

// Event Listeners
document.addEventListener("DOMContentLoaded", function () {
  // Load initial data
  loadReports();

  // Event listeners
  document.getElementById("refreshBtn").addEventListener("click", loadReports);
  document.getElementById("exportAllBtn").addEventListener("click", exportAllReports);
  document.getElementById("onlyChangesFilter").addEventListener("change", function () {
    onlyChanges = this.checked;
    currentPage = 1;
    loadReports();
  });
  document.getElementById("perPageSelect").addEventListener("change", function () {
    perPage = parseInt(this.value);
    currentPage = 1;
    loadReports();
  });
  document.getElementById("confirmDeleteBtn").addEventListener("click", deleteReport);
  document.getElementById("exportModalReportBtn").addEventListener("click", function () {
    if (currentReportId) {
      exportReport(currentReportId);
    }
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", function (e) {
    if (e.key === "r" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      loadReports();
    }
    if (e.key === "Escape") {
      const modals = document.querySelectorAll(".modal.show");
      if (modals.length > 0) {
        bootstrap.Modal.getInstance(modals[0]).hide();
      }
    }
  });
});
