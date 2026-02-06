"""
GharDoc Database Models
Medical data storage and user management
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import json

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(db.Model):
    """User accounts for GharDoc system"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Personal Information
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    
    # Account Status
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    medical_data = db.relationship('MedicalData', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Verify password"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_profile=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_profile and self.profile:
            data['profile'] = self.profile.to_dict()
        
        return data


class UserProfile(db.Model):
    """Extended user profile information"""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Demographic Information
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))  # Male, Female, Other
    blood_group = db.Column(db.String(5))  # A+, B+, O+, AB+, etc.
    height = db.Column(db.Float)  # in cm
    weight = db.Column(db.Float)  # in kg
    
    # Location
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    pincode = db.Column(db.String(10))
    
    # Medical Information
    emergency_contact = db.Column(db.String(15))
    emergency_contact_name = db.Column(db.String(100))
    known_allergies = db.Column(db.Text)  # JSON or comma-separated
    chronic_conditions = db.Column(db.Text)  # JSON or comma-separated
    current_medications = db.Column(db.Text)  # JSON or comma-separated
    
    # Device Information
    device_id = db.Column(db.String(50))  # ESP32 device ID
    device_registered_at = db.Column(db.DateTime)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserProfile {self.user_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'age': self.age,
            'gender': self.gender,
            'blood_group': self.blood_group,
            'height': self.height,
            'weight': self.weight,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'emergency_contact': self.emergency_contact,
            'emergency_contact_name': self.emergency_contact_name,
            'known_allergies': self.known_allergies,
            'chronic_conditions': self.chronic_conditions,
            'current_medications': self.current_medications,
            'device_id': self.device_id
        }


class MedicalData(db.Model):
    """Medical readings from GharDoc device"""
    __tablename__ = 'medical_data'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Vital Signs
    body_temperature = db.Column(db.Float, nullable=False)  # °F
    pulse_rate = db.Column(db.Integer, nullable=False)  # bpm
    heart_rate = db.Column(db.Integer, nullable=False)  # bpm
    spo2 = db.Column(db.Float)  # Oxygen saturation %
    blood_pressure_systolic = db.Column(db.Integer)  # mmHg
    blood_pressure_diastolic = db.Column(db.Integer)  # mmHg
    
    # Metadata
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    recorded_at = db.Column(db.DateTime)  # When ESP32 actually recorded (for offline data)
    
    # Device Information
    device_id = db.Column(db.String(50))
    battery_level = db.Column(db.Float)  # %
    signal_strength = db.Column(db.Integer)  # RSSI
    
    # Data Quality
    is_valid = db.Column(db.Boolean, default=True)
    is_offline_data = db.Column(db.Boolean, default=False)  # Uploaded after being offline
    validation_errors = db.Column(db.Text)  # JSON of validation errors
    
    # Additional Notes
    notes = db.Column(db.Text)  # User notes
    symptoms = db.Column(db.Text)  # Reported symptoms
    
    def __repr__(self):
        return f'<MedicalData {self.id} - User {self.user_id}>'
    
    def to_dict(self, include_user=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'body_temperature': round(self.body_temperature, 1) if self.body_temperature else None,
            'pulse_rate': self.pulse_rate,
            'heart_rate': self.heart_rate,
            'spo2': round(self.spo2, 1) if self.spo2 else None,
            'blood_pressure': f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}" 
                if self.blood_pressure_systolic else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'device_id': self.device_id,
            'battery_level': round(self.battery_level, 1) if self.battery_level else None,
            'signal_strength': self.signal_strength,
            'is_valid': self.is_valid,
            'is_offline_data': self.is_offline_data,
            'notes': self.notes,
            'symptoms': self.symptoms
        }
        
        if include_user and self.user:
            data['user_name'] = self.user.full_name
        
        return data
    
    @staticmethod
    def get_latest_by_user(user_id):
        """Get latest reading for a user"""
        return MedicalData.query.filter_by(user_id=user_id).order_by(
            MedicalData.timestamp.desc()
        ).first()
    
    @staticmethod
    def get_statistics(user_id, days=7):
        """Get statistics for a user over N days"""
        time_threshold = datetime.utcnow() - timedelta(days=days)
        
        query = MedicalData.query.filter(
            MedicalData.user_id == user_id,
            MedicalData.timestamp >= time_threshold,
            MedicalData.is_valid == True
        )
        
        stats = query.with_entities(
            func.avg(MedicalData.body_temperature).label('avg_temp'),
            func.min(MedicalData.body_temperature).label('min_temp'),
            func.max(MedicalData.body_temperature).label('max_temp'),
            func.avg(MedicalData.pulse_rate).label('avg_pulse'),
            func.min(MedicalData.pulse_rate).label('min_pulse'),
            func.max(MedicalData.pulse_rate).label('max_pulse'),
            func.avg(MedicalData.heart_rate).label('avg_hr'),
            func.avg(MedicalData.spo2).label('avg_spo2'),
            func.count(MedicalData.id).label('total_readings')
        ).first()
        
        return {
            'body_temperature': {
                'average': round(stats.avg_temp, 1) if stats.avg_temp else None,
                'min': round(stats.min_temp, 1) if stats.min_temp else None,
                'max': round(stats.max_temp, 1) if stats.max_temp else None
            },
            'pulse_rate': {
                'average': round(stats.avg_pulse, 1) if stats.avg_pulse else None,
                'min': stats.min_pulse,
                'max': stats.max_pulse
            },
            'heart_rate': {
                'average': round(stats.avg_hr, 1) if stats.avg_hr else None
            },
            'spo2': {
                'average': round(stats.avg_spo2, 1) if stats.avg_spo2 else None
            },
            'total_readings': stats.total_readings,
            'period_days': days
        }


class Alert(db.Model):
    """Health alerts based on vital signs"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    medical_data_id = db.Column(db.Integer, db.ForeignKey('medical_data.id'))
    
    alert_type = db.Column(db.String(50), nullable=False)  # 'temp_high', 'pulse_low', etc.
    severity = db.Column(db.String(20), default='warning')  # 'info', 'warning', 'critical'
    message = db.Column(db.String(500), nullable=False)
    
    value = db.Column(db.Float)  # The value that triggered alert
    threshold = db.Column(db.Float)  # The threshold crossed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Alert {self.id} - {self.alert_type}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'value': round(self.value, 1) if self.value else None,
            'threshold': round(self.threshold, 1) if self.threshold else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged': self.acknowledged,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }
    
    def acknowledge(self):
        """Mark alert as acknowledged"""
        self.acknowledged = True
        self.acknowledged_at = datetime.utcnow()
        db.session.commit()


class SystemLog(db.Model):
    """System activity logging"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    log_level = db.Column(db.String(20), nullable=False)
    source = db.Column(db.String(100))
    message = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    metadata = db.Column(db.Text)  # JSON
    
    @staticmethod
    def log(level, source, message, user_id=None, ip_address=None, metadata=None):
        """Helper to create log entries"""
        log_entry = SystemLog(
            log_level=level,
            source=source,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            metadata=json.dumps(metadata) if metadata else None
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry