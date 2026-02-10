"""
GharDoc Medical System - Main Application
Rural Healthcare Monitoring Backend
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime, timedelta
import traceback
import json

# Import local modules
from config import config
from models import db, bcrypt, User, UserProfile, MedicalData, Alert, SystemLog
from utils import (
    MedicalDataValidator, HealthAlertManager, DataProcessor,
    DataExporter, clean_old_data
)
from auth import AuthManager, ProfileManager, login_required, logout_required

# Initialize Flask app
app = Flask(__name__)

# Load configuration
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=app.config['RATELIMIT_STORAGE_URL']
)

# ==================== LOGGING SETUP ====================

def setup_logging():
    """Configure application logging"""
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    
    app.logger.info('GharDoc Backend startup')

setup_logging()

# ==================== DATABASE INITIALIZATION ====================

def init_database():
    """Initialize database and create tables"""
    with app.app_context():
        db.create_all()
        app.logger.info('Database tables created successfully')

init_database()

# ==================== ERROR HANDLERS ====================

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad Request',
        'message': str(error),
        'timestamp': datetime.utcnow().isoformat()
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        'success': False,
        'error': 'Unauthorized',
        'message': 'Authentication required',
        'timestamp': datetime.utcnow().isoformat()
    }), 401

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'timestamp': datetime.utcnow().isoformat()
    }), 404

@app.errorhandler(429)
def ratelimit_handler(error):
    return jsonify({
        'success': False,
        'error': 'Rate Limit Exceeded',
        'message': 'Too many requests. Please try again later.',
        'timestamp': datetime.utcnow().isoformat()
    }), 429

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'Server Error: {error}\n{traceback.format_exc()}')
    
    SystemLog.log(
        level='ERROR',
        source='ErrorHandler',
        message=str(error),
        log_metadata={'traceback': traceback.format_exc()}
    )
    
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred. Please try again later.',
        'timestamp': datetime.utcnow().isoformat()
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    if isinstance(error, HTTPException):
        return error
    
    db.session.rollback()
    app.logger.error(f'Unhandled Exception: {error}\n{traceback.format_exc()}')
    
    return jsonify({
        'success': False,
        'error': 'Unexpected Error',
        'message': str(error),
        'timestamp': datetime.utcnow().isoformat()
    }), 500

# ==================== HELPER FUNCTIONS ====================

def get_request_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def create_response(success=True, data=None, message=None, status_code=200):
    response = {
        'success': success,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    return jsonify(response), status_code

# ==================== WEB ROUTES (HTML PAGES) ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how-it-works.html')

@app.route('/user-guide')
def user_guide():
    return render_template('user-guide.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/login', methods=['GET', 'POST'])
@logout_required
def login():
    return redirect(url_for('signup'))

@app.route('/signup', methods=['GET', 'POST'])
@logout_required
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('signup'))
        
        success, result = AuthManager.register_user(
            full_name, email, phone, password, get_request_ip()
        )
        
        if success:
            AuthManager.create_session(result)
            flash('Registration successful! Welcome to GharDoc!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(result, 'danger')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    user_email = session.get('user_email', 'unknown')
    AuthManager.destroy_session()
    
    SystemLog.log(
        level='INFO',
        source='Logout',
        message=f'User logged out: {user_email}',
        ip_address=get_request_ip()
    )
    
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = AuthManager.get_current_user()
    health_summary = DataProcessor.get_health_summary(user.id, days=7)
    profile = ProfileManager.get_profile(user.id)
    
    bmi = None
    bmi_category = None
    if profile and profile.weight and profile.height:
        bmi = DataProcessor.calculate_bmi(profile.weight, profile.height)
        bmi_category = DataProcessor.get_bmi_category(bmi)
    
    return render_template(
        'dashboard.html',
        user=user,
        profile=profile,
        health_summary=health_summary,
        bmi=bmi,
        bmi_category=bmi_category
    )

@app.route('/medical-history')
def medical_history():
    if 'user_id' not in session:
        flash('Please login to view medical history', 'warning')
        return redirect(url_for('signup'))
    
    user = AuthManager.get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    pagination = MedicalData.query.filter_by(user_id=user.id).order_by(
        MedicalData.timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template(
        'medical_history.html',
        user=user,
        pagination=pagination,
        medical_records=pagination.items
    )

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('signup'))
    
    flash('Settings page coming soon!', 'info')
    return redirect(url_for('dashboard'))

# ==================== API ENDPOINTS - MEDICAL DATA ====================
@app.route('/api/v1/medical-data', methods=['POST'])
@limiter.limit(app.config['ESP32_RATE_LIMIT'])
def receive_medical_data():
    try:
        data = request.get_json()
        
        if not data:
            return create_response(success=False, message='No data provided', status_code=400)
        
        user_id = data.get('user_id')
        if not user_id:
            return create_response(success=False, message='user_id is required', status_code=400)
        
        user = User.query.get(user_id)
        if not user:
            return create_response(success=False, message='User not found', status_code=404)
        
        # Handle NULL values for heart_rate/pulse_rate/spo2
        temp = data.get('body_temperature')
        hr = data.get('heart_rate')
        pulse = data.get('pulse_rate')
        spo2 = data.get('spo2')
        
        # If no finger detected, set defaults
        if hr is None and pulse is None:
            hr = 0
            pulse = 0
        
        # Validate only if we have actual readings
        is_valid = True
        errors = {}
        
        if hr and hr > 0:  # Only validate if finger was detected
            is_valid, errors = MedicalDataValidator.validate_medical_reading(data, app.config)
        
        medical_reading = MedicalData(
            user_id=user_id,
            body_temperature=temp if temp else 36.5,
            pulse_rate=pulse if pulse else 0,
            heart_rate=hr if hr else 0,
            spo2=spo2 if spo2 else 0,
            blood_pressure_systolic=data.get('blood_pressure_systolic'),
            blood_pressure_diastolic=data.get('blood_pressure_diastolic'),
            device_id=data.get('device_id'),
            battery_level=data.get('battery_level'),
            signal_strength=data.get('signal_strength'),
            is_valid=is_valid,
            is_offline_data=data.get('is_offline_data', False),
            validation_errors=json.dumps(errors) if errors else None,
            notes=data.get('notes'),
            symptoms=data.get('symptoms')
        )
        
        if data.get('recorded_at'):
            try:
                medical_reading.recorded_at = datetime.fromisoformat(
                    data['recorded_at'].replace('Z', '+00:00')
                )
            except:
                pass
        
        db.session.add(medical_reading)
        db.session.commit()
        
        # Create alerts only if valid reading with finger
        alerts_created = []
        if is_valid and hr and hr > 0:
            alerts_created = HealthAlertManager.check_and_create_alerts(medical_reading, app.config)
        
        finger_detected = hr is not None and hr > 0
        app.logger.info(f'Medical data received from user {user_id} - Finger: {finger_detected}')
        
        return create_response(
            success=True,
            data={
                'id': medical_reading.id,
                'user_id': user_id,
                'is_valid': is_valid,
                'finger_detected': finger_detected,
                'alerts_triggered': len(alerts_created),
                'validation_errors': errors if errors else None
            },
            message='Medical data received successfully',
            status_code=201
        )
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error receiving medical data: {str(e)}')
        return create_response(success=False, message=f'Error: {str(e)}', status_code=500)

@app.route('/api/v1/medical-data/latest', methods=['GET'])
@limiter.limit("200 per minute")
def get_latest_medical_data():
    try:
        if 'user_id' not in session:
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_response(success=False, message='user_id required', status_code=401)
        else:
            user_id = session['user_id']
        
        latest = MedicalData.get_latest_by_user(user_id)
        
        if not latest:
            return create_response(success=False, message='No medical data found', status_code=404)
        
        return create_response(success=True, data=latest.to_dict(include_user=True))
        
    except Exception as e:
        app.logger.error(f'Error getting latest data: {str(e)}')
        return create_response(success=False, message=f'Error: {str(e)}', status_code=500)

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    try:
        db.session.execute('SELECT 1')
        
        total_users = User.query.count()
        total_readings = MedicalData.query.count()
        active_alerts = Alert.query.filter_by(acknowledged=False).count()
        
        return create_response(
            success=True,
            data={
                'status': 'healthy',
                'database': 'connected',
                'total_users': total_users,
                'total_readings': total_readings,
                'active_alerts': active_alerts,
                'version': '1.0.0'
            }
        )
        
    except Exception as e:
        return create_response(success=False, data={'status': 'unhealthy', 'error': str(e)}, status_code=500)
# ==================== MAIN ====================


@app.route('/api/v1/medical-data/batch', methods=['POST'])
@limiter.limit(app.config['ESP32_RATE_LIMIT'])
def upload_batch_medical_data():
    try:
        data = request.get_json()
        readings = data.get('readings', [])
        
        if not readings:
            return create_response(success=False, message='No readings', status_code=400)
        
        uploaded = 0
        for reading in readings[:100]:
            user_id = reading.get('user_id')
            if not user_id:
                continue
                
            is_valid, errors = MedicalDataValidator.validate_medical_reading(reading, app.config)
            
            medical_entry = MedicalData(
                user_id=user_id,
                body_temperature=reading.get('body_temperature'),
                pulse_rate=reading.get('pulse_rate', 0),
                heart_rate=reading.get('heart_rate', 0),
                spo2=reading.get('spo2'),
                device_id=reading.get('device_id'),
                battery_level=reading.get('battery_level'),
                is_valid=is_valid,
                is_offline_data=True,
                validation_errors=json.dumps(errors) if errors else None
            )
            
            db.session.add(medical_entry)
            uploaded += 1
        
        db.session.commit()
        return create_response(success=True, data={'uploaded': uploaded}, status_code=200)
        
    except Exception as e:
        db.session.rollback()
        return create_response(success=False, message=str(e), status_code=500)

# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])