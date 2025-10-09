/**
 * Delta Reports JavaScript Module
 * Handles fetching, displaying, and interacting with delta reports
 */

const DeltaReports = (function() {
    'use strict';

    // State management
    let state = {
        scanId: null,
        currentPage: 1,
        perPage: 10,
        onlyChanges: false,
        reports: [],
        pagination: {},
        expandedReports: new Set(),
        currentReportId: null,
        loadedDetailData: {}
    };

    // DOM elements
    let elements = {};

    /**
     * Initialize the module
     */
    function init(scanId) {
        state.scanId = scanId;
        cacheElements();
        bindEvents();
        loadReports();
    }

    /**
     * Cache DOM elements
     */
    function cacheElements() {
        elements = {
            reportsList: document.getElementById('reportsList'),
            loadingSpinner: document.getElementById('loadingSpinner'),
            emptyState: document.getElementById('emptyState'),
            emptyStateMessage: document.getElementById('emptyStateMessage'),
            paginationContainer: document.getElementById('paginationContainer'),
            pagination: document.getElementById('pagination'),
            reportCount: document.getElementById('reportCount'),
            onlyChangesFilter: document.getElementById('onlyChangesFilter'),
            perPageSelect: document.getElementById('perPageSelect'),
            refreshBtn: document.getElementById('refreshBtn'),
            exportAllBtn: document.getElementById('exportAllBtn'),
            reportDetailModal: new bootstrap.Modal(document.getElementById('reportDetailModal')),
            deleteConfirmModal: new bootstrap.Modal(document.getElementById('deleteConfirmModal')),
            modalBodyContent: document.getElementById('modalBodyContent'),
            exportModalReportBtn: document.getElementById('exportModalReportBtn'),
            confirmDeleteBtn: document.getElementById('confirmDeleteBtn')
        };
    }

    /**
     * Bind event listeners
     */
    function bindEvents() {
        elements.onlyChangesFilter.addEventListener('change', handleFilterChange);
        elements.perPageSelect.addEventListener('change', handlePerPageChange);
        elements.refreshBtn.addEventListener('click', handleRefresh);
        elements.exportAllBtn.addEventListener('click', handleExportAll);
        elements.exportModalReportBtn.addEventListener('click', handleExportModalReport);
        elements.confirmDeleteBtn.addEventListener('click', handleConfirmDelete);
    }

    /**
     * Load reports from API
     */
    async function loadReports(page = 1) {
        state.currentPage = page;
        showLoading();

        try {
            const params = new URLSearchParams({
                page: state.currentPage,
                per_page: state.perPage,
                only_changes: state.onlyChanges
            });

            const response = await fetch(`/api/delta/scan/${state.scanId}/reports?${params}`);

            if (!response.ok) {
                throw new Error('Failed to fetch reports');
            }

            const data = await response.json();
            state.reports = data.reports;
            state.pagination = {
                total: data.total,
                pages: data.pages,
                currentPage: data.current_page,
                hasNext: data.has_next,
                hasPrev: data.has_prev
            };

            renderReports();
            renderPagination();
            updateReportCount();
            hideLoading();

        } catch (error) {
            console.error('Error loading reports:', error);
            showError('Failed to load delta reports. Please try again.');
            hideLoading();
        }
    }

    /**
     * Render reports list
     */
    function renderReports() {
        if (state.reports.length === 0) {
            showEmptyState();
            return;
        }

        elements.emptyState.style.display = 'none';
        elements.reportsList.innerHTML = '';

        state.reports.forEach(report => {
            const reportCard = createReportCard(report);
            elements.reportsList.appendChild(reportCard);
        });
    }

    /**
     * Create a report card element
     */
    function createReportCard(report) {
        const col = document.createElement('div');
        col.className = 'col-md-12';

        const card = document.createElement('div');
        card.className = 'report-card';
        card.dataset.reportId = report.id;

        // Header
        const header = document.createElement('div');
        header.className = 'report-card-header';
        if (state.expandedReports.has(report.id)) {
            header.classList.add('expanded');
        }
        header.onclick = () => toggleReportDetails(report.id);

        // Meta section
        const meta = document.createElement('div');
        meta.className = 'report-meta';

        // Timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'report-timestamp';
        timestamp.innerHTML = `
            <i class="far fa-clock"></i>
            ${formatDateTime(report.created_at)}
            <span class="ms-3 ${report.has_changes ? 'status-has-changes' : 'status-no-changes'} status-badge">
                ${report.has_changes ? 'Changes Detected' : 'No Changes'}
            </span>
        `;
        meta.appendChild(timestamp);

        // Badges
        if (report.has_changes) {
            const badges = document.createElement('div');
            badges.className = 'report-badges';
            badges.innerHTML = createBadgesHTML(report);
            meta.appendChild(badges);
        }

        // Scan times
        const scanTimes = document.createElement('div');
        scanTimes.className = 'report-scan-times';
        scanTimes.innerHTML = `
            Baseline: ${formatDateTime(report.baseline_scan_time)}
            <i class="fas fa-arrow-right mx-2"></i>
            Current: ${formatDateTime(report.current_scan_time)}
        `;
        meta.appendChild(scanTimes);

        header.appendChild(meta);

        // Actions
        const actions = document.createElement('div');
        actions.className = 'report-actions';
        actions.onclick = (e) => e.stopPropagation();
        actions.innerHTML = `
            <button class="btn btn-sm btn-outline-primary" onclick="DeltaReports.viewDetails(${report.id})" title="View Details">
                <i class="fas fa-eye"></i>
            </button>
            <button class="btn btn-sm btn-outline-success" onclick="DeltaReports.exportReport(${report.id})" title="Export CSV">
                <i class="fas fa-download"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger" onclick="DeltaReports.deleteReport('${report.report_id}')" title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        `;
        header.appendChild(actions);

        card.appendChild(header);

        // Details section (initially hidden)
        const details = document.createElement('div');
        details.className = 'report-details';
        details.id = `report-details-${report.id}`;
        if (state.expandedReports.has(report.id)) {
            details.classList.add('show');
            loadReportDetails(report.id, details);
        }
        card.appendChild(details);

        col.appendChild(card);
        return col;
    }

    /**
     * Create badges HTML
     */
    function createBadgesHTML(report) {
        let html = '';

        if (report.new_hosts_count > 0) {
            html += `
                <span class="change-badge badge-new-hosts">
                    <i class="fas fa-plus"></i>
                    ${report.new_hosts_count} New Host${report.new_hosts_count !== 1 ? 's' : ''}
                </span>
            `;
        }

        if (report.removed_hosts_count > 0) {
            html += `
                <span class="change-badge badge-removed-hosts">
                    <i class="fas fa-minus"></i>
                    ${report.removed_hosts_count} Removed Host${report.removed_hosts_count !== 1 ? 's' : ''}
                </span>
            `;
        }

        if (report.new_ports_count > 0) {
            html += `
                <span class="change-badge badge-new-ports">
                    <i class="fas fa-network-wired"></i>
                    ${report.new_ports_count} New Port${report.new_ports_count !== 1 ? 's' : ''}
                </span>
            `;
        }

        if (report.closed_ports_count > 0) {
            html += `
                <span class="change-badge badge-closed-ports">
                    <i class="fas fa-lock"></i>
                    ${report.closed_ports_count} Closed Port${report.closed_ports_count !== 1 ? 's' : ''}
                </span>
            `;
        }

        if (report.changed_services_count > 0) {
            html += `
                <span class="change-badge badge-changed-services">
                    <i class="fas fa-exchange-alt"></i>
                    ${report.changed_services_count} Changed Service${report.changed_services_count !== 1 ? 's' : ''}
                </span>
            `;
        }

        return html;
    }

    /**
     * Toggle report details expansion
     */
    function toggleReportDetails(reportId) {
        const detailsElement = document.getElementById(`report-details-${reportId}`);
        const headerElement = detailsElement.previousElementSibling;

        if (state.expandedReports.has(reportId)) {
            state.expandedReports.delete(reportId);
            detailsElement.classList.remove('show');
            headerElement.classList.remove('expanded');
        } else {
            state.expandedReports.add(reportId);
            detailsElement.classList.add('show');
            headerElement.classList.add('expanded');

            // Load details if not already loaded
            if (!state.loadedDetailData[reportId]) {
                loadReportDetails(reportId, detailsElement);
            }
        }
    }

    /**
     * Load report details
     */
    async function loadReportDetails(reportId, detailsElement) {
        detailsElement.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div></div>';

        try {
            const response = await fetch(`/api/delta/report/${reportId}?include_data=true`);

            if (!response.ok) {
                throw new Error('Failed to fetch report details');
            }

            const data = await response.json();
            state.loadedDetailData[reportId] = data;

            detailsElement.innerHTML = renderReportDetails(data);

        } catch (error) {
            console.error('Error loading report details:', error);
            detailsElement.innerHTML = '<div class="alert alert-danger">Failed to load report details.</div>';
        }
    }

    /**
     * Render report details HTML
     */
    function renderReportDetails(report) {
        const deltaData = report.delta_data;

        if (!deltaData) {
            return '<div class="no-changes-message"><p>No delta data available</p></div>';
        }

        let html = '';

        // New Hosts
        if (deltaData.new_hosts && deltaData.new_hosts.length > 0) {
            html += `
                <div class="delta-section">
                    <div class="delta-section-header new-hosts">
                        <i class="fas fa-server"></i>
                        New Hosts (${deltaData.new_hosts.length})
                    </div>
                    <ul class="host-list">
                        ${deltaData.new_hosts.map(host => `
                            <li><i class="fas fa-plus-circle icon-success"></i> ${host}</li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }

        // Removed Hosts
        if (deltaData.removed_hosts && deltaData.removed_hosts.length > 0) {
            html += `
                <div class="delta-section">
                    <div class="delta-section-header removed-hosts">
                        <i class="fas fa-server"></i>
                        Removed Hosts (${deltaData.removed_hosts.length})
                    </div>
                    <ul class="host-list">
                        ${deltaData.removed_hosts.map(host => `
                            <li><i class="fas fa-minus-circle icon-danger"></i> ${host}</li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }

        // Host Changes
        if (deltaData.host_changes && Object.keys(deltaData.host_changes).length > 0) {
            html += '<div class="delta-section"><div class="delta-section-header changes"><i class="fas fa-exchange-alt"></i> Host Changes</div>';

            for (const [hostIp, changes] of Object.entries(deltaData.host_changes)) {
                html += `
                    <div class="host-change-block">
                        <div class="host-change-header">
                            <i class="fas fa-network-wired"></i>
                            ${hostIp}
                        </div>
                `;

                // New Ports
                if (changes.new_ports && changes.new_ports.length > 0) {
                    html += `
                        <div class="change-subsection">
                            <div class="change-subsection-title text-success">
                                <i class="fas fa-plus"></i> New Ports
                            </div>
                            <table class="table table-sm delta-table">
                                <thead>
                                    <tr>
                                        <th>Port</th>
                                        <th>State</th>
                                        <th>Service</th>
                                        <th>Version</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${changes.new_ports.map(port => `
                                        <tr>
                                            <td class="port-number">${port.port}</td>
                                            <td><span class="badge bg-success">${port.state}</span></td>
                                            <td>${port.service || '-'}</td>
                                            <td class="text-monospace">${port.version || '-'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                }

                // Closed Ports
                if (changes.closed_ports && changes.closed_ports.length > 0) {
                    html += `
                        <div class="change-subsection">
                            <div class="change-subsection-title text-danger">
                                <i class="fas fa-minus"></i> Closed Ports
                            </div>
                            <table class="table table-sm delta-table">
                                <thead>
                                    <tr>
                                        <th>Port</th>
                                        <th>Service</th>
                                        <th>Version</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${changes.closed_ports.map(port => `
                                        <tr>
                                            <td class="port-number">${port.port}</td>
                                            <td>${port.service || '-'}</td>
                                            <td class="text-monospace">${port.version || '-'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                }

                // Changed Ports
                if (changes.changed_ports && changes.changed_ports.length > 0) {
                    html += `
                        <div class="change-subsection">
                            <div class="change-subsection-title text-warning">
                                <i class="fas fa-exchange-alt"></i> Changed Ports
                            </div>
                            <table class="table table-sm delta-table">
                                <thead>
                                    <tr>
                                        <th>Port</th>
                                        <th>Change Type</th>
                                        <th>Old Value</th>
                                        <th>New Value</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${changes.changed_ports.map(portChange => {
                                        let rows = '';
                                        for (const [changeType, vals] of Object.entries(portChange.changes)) {
                                            rows += `
                                                <tr>
                                                    <td class="port-number">${portChange.port}</td>
                                                    <td><span class="badge bg-secondary">${changeType}</span></td>
                                                    <td class="change-value-old">${vals.old || '-'}</td>
                                                    <td class="change-value-new">${vals.new || '-'}</td>
                                                </tr>
                                            `;
                                        }
                                        return rows;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                }

                html += '</div>'; // Close host-change-block
            }

            html += '</div>'; // Close delta-section
        }

        // No changes
        if (!html) {
            html = `
                <div class="no-changes-message">
                    <i class="fas fa-check-circle"></i>
                    <p>No changes detected in this scan</p>
                </div>
            `;
        }

        return html;
    }

    /**
     * View report details in modal
     */
    async function viewDetails(reportId) {
        state.currentReportId = reportId;

        elements.modalBodyContent.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>';
        elements.reportDetailModal.show();

        try {
            const response = await fetch(`/api/delta/report/${reportId}?include_data=true`);

            if (!response.ok) {
                throw new Error('Failed to fetch report details');
            }

            const data = await response.json();
            state.loadedDetailData[reportId] = data;

            elements.modalBodyContent.innerHTML = renderReportDetails(data);

        } catch (error) {
            console.error('Error loading report details:', error);
            elements.modalBodyContent.innerHTML = '<div class="alert alert-danger">Failed to load report details.</div>';
        }
    }

    /**
     * Export report as CSV
     */
    async function exportReport(reportId) {
        try {
            const response = await fetch(`/api/delta/report/${reportId}/export/csv`);

            if (!response.ok) {
                throw new Error('Failed to export report');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `delta_report_${reportId}_${Date.now()}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showSuccess('Report exported successfully!');

        } catch (error) {
            console.error('Error exporting report:', error);
            showError('Failed to export report. Please try again.');
        }
    }

    /**
     * Export modal report
     */
    function exportModalReport() {
        if (state.currentReportId) {
            exportReport(state.currentReportId);
        }
    }

    /**
     * Delete report
     */
    function deleteReport(reportId) {
        state.currentReportId = reportId;
        elements.deleteConfirmModal.show();
    }

    /**
     * Confirm delete report
     */
    async function confirmDelete() {
        if (!state.currentReportId) return;

        try {
            const response = await fetch(`/api/delta/report/${state.currentReportId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete report');
            }

            elements.deleteConfirmModal.hide();
            showSuccess('Report deleted successfully!');
            loadReports(state.currentPage);

        } catch (error) {
            console.error('Error deleting report:', error);
            showError('Failed to delete report. Please try again.');
        }
    }

    /**
     * Render pagination
     */
    function renderPagination() {
        if (state.pagination.pages <= 1) {
            elements.paginationContainer.style.display = 'none';
            return;
        }

        elements.paginationContainer.style.display = 'block';
        elements.pagination.innerHTML = '';

        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${!state.pagination.hasPrev ? 'disabled' : ''}`;
        prevLi.innerHTML = `<a class="page-link" href="#" aria-label="Previous"><span aria-hidden="true">&laquo;</span></a>`;
        if (state.pagination.hasPrev) {
            prevLi.querySelector('a').onclick = (e) => {
                e.preventDefault();
                loadReports(state.currentPage - 1);
            };
        }
        elements.pagination.appendChild(prevLi);

        // Page numbers
        const startPage = Math.max(1, state.currentPage - 2);
        const endPage = Math.min(state.pagination.pages, state.currentPage + 2);

        if (startPage > 1) {
            addPageNumber(1);
            if (startPage > 2) {
                const ellipsis = document.createElement('li');
                ellipsis.className = 'page-item disabled';
                ellipsis.innerHTML = '<span class="page-link">...</span>';
                elements.pagination.appendChild(ellipsis);
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            addPageNumber(i);
        }

        if (endPage < state.pagination.pages) {
            if (endPage < state.pagination.pages - 1) {
                const ellipsis = document.createElement('li');
                ellipsis.className = 'page-item disabled';
                ellipsis.innerHTML = '<span class="page-link">...</span>';
                elements.pagination.appendChild(ellipsis);
            }
            addPageNumber(state.pagination.pages);
        }

        // Next button
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${!state.pagination.hasNext ? 'disabled' : ''}`;
        nextLi.innerHTML = `<a class="page-link" href="#" aria-label="Next"><span aria-hidden="true">&raquo;</span></a>`;
        if (state.pagination.hasNext) {
            nextLi.querySelector('a').onclick = (e) => {
                e.preventDefault();
                loadReports(state.currentPage + 1);
            };
        }
        elements.pagination.appendChild(nextLi);
    }

    /**
     * Add page number to pagination
     */
    function addPageNumber(pageNum) {
        const li = document.createElement('li');
        li.className = `page-item ${pageNum === state.currentPage ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#">${pageNum}</a>`;

        if (pageNum !== state.currentPage) {
            li.querySelector('a').onclick = (e) => {
                e.preventDefault();
                loadReports(pageNum);
            };
        }

        elements.pagination.appendChild(li);
    }

    /**
     * Update report count display
     */
    function updateReportCount() {
        const start = (state.currentPage - 1) * state.perPage + 1;
        const end = Math.min(start + state.reports.length - 1, state.pagination.total);

        elements.reportCount.textContent =
            `Showing ${start}-${end} of ${state.pagination.total} reports`;
    }

    /**
     * Handle filter change
     */
    function handleFilterChange() {
        state.onlyChanges = elements.onlyChangesFilter.checked;
        loadReports(1);
    }

    /**
     * Handle per page change
     */
    function handlePerPageChange() {
        state.perPage = parseInt(elements.perPageSelect.value);
        loadReports(1);
    }

    /**
     * Handle refresh
     */
    function handleRefresh() {
        loadReports(state.currentPage);
    }

    /**
     * Handle export all
     */
    async function handleExportAll() {
        if (state.reports.length === 0) {
            showError('No reports to export');
            return;
        }

        const btn = elements.exportAllBtn;
        btn.classList.add('exporting');
        btn.disabled = true;

        try {
            // Export all reports for this scan
            const response = await fetch(`/api/delta/scan/${state.scanId}/export-all`);

            if (!response.ok) {
                throw new Error('Failed to export reports');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `delta_reports_scan_${state.scanId}_${Date.now()}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showSuccess('All reports exported successfully!');

        } catch (error) {
            console.error('Error exporting all reports:', error);
            showError('Failed to export reports. Please try again.');
        } finally {
            btn.classList.remove('exporting');
            btn.disabled = false;
        }
    }

    /**
     * Handle confirm delete
     */
    function handleConfirmDelete() {
        confirmDelete();
    }

    /**
     * Handle export modal report
     */
    function handleExportModalReport() {
        exportModalReport();
    }

    /**
     * Show loading state
     */
    function showLoading() {
        elements.loadingSpinner.style.display = 'block';
        elements.reportsList.style.display = 'none';
        elements.emptyState.style.display = 'none';
        elements.paginationContainer.style.display = 'none';
    }

    /**
     * Hide loading state
     */
    function hideLoading() {
        elements.loadingSpinner.style.display = 'none';
        elements.reportsList.style.display = 'block';
    }

    /**
     * Show empty state
     */
    function showEmptyState() {
        elements.emptyState.style.display = 'block';
        elements.reportsList.style.display = 'none';
        elements.paginationContainer.style.display = 'none';

        if (state.onlyChanges) {
            elements.emptyStateMessage.textContent = 'No reports with changes found.';
        } else {
            elements.emptyStateMessage.textContent = 'Delta reports will appear here after your second scan completes.';
        }

        elements.reportCount.textContent = 'Showing 0 reports';
    }

    /**
     * Show success message
     */
    function showSuccess(message) {
        showAlert(message, 'success');
    }

    /**
     * Show error message
     */
    function showError(message) {
        showAlert(message, 'danger');
    }

    /**
     * Show alert message
     */
    function showAlert(message, type) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show alert-floating`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);

        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    }

    /**
     * Format date time
     */
    function formatDateTime(isoString) {
        if (!isoString) return '-';

        const date = new Date(isoString);
        const options = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };

        return date.toLocaleString('en-US', options);
    }

    // Public API
    return {
        init,
        viewDetails,
        exportReport,
        deleteReport
    };

})();

// Make it globally available
window.DeltaReports = DeltaReports;
