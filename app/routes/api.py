from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.scan import Scan
from app.models.scan_result import ScanResult
from src.scanner import NetworkScanner
from datetime import datetime, timedelta
import json

bp = Blueprint('api', __name__)


def api_response(success=True, data=None, message=None, error=None, status_code=200):
    """Standardized API response format"""
    response_data = {
        'success': success,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response_data['data'] = data
    if message:
        response_data['message'] = message
    if error:
        response_data['error'] = error
        
    return jsonify(response_data), status_code


@bp.errorhandler(400)
def bad_request(error):
    return api_response(success=False, error='Bad request', status_code=400)


@bp.errorhandler(404)
def not_found(error):
    return api_response(success=False, error='Resource not found', status_code=404)


@bp.errorhandler(500)
def internal_error(error):
    return api_response(success=False, error='Internal server error', status_code=500)


# Dashboard API endpoints
@bp.route('/dashboard/stats')
@login_required
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Basic stats
        total_scans = current_user.scans.count()
        active_scans = current_user.scans.filter_by(is_active=True).count()
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_results = ScanResult.query.join(Scan).filter(
            Scan.user_id == current_user.id,
            ScanResult.created_at >= thirty_days_ago
        ).all()
        
        total_recent_results = len(recent_results)
        successful_results = len([r for r in recent_results if r.status == 'completed'])
        failed_results = len([r for r in recent_results if r.status == 'failed'])
        
        # Calculate success rate
        success_rate = (successful_results / total_recent_results * 100) if total_recent_results > 0 else 0
        
        # Scan activity over time (last 7 days)
        activity_data = []
        for i in range(7):
            date = datetime.utcnow().date() - timedelta(days=i)
            day_results = [r for r in recent_results if r.created_at.date() == date]
            activity_data.append({
                'date': date.isoformat(),
                'scans': len(day_results),
                'successful': len([r for r in day_results if r.status == 'completed']),
                'failed': len([r for r in day_results if r.status == 'failed'])
            })
        
        activity_data.reverse()  # Show chronologically
        
        # Top services discovered
        service_counts = {}
        for result in recent_results:
            if result.status == 'completed' and result.results_data:
                for host_result in result.results_data.get('results', []):
                    for port in host_result.get('ports', []):
                        if port.get('state') == 'open':
                            service = port.get('service', 'unknown')
                            service_counts[service] = service_counts.get(service, 0) + 1
        
        top_services = sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        stats = {
            'total_scans': total_scans,
            'active_scans': active_scans,
            'total_results': total_recent_results,
            'successful_results': successful_results,
            'failed_results': failed_results,
            'success_rate': round(success_rate, 1),
            'activity_data': activity_data,
            'top_services': [{'service': s[0], 'count': s[1]} for s in top_services]
        }
        
        return api_response(data=stats)
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# Scan management API endpoints
@bp.route('/scans')
@login_required
def get_scans():
    """Get user's scans with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', '')
        
        # Limit per_page to prevent abuse
        per_page = min(per_page, 100)
        
        query = current_user.scans.order_by(Scan.updated_at.desc())
        
        if status_filter == 'active':
            query = query.filter_by(is_active=True)
        elif status_filter == 'inactive':
            query = query.filter_by(is_active=False)
        elif status_filter == 'scheduled':
            query = query.filter_by(is_scheduled=True)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        scans_data = [scan.to_dict() for scan in pagination.items]
        
        return api_response(data={
            'scans': scans_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


@bp.route('/scans/<int:scan_id>')
@login_required
def get_scan(scan_id):
    """Get specific scan details"""
    try:
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        if not scan:
            return api_response(success=False, error='Scan not found', status_code=404)
        
        return api_response(data=scan.to_dict())
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


@bp.route('/scans/<int:scan_id>/results')
@login_required
def get_scan_results(scan_id):
    """Get scan results for a specific scan"""
    try:
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        if not scan:
            return api_response(success=False, error='Scan not found', status_code=404)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', '')
        
        per_page = min(per_page, 100)
        
        query = scan.results.order_by(ScanResult.created_at.desc())
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        results_data = [result.to_dict() for result in pagination.items]
        
        return api_response(data={
            'scan': scan.to_dict(),
            'results': results_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


@bp.route('/scans/<int:scan_id>/toggle', methods=['POST'])
@login_required
def toggle_scan_status(scan_id):
    """Toggle scan active/inactive status"""
    try:
        scan = Scan.query.filter_by(id=scan_id, user_id=current_user.id).first()
        if not scan:
            return api_response(success=False, error='Scan not found', status_code=404)
        
        scan.is_active = not scan.is_active
        scan.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'activated' if scan.is_active else 'deactivated'
        return api_response(
            data=scan.to_dict(),
            message=f'Scan {status} successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(success=False, error=str(e), status_code=500)


# Scanner validation API endpoints
@bp.route('/validate/target', methods=['POST'])
@login_required
def validate_target():
    """Validate target IP or subnet"""
    try:
        data = request.get_json()
        if not data or 'target' not in data:
            return api_response(success=False, error='Target is required', status_code=400)
        
        target = data['target'].strip()
        scanner = NetworkScanner()
        is_valid = scanner.validate_target(target)
        
        return api_response(data={
            'target': target,
            'is_valid': is_valid,
            'message': 'Valid target format' if is_valid else 'Invalid target format'
        })
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


@bp.route('/validate/ports', methods=['POST'])
@login_required
def validate_ports():
    """Validate port specification"""
    try:
        data = request.get_json()
        if not data or 'ports' not in data:
            return api_response(success=False, error='Ports specification is required', status_code=400)
        
        ports = data['ports'].strip()
        scanner = NetworkScanner()
        is_valid = scanner.validate_ports(ports)
        
        return api_response(data={
            'ports': ports,
            'is_valid': is_valid,
            'message': 'Valid ports format' if is_valid else 'Invalid ports format'
        })
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# System information API endpoints
@bp.route('/system/info')
@login_required
def system_info():
    """Get system information"""
    try:
        scanner = NetworkScanner()
        sys_info = scanner.get_system_info()
        
        return api_response(data={
            'timestamp': sys_info.timestamp,
            'hostname': sys_info.hostname,
            'local_ip': sys_info.local_ip,
            'interfaces': sys_info.interfaces,
            'cpu_cores': sys_info.cpu_cores,
            'cpu_usage': sys_info.cpu_usage,
            'memory_usage': sys_info.memory_usage
        })
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# Real-time scan status API
@bp.route('/scans/running')
@login_required
def get_running_scans():
    """Get currently running scans"""
    try:
        running_results = ScanResult.query.join(Scan).filter(
            Scan.user_id == current_user.id,
            ScanResult.status == 'running'
        ).all()
        
        running_data = []
        for result in running_results:
            elapsed_time = (datetime.utcnow() - result.start_time).total_seconds()
            running_data.append({
                'result_id': result.id,
                'scan_id': result.scan_id,
                'scan_name': result.scan.name,
                'target': result.scan.target,
                'ports': result.scan.ports,
                'start_time': result.start_time.isoformat(),
                'elapsed_seconds': round(elapsed_time, 1)
            })
        
        return api_response(data={'running_scans': running_data})
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# Scan result details API
@bp.route('/results/<int:result_id>')
@login_required
def get_result_details(result_id):
    """Get detailed scan result"""
    try:
        result = ScanResult.query.join(Scan).filter(
            ScanResult.id == result_id,
            Scan.user_id == current_user.id
        ).first()
        
        if not result:
            return api_response(success=False, error='Result not found', status_code=404)
        
        result_data = result.to_dict()
        
        # Add detailed results if available
        if result.status == 'completed' and result.results_data:
            result_data['detailed_results'] = result.results_data.get('results', [])
        
        return api_response(data=result_data)
        
    except Exception as e:
        return api_response(success=False, error=str(e), status_code=500)


# Bulk operations API
@bp.route('/scans/bulk/toggle', methods=['POST'])
@login_required
def bulk_toggle_scans():
    """Toggle multiple scans active/inactive status"""
    try:
        data = request.get_json()
        if not data or 'scan_ids' not in data:
            return api_response(success=False, error='Scan IDs are required', status_code=400)
        
        scan_ids = data['scan_ids']
        action = data.get('action', 'toggle')  # 'activate', 'deactivate', or 'toggle'
        
        if not isinstance(scan_ids, list) or not scan_ids:
            return api_response(success=False, error='Valid scan IDs list required', status_code=400)
        
        scans = Scan.query.filter(
            Scan.id.in_(scan_ids),
            Scan.user_id == current_user.id
        ).all()
        
        if len(scans) != len(scan_ids):
            return api_response(success=False, error='Some scans not found', status_code=404)
        
        updated_scans = []
        for scan in scans:
            if action == 'activate':
                scan.is_active = True
            elif action == 'deactivate':
                scan.is_active = False
            else:  # toggle
                scan.is_active = not scan.is_active
            
            scan.updated_at = datetime.utcnow()
            updated_scans.append(scan.to_dict())
        
        db.session.commit()
        
        return api_response(
            data={'updated_scans': updated_scans},
            message=f'Successfully updated {len(updated_scans)} scans'
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(success=False, error=str(e), status_code=500)