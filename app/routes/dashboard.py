from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.scan import Scan
from app.models.scan_result import ScanResult
from src.scanner import NetworkScanner
from datetime import datetime, timedelta
import json

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index():
    """Dashboard home page with overview statistics"""
    
    # Get user's scan statistics
    total_scans = current_user.scans.count()
    active_scans = current_user.scans.filter_by(is_active=True).count()
    recent_scans = current_user.scans.order_by(Scan.updated_at.desc()).limit(5).all()
    
    # Get recent scan results
    recent_results = ScanResult.query.join(Scan).filter(
        Scan.user_id == current_user.id
    ).order_by(ScanResult.created_at.desc()).limit(10).all()
    
    # Calculate success rate for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_results_count = ScanResult.query.join(Scan).filter(
        Scan.user_id == current_user.id,
        ScanResult.created_at >= thirty_days_ago
    ).count()
    
    successful_results_count = ScanResult.query.join(Scan).filter(
        Scan.user_id == current_user.id,
        ScanResult.created_at >= thirty_days_ago,
        ScanResult.status == 'completed'
    ).count()
    
    success_rate = (successful_results_count / recent_results_count * 100) if recent_results_count > 0 else 0
    
    # Get system information
    scanner = NetworkScanner()
    try:
        system_info = scanner.get_system_info()
    except Exception as e:
        system_info = None
        flash(f'Could not retrieve system information: {str(e)}', 'warning')
    
    stats = {
        'total_scans': total_scans,
        'active_scans': active_scans,
        'recent_results_count': recent_results_count,
        'success_rate': round(success_rate, 1)
    }
    
    return render_template('dashboard/index.html',
                         stats=stats,
                         recent_scans=recent_scans,
                         recent_results=recent_results,
                         system_info=system_info)


@bp.route('/scans')
@login_required
def scans():
    """Scan management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    scans_query = current_user.scans.order_by(Scan.updated_at.desc())
    scans_pagination = scans_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('dashboard/scans.html', 
                         scans=scans_pagination.items,
                         pagination=scans_pagination)


@bp.route('/scans/new', methods=['GET', 'POST'])
@login_required
def new_scan():
    """Create new scan configuration"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        target = data.get('target', '').strip()
        ports = data.get('ports', '').strip()
        scan_arguments = data.get('scan_arguments', '-sV').strip()
        interval_minutes = int(data.get('interval_minutes', 60))
        is_scheduled = bool(data.get('is_scheduled', False))
        
        # Validation
        errors = []
        scanner = NetworkScanner()
        
        if not name:
            errors.append('Scan name is required')
        elif len(name) < 3:
            errors.append('Scan name must be at least 3 characters long')
        
        if not target:
            errors.append('Target is required')
        elif not scanner.validate_target(target):
            errors.append('Invalid target format. Use IP address or CIDR notation (e.g., 192.168.1.0/24)')
        
        if not ports:
            errors.append('Ports specification is required')
        elif not scanner.validate_ports(ports):
            errors.append('Invalid ports format. Use comma-separated ports (22,80,443) or ranges (1-1024)')
        
        if interval_minutes < 1:
            errors.append('Scan interval must be at least 1 minute')
        elif interval_minutes > 10080:  # 1 week
            errors.append('Scan interval cannot exceed 1 week (10080 minutes)')
        
        # Check for duplicate scan names
        existing_scan = current_user.scans.filter_by(name=name).first()
        if existing_scan:
            errors.append('A scan with this name already exists')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('dashboard/new_scan.html')
        
        # Create new scan
        try:
            scan = Scan(
                user_id=current_user.id,
                name=name,
                description=description if description else None,
                target=target,
                ports=ports,
                scan_arguments=scan_arguments,
                interval_minutes=interval_minutes,
                is_scheduled=is_scheduled
            )
            
            db.session.add(scan)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Scan created successfully',
                    'scan_id': scan.id,
                    'redirect': url_for('dashboard.view_scan', scan_id=scan.id)
                })
            
            flash('Scan created successfully!', 'success')
            return redirect(url_for('dashboard.view_scan', scan_id=scan.id))
            
        except Exception as e:
            db.session.rollback()
            error = f'Failed to create scan: {str(e)}'
            
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 500
            
            flash(error, 'error')
    
    return render_template('dashboard/new_scan.html')


