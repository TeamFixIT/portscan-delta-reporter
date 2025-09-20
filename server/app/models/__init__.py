"""
Database Models for Port Scanner Delta Reporter

This module defines the SQLAlchemy models for storing scan results,
client information, and delta reports.
"""

from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

# Import db from parent package - this will be set by the app factory
from .. import db


class User(UserMixin, db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Client(db.Model):
    """Scanning client devices (Raspberry Pi 4s)"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False)  # MAC address
    hostname = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='offline')  # online, offline, scanning
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    scan_results = db.relationship('ScanResult', backref='client', lazy=True)


class ScanResult(db.Model):
    """Individual scan results from clients"""
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.String(64), unique=True, nullable=False)
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'), nullable=False)
    target_host = db.Column(db.String(255), nullable=False)  # Target IP or hostname
    target_mac = db.Column(db.String(17))  # MAC address of target (if available)
    scan_type = db.Column(db.String(20), default='tcp')
    status = db.Column(db.String(20), nullable=False)  # completed, failed, in_progress
    scan_duration = db.Column(db.Float)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    open_ports = db.relationship('OpenPort', backref='scan_result', lazy=True, cascade='all, delete-orphan')


class OpenPort(db.Model):
    """Individual open ports found in scans"""
    id = db.Column(db.Integer, primary_key=True)
    scan_result_id = db.Column(db.Integer, db.ForeignKey('scan_result.id'), nullable=False)
    port_number = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.String(10), default='tcp')
    state = db.Column(db.String(20), nullable=False)  # open, closed, filtered
    service_name = db.Column(db.String(100))
    service_version = db.Column(db.String(255))
    service_product = db.Column(db.String(255))


class ScanTask(db.Model):
    """Scan tasks to be distributed to clients"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(64), unique=True, nullable=False)
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'), nullable=True)
    targets = db.Column(db.Text, nullable=False)  # JSON array of targets
    ports = db.Column(db.String(255), default='1-1000')
    scan_type = db.Column(db.String(20), default='tcp')
    priority = db.Column(db.Integer, default=5)  # 1=highest, 10=lowest
    status = db.Column(db.String(20), default='pending')  # pending, assigned, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)


class DeltaReport(db.Model):
    """Generated delta reports comparing scans"""
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(64), unique=True, nullable=False)
    baseline_scan_id = db.Column(db.String(64), nullable=False)
    current_scan_id = db.Column(db.String(64), nullable=False)
    target_mac = db.Column(db.String(17), nullable=False)  # MAC address for tracking
    report_type = db.Column(db.String(20), default='delta')  # delta, full, summary
    status = db.Column(db.String(20), default='generated')
    file_path = db.Column(db.String(500))  # Path to generated report file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Summary statistics
    new_ports_count = db.Column(db.Integer, default=0)
    closed_ports_count = db.Column(db.Integer, default=0)
    changed_services_count = db.Column(db.Integer, default=0)


# Export all models for easy importing
__all__ = ['User', 'Client', 'ScanResult', 'OpenPort', 'ScanTask', 'DeltaReport']