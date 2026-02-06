"""
GharDoc Medical System - Configuration
Rural Healthcare Monitoring System
"""

import os
from datetime import timedelta


class Config:
    """Base configuration"""
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ghardoc-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # Database Settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///gharDoc.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Session Settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)  # Stay logged in for 30 days
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # API Settings
    API_VERSION = 'v1'
    API_TITLE = 'GharDoc Medical API'
    API_DESCRIPTION = 'Healthcare monitoring system for rural areas'
    
    # Pagination
    ITEMS_PER_PAGE = 50
    MAX_ITEMS_PER_PAGE = 500
    
    # CORS Settings
    CORS_ORIGINS = ['*']  # In production, specify actual domain
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    ESP32_RATE_LIMIT = "2000 per hour"  # High limit for batch uploads
    API_RATE_LIMIT = "200 per hour"
    
    # Medical Data Validation Thresholds
    BODY_TEMP_MIN = 95.0  # °F
    BODY_TEMP_MAX = 107.0  # °F
    PULSE_MIN = 40  # bpm
    PULSE_MAX = 200  # bpm
    HEART_RATE_MIN = 40  # bpm
    HEART_RATE_MAX = 200  # bpm
    SPO2_MIN = 70  # %
    SPO2_MAX = 100  # %
    
    # Alert Thresholds (for notifications)
    TEMP_ALERT_HIGH = 100.4  # Fever threshold (°F)
    TEMP_ALERT_LOW = 96.0  # Hypothermia threshold
    PULSE_ALERT_HIGH = 120  # Tachycardia
    PULSE_ALERT_LOW = 50  # Bradycardia
    HEART_RATE_ALERT_HIGH = 120
    HEART_RATE_ALERT_LOW = 50
    SPO2_ALERT_LOW = 90  # Low oxygen
    
    # ESP32 Settings
    MAX_BATCH_SIZE = 100  # Maximum readings in one batch upload
    OFFLINE_BUFFER_SIZE = 200  # ESP32 can store 200 readings
    
    # Logging
    LOG_FILE = 'logs/app.log'
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_LEVEL = 'INFO'
    
    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'csv', 'json', 'txt', 'pdf'}
    
    # Timezone
    TIMEZONE = 'Asia/Kolkata'  # Indian Standard Time
    
    # Password Hashing
    BCRYPT_LOG_ROUNDS = 12


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    LOG_LEVEL = 'WARNING'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_gharDoc.db'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}