@bp.route('/scans/<int:scan_id>')
@login_required
def view_scan(scan_id):
    """View scan details and results"""
    scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first_or_404()
    
    # Get paginated results
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    results_pagination = scan.results.order_by(ScanResult.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('dashboard/view_scan.html',
                         scan=scan,
                         results=results_pagination.items,
                         pagination=results_pagination)


@bp.route('/scans/<int:scan_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_scan(scan_id):
    """Edit scan configuration"""
    scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        target = data.get('target', '').strip()
        ports = data.get('ports', '').strip()
        scan_arguments = data.get('scan_arguments', '-sV').strip()
        interval_minutes = int(data.get('interval_minutes', 60))
        is_scheduled = bool(data.get('is_scheduled', False))
        is_active = bool(data.get('is_active', True))
        
        # Validation (similar to new_scan)
        errors = []
        scanner = NetworkScanner()
        
        if not name:
            errors.append('Scan name is required')
        elif len(name) < 3:
            errors.append('Scan name must be at least 3 characters long')
        
        if not target:
            errors.append('Target is required')
        elif not scanner.validate_target(target):
            errors.append('Invalid target format')
        
        if not ports:
            errors.append('Ports specification is required')
        elif not scanner.validate_ports(ports):
            errors.append('Invalid ports format')
        
        if interval_minutes < 1 or interval_minutes > 10080:
            errors.append('Invalid scan interval')
        
        # Check for duplicate names (excluding current scan)
        existing_scan = current_user.scans.filter(
            Scan.name == name, Scan.id != scan.id
        ).first()
        if existing_scan:
            errors.append('A scan with this name already exists')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('dashboard/edit_scan.html', scan=scan)
        
        # Update scan
        try:
            scan.name = name
            scan.description = description if description else None
            scan.target = target
            scan.ports = ports
            scan.scan_arguments = scan_arguments
            scan.interval_minutes = interval_minutes
            scan.is_scheduled = is_scheduled
            scan.is_active = is_active
            scan.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Scan updated successfully',
                    'redirect': url_for('dashboard.view_scan', scan_id=scan.id)
                })
            
            flash('Scan updated successfully!', 'success')
            return redirect(url_for('dashboard.view_scan', scan_id=scan.id))
            
        except Exception as e:
            db.session.rollback()
            error = f'Failed to update scan: {str(e)}'
            
            if request.is_json:
                return jsonify({'success': False, 'error': error}), 500
            
            flash(error, 'error')
    
    return render_template('dashboard/edit_scan.html', scan=scan)


@bp.route('/scans/<int:scan_id>/delete', methods=['POST'])
@login_required
def delete_scan(scan_id):
    """Delete scan and all its results"""
    scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first_or_404()
    
    try:
        scan_name = scan.name
        db.session.delete(scan)
        db.session.commit()
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': f'Scan "{scan_name}" deleted successfully',
                'redirect': url_for('dashboard.scans')
            })
        
        flash(f'Scan "{scan_name}" deleted successfully!', 'success')
        return redirect(url_for('dashboard.scans'))
        
    except Exception as e:
        db.session.rollback()
        error = f'Failed to delete scan: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        
        flash(error, 'error')
        return redirect(url_for('dashboard.view_scan', scan_id=scan_id))


