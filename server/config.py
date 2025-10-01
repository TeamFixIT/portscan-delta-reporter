import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration class"""

    # Flask Core Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Security Headers
    SECURITY_HEADERS = {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }

    # File Upload Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')

    # Scanner Settings
    SCANNER_OUTPUT_DIR = os.path.join(basedir, 'scan_results')
    SCANNER_LOG_LEVEL = 'INFO'
    MAX_CONCURRENT_SCANS = int(os.environ.get('MAX_CONCURRENT_SCANS', '3'))
    DEFAULT_SCAN_TIMEOUT = int(os.environ.get('DEFAULT_SCAN_TIMEOUT', '300'))  # 5 minutes

    # Background Task Settings
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'UTC'
    JOBS_DATABASE_URL = os.environ.get('JOBS_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'scheduler.db')

    # Redis Configuration (for production task queue)
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

    # Email Configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = '[Port Detector] '
    MAIL_SENDER = os.environ.get('MAIL_SENDER') or 'Port Detector <noreply@portdetector.com>'

    # Application Settings
    APP_NAME = 'Port Detector'
    APP_VERSION = '2.0.0'
    ITEMS_PER_PAGE = 20

    # Security Settings
    BCRYPT_LOG_ROUNDS = 12
    WTF_CSRF_TIME_LIMIT = 3600

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'

    @staticmethod
    def init_app(app):
        """Initialize configuration for the app"""
        # Create necessary directories
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['SCANNER_OUTPUT_DIR'], exist_ok=True)


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set to True to see SQL queries
    SCANNER_LOG_LEVEL = 'DEBUG'
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = False
    SCANNER_LOG_LEVEL = 'ERROR'
    MAX_CONCURRENT_SCANS = 1


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = True

    # Enhanced security for production
    SECURITY_HEADERS = Config.SECURITY_HEADERS.copy()
    SECURITY_HEADERS.update({
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    })

    # Production logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # Log to stderr in production
        import logging
        from logging import StreamHandler

        handler = StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment variable"""
    return config.get(os.environ.get('FLASK_ENV', 'development'), DevelopmentConfig)