@bp.route('/scans/<int:scan_id>/run', methods=['POST'])
@login_required
def run_scan_now(scan_id):
    """Run a scan immediately"""
    scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first_or_404()
    
    if not scan.is_active:
        error = 'Cannot run inactive scan'
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('dashboard.view_scan', scan_id=scan_id))
    
    try:
        # Create new scan result record
        scan_result = ScanResult(
            scan_id=scan.id,
            status='running'
        )
        db.session.add(scan_result)
        db.session.commit()
        
        # Initialize scanner and run scan
        scanner = NetworkScanner()
        
        try:
            # Mark as running
            scan_result.mark_running()
            
            # Execute scan
            results = scanner.scan_target(
                target=scan.target,
                ports=scan.ports,
                scan_args=scan.scan_arguments
            )
            
            # Save results to file
            results_file = scanner.save_results(results, f"scan_{scan_result.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            # Prepare results data for database
            results_data = {
                'scan_metadata': {
                    'total_hosts': len(results),
                    'scan_time': datetime.now().isoformat(),
                    'scanner_version': '2.0',
                    'results_file': results_file
                },
                'results': [
                    {
                        'host': r.host,
                        'hostname': r.hostname,
                        'state': r.state,
                        'ports': r.ports,
                        'timestamp': r.timestamp,
                        'scan_duration': r.scan_duration
                    } for r in results
                ]
            }
            
            # Mark as completed
            scan_result.mark_completed(results_data)
            scan.update_last_run()
            
            message = f'Scan completed successfully. Found {len(results)} hosts.'
            
        except Exception as scan_error:
            scan_result.mark_failed(str(scan_error))
            raise scan_error
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': message,
                'scan_result_id': scan_result.id,
                'redirect': url_for('dashboard.view_result', result_id=scan_result.id)
            })
        
        flash(message, 'success')
        return redirect(url_for('dashboard.view_result', result_id=scan_result.id))
        
    except Exception as e:
        error = f'Scan failed: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 500
        
        flash(error, 'error')
        return redirect(url_for('dashboard.view_scan', scan_id=scan_id))


@bp.route('/results/<int:result_id>')
@login_required
def view_result(result_id):
    """View detailed scan result"""
    result = ScanResult.query.join(Scan).filter(
        ScanResult.id == result_id,
        Scan.user_id == current_user.id
    ).first_or_404()
    
    # Parse results data for display
    detailed_results = []
    summary = {}
    
    if result.results_data and result.status == 'completed':
        results_data = result.results_data.get('results', [])
        summary = result.get_summary()
        
        for host_result in results_data:
            host_info = {
                'host': host_result.get('host'),
                'hostname': host_result.get('hostname'),
                'state': host_result.get('state'),
                'ports': host_result.get('ports', []),
                'open_ports': [p for p in host_result.get('ports', []) if p.get('state') == 'open'],
                'filtered_ports': [p for p in host_result.get('ports', []) if p.get('state') == 'filtered'],
                'closed_ports': [p for p in host_result.get('ports', []) if p.get('state') == 'closed']
            }
            detailed_results.append(host_info)
    
    return render_template('dashboard/view_result.html',
                         result=result,
                         detailed_results=detailed_results,
                         summary=summary)


@bp.route('/results/<int:result_id>/export')
@login_required
def export_result(result_id):
    """Export scan result as JSON"""
    result = ScanResult.query.join(Scan).filter(
        ScanResult.id == result_id,
        Scan.user_id == current_user.id
    ).first_or_404()
    
    if result.status != 'completed' or not result.results_data:
        flash('No data available for export', 'error')
        return redirect(url_for('dashboard.view_result', result_id=result_id))
    
    from flask import Response
    
    # Prepare export data
    export_data = {
        'scan_info': {
            'scan_name': result.scan.name,
            'target': result.scan.target,
            'ports': result.scan.ports,
            'scan_arguments': result.scan.scan_arguments,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat(),
            'duration_seconds': result.duration_seconds
        },
        'summary': result.get_summary(),
        'results': result.results_data.get('results', [])
    }
    
    filename = f"scan_result_{result.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return Response(
        json.dumps(export_data, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@bp.route('/results')
@login_required
def results():
    """View all scan results"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status_filter = request.args.get('status', '')
    
    # Build query
    query = ScanResult.query.join(Scan).filter(Scan.user_id == current_user.id)
    
    if status_filter:
        query = query.filter(ScanResult.status == status_filter)
    
    results_pagination = query.order_by(ScanResult.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get status counts for filter buttons
    status_counts = {
        'all': ScanResult.query.join(Scan).filter(Scan.user_id == current_user.id).count(),
        'completed': ScanResult.query.join(Scan).filter(
            Scan.user_id == current_user.id, ScanResult.status == 'completed'
        ).count(),
        'failed': ScanResult.query.join(Scan).filter(
            Scan.user_id == current_user.id, ScanResult.status == 'failed'
        ).count(),
        'running': ScanResult.query.join(Scan).filter(
            Scan.user_id == current_user.id, ScanResult.status == 'running'
        ).count()
    }
    
    return render_template('dashboard/results.html',
                         results=results_pagination.items,
                         pagination=results_pagination,
                         status_filter=status_filter,
                         status_counts=status_counts)