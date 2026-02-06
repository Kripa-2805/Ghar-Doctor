"""
GharDoc Medical System - Main Application
Rural Healthcare Monitoring Backend

Version: 1.0.0
Date: February 2026
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
    """Handle bad request errors"""
    return jsonify({
        'success': False,
        'error': 'Bad Request',
        'message': str(error),
        'timestamp': datetime.utcnow().isoformat()
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors"""
    return jsonify({
        'success': False,
        'error': 'Unauthorized',
        'message': 'Authentication required',
        'timestamp': datetime.utcnow().isoformat()
    }), 401

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'timestamp': datetime.utcnow().isoformat()
    }), 404

@app.errorhandler(429)
def ratelimit_handler(error):
    """Handle rate limit exceeded"""
    return jsonify({
        'success': False,
        'error': 'Rate Limit Exceeded',
        'message': 'Too many requests. Please try again later.',
        'timestamp': datetime.utcnow().isoformat()
    }), 429

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    db.session.rollback()
    app.logger.error(f'Server Error: {error}\n{traceback.format_exc()}')
    
    SystemLog.log(
        level='ERROR',
        source='ErrorHandler',
        message=str(error),
        metadata={'traceback': traceback.format_exc()}
    )
    
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred. Please try again later.',
        'timestamp': datetime.utcnow().isoformat()
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions"""
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
    """Get client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def create_response(success=True, data=None, message=None, status_code=200):
    """Create standardized API response"""
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
    """Home page"""
    return render_template('index.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/contact')
def contact():
    """Contact Us page"""
    return render_template('contact.html')

@app.route('/how-it-works')
def how_it_works():
    """How it works page"""
    return render_template('how_it_works.html')

@app.route('/guide')
def guide():
    """User guide page"""
    return render_template('guide.html')

@app.route('/login', methods=['GET', 'POST'])
@logout_required
def login():
    """Login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, result = AuthManager.login_user(email, password, get_request_ip())
        
        if success:
            AuthManager.create_session(result)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(result, 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
@logout_required
def signup():
    """Sign up page"""
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check password confirmation
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
    """Logout"""
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
    """User dashboard (after login)"""
    user = AuthManager.get_current_user()
    
    # Get health summary
    health_summary = DataProcessor.get_health_summary(user.id, days=7)
    
    # Get profile
    profile = ProfileManager.get_profile(user.id)
    
    # Calculate BMI if height and weight available
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
@login_required
def medical_history():
    """Medical history page"""
    user = AuthManager.get_current_user()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Get medical records
    pagination = MedicalData.query.filter_by(user_id=user.id).order_by(
        MedicalData.timestamp.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template(
        'medical_history.html',
        user=user,
        pagination=pagination,
        medical_records=pagination.items
    )

# ==================== API ENDPOINTS - AUTHENTICATION ====================

@app.route('/api/v1/auth/register', methods=['POST'])
@limiter.limit("10 per hour")
def api_register():
    """API endpoint for user registration"""
    try:
        data = request.get_json()
        
        if not data:
            return create_response(
                success=False,
                message='No data provided',
                status_code=400
            )
        
        success, result = AuthManager.register_user(
            full_name=data.get('full_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            password=data.get('password'),
            ip_address=get_request_ip()
        )
        
        if success:
            return create_response(
                success=True,
                data={'user_id': result.id, 'email': result.email},
                message='Registration successful',
                status_code=201
            )
        else:
            return create_response(
                success=False,
                message=result,
                status_code=400
            )
            
    except Exception as e:
        app.logger.error(f'Registration API error: {str(e)}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit("20 per hour")
def api_login():
    """API endpoint for user login"""
    try:
        data = request.get_json()
        
        if not data:
            return create_response(
                success=False,
                message='No data provided',
                status_code=400
            )
        
        success, result = AuthManager.login_user(
            email=data.get('email'),
            password=data.get('password'),
            ip_address=get_request_ip()
        )
        
        if success:
            return create_response(
                success=True,
                data=result.to_dict(),
                message='Login successful'
            )
        else:
            return create_response(
                success=False,
                message=result,
                status_code=401
            )
            
    except Exception as e:
        app.logger.error(f'Login API error: {str(e)}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

# ==================== API ENDPOINTS - MEDICAL DATA ====================

@app.route('/api/v1/medical-data', methods=['POST'])
@limiter.limit(app.config['ESP32_RATE_LIMIT'])
def receive_medical_data():
    """
    Receive medical data from ESP32 (single reading)
    
    Expected JSON:
    {
        "user_id": 123,
        "device_id": "ESP32_GHARDOC_001",
        "body_temperature": 98.6,
        "pulse_rate": 72,
        "heart_rate": 75,
        "spo2": 98,
        "battery_level": 85.5,
        "signal_strength": -65
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return create_response(
                success=False,
                message='No data provided',
                status_code=400
            )
        
        # Get user ID
        user_id = data.get('user_id')
        if not user_id:
            return create_response(
                success=False,
                message='user_id is required',
                status_code=400
            )
        
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return create_response(
                success=False,
                message='User not found',
                status_code=404
            )
        
        # Validate medical data
        is_valid, errors = MedicalDataValidator.validate_medical_reading(data, app.config)
        
        # Create medical data entry
        medical_reading = MedicalData(
            user_id=user_id,
            body_temperature=data.get('body_temperature'),
            pulse_rate=data.get('pulse_rate'),
            heart_rate=data.get('heart_rate'),
            spo2=data.get('spo2'),
            blood_pressure_systolic=data.get('blood_pressure_systolic'),
            blood_pressure_diastolic=data.get('blood_pressure_diastolic'),
            device_id=data.get('device_id'),
            battery_level=data.get('battery_level'),
            signal_strength=data.get('signal_strength'),
            is_valid=is_valid,
            is_offline_data=data.get('is_offline_data', False),
            validation_errors=json.dumps(errors) if not is_valid else None,
            notes=data.get('notes'),
            symptoms=data.get('symptoms')
        )
        
        # Handle recorded_at for offline data
        if data.get('recorded_at'):
            try:
                medical_reading.recorded_at = datetime.fromisoformat(
                    data['recorded_at'].replace('Z', '+00:00')
                )
            except:
                pass
        
        db.session.add(medical_reading)
        db.session.commit()
        
        # Check for health alerts
        alerts_created = []
        if is_valid:
            alerts_created = HealthAlertManager.check_and_create_alerts(
                medical_reading, app.config
            )
        
        app.logger.info(
            f'Medical data received from user {user_id}: '
            f'Temp={data.get("body_temperature")}°F, '
            f'Pulse={data.get("pulse_rate")} bpm'
        )
        
        return create_response(
            success=True,
            data={
                'id': medical_reading.id,
                'user_id': user_id,
                'is_valid': is_valid,
                'alerts_triggered': len(alerts_created),
                'validation_errors': errors if not is_valid else None
            },
            message='Medical data received successfully',
            status_code=201
        )
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error receiving medical data: {str(e)}\n{traceback.format_exc()}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

@app.route('/api/v1/medical-data/batch', methods=['POST'])
@limiter.limit("100 per hour")
def receive_medical_data_batch():
    """
    Receive batch of medical readings (for offline data upload)
    
    Expected JSON:
    {
        "user_id": 123,
        "device_id": "ESP32_GHARDOC_001",
        "readings": [
            {
                "body_temperature": 98.6,
                "pulse_rate": 72,
                "heart_rate": 75,
                "recorded_at": "2026-02-03T10:30:00Z"
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'readings' not in data:
            return create_response(
                success=False,
                message='No readings provided',
                status_code=400
            )
        
        user_id = data.get('user_id')
        if not user_id:
            return create_response(
                success=False,
                message='user_id is required',
                status_code=400
            )
        
        # Verify user
        user = User.query.get(user_id)
        if not user:
            return create_response(
                success=False,
                message='User not found',
                status_code=404
            )
        
        readings = data.get('readings', [])
        
        # Limit batch size
        if len(readings) > app.config['MAX_BATCH_SIZE']:
            return create_response(
                success=False,
                message=f'Batch size exceeds maximum of {app.config["MAX_BATCH_SIZE"]}',
                status_code=400
            )
        
        saved_count = 0
        alert_count = 0
        device_id = data.get('device_id')
        
        for reading_data in readings:
            try:
                # Merge with common data
                reading_data['user_id'] = user_id
                reading_data['device_id'] = device_id
                reading_data['is_offline_data'] = True
                
                # Validate
                is_valid, errors = MedicalDataValidator.validate_medical_reading(
                    reading_data, app.config
                )
                
                # Create entry
                medical_reading = MedicalData(
                    user_id=user_id,
                    body_temperature=reading_data.get('body_temperature'),
                    pulse_rate=reading_data.get('pulse_rate'),
                    heart_rate=reading_data.get('heart_rate'),
                    spo2=reading_data.get('spo2'),
                    device_id=device_id,
                    battery_level=reading_data.get('battery_level'),
                    signal_strength=reading_data.get('signal_strength'),
                    is_valid=is_valid,
                    is_offline_data=True,
                    validation_errors=json.dumps(errors) if not is_valid else None
                )
                
                # Handle recorded_at
                if reading_data.get('recorded_at'):
                    try:
                        medical_reading.recorded_at = datetime.fromisoformat(
                            reading_data['recorded_at'].replace('Z', '+00:00')
                        )
                    except:
                        pass
                
                db.session.add(medical_reading)
                db.session.flush()
                
                # Check alerts
                if is_valid:
                    alerts = HealthAlertManager.check_and_create_alerts(
                        medical_reading, app.config
                    )
                    alert_count += len(alerts)
                
                saved_count += 1
                
            except Exception as e:
                app.logger.warning(f'Error processing reading in batch: {str(e)}')
                continue
        
        db.session.commit()
        
        app.logger.info(
            f'Batch upload from user {user_id}: '
            f'{saved_count}/{len(readings)} readings saved, '
            f'{alert_count} alerts triggered'
        )
        
        return create_response(
            success=True,
            data={
                'user_id': user_id,
                'total_readings': len(readings),
                'saved_readings': saved_count,
                'alerts_triggered': alert_count
            },
            message=f'Batch upload successful: {saved_count} readings saved',
            status_code=201
        )
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Batch upload error: {str(e)}\n{traceback.format_exc()}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

@app.route('/api/v1/medical-data/latest', methods=['GET'])
@limiter.limit("200 per minute")
def get_latest_medical_data():
    """Get latest medical reading for current user"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            # Try to get user_id from query params (for API access)
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_response(
                    success=False,
                    message='user_id required or login required',
                    status_code=401
                )
        else:
            user_id = session['user_id']
        
        latest = MedicalData.get_latest_by_user(user_id)
        
        if not latest:
            return create_response(
                success=False,
                message='No medical data found',
                status_code=404
            )
        
        return create_response(
            success=True,
            data=latest.to_dict(include_user=True)
        )
        
    except Exception as e:
        app.logger.error(f'Error getting latest data: {str(e)}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

@app.route('/api/v1/medical-data/statistics', methods=['GET'])
@limiter.limit("100 per minute")
def get_medical_statistics():
    """Get medical data statistics"""
    try:
        if 'user_id' not in session:
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_response(
                    success=False,
                    message='user_id required or login required',
                    status_code=401
                )
        else:
            user_id = session['user_id']
        
        days = request.args.get('days', 7, type=int)
        days = min(days, 90)  # Maximum 90 days
        
        stats = MedicalData.get_statistics(user_id, days)
        
        return create_response(success=True, data=stats)
        
    except Exception as e:
        app.logger.error(f'Error getting statistics: {str(e)}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

@app.route('/api/v1/medical-data/history', methods=['GET'])
@limiter.limit("100 per minute")
def get_medical_history():
    """Get medical history with pagination"""
    try:
        if 'user_id' not in session:
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_response(
                    success=False,
                    message='user_id required or login required',
                    status_code=401
                )
        else:
            user_id = session['user_id']
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        
        pagination = MedicalData.query.filter_by(user_id=user_id).order_by(
            MedicalData.timestamp.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return create_response(
            success=True,
            data={
                'readings': [reading.to_dict() for reading in pagination.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_pages': pagination.pages,
                    'total_items': pagination.total,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        )
        
    except Exception as e:
        app.logger.error(f'Error getting history: {str(e)}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

@app.route('/api/v1/medical-data/export', methods=['GET'])
@limiter.limit("10 per hour")
def export_medical_data():
    """Export medical data as CSV"""
    try:
        if 'user_id' not in session:
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_response(
                    success=False,
                    message='user_id required or login required',
                    status_code=401
                )
        else:
            user_id = session['user_id']
        
        limit = min(request.args.get('limit', 1000, type=int), 10000)
        
        readings = MedicalData.query.filter_by(user_id=user_id).order_by(
            MedicalData.timestamp.desc()
        ).limit(limit).all()
        
        if not readings:
            return create_response(
                success=False,
                message='No data to export',
                status_code=404
            )
        
        csv_data = DataExporter.to_csv(readings)
        
        filename = f'ghardoc_medical_data_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        
        from io import BytesIO
        output = BytesIO()
        output.write(csv_data.encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f'Error exporting data: {str(e)}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

# ==================== API ENDPOINTS - ALERTS ====================

@app.route('/api/v1/alerts', methods=['GET'])
@limiter.limit("100 per minute")
def get_alerts():
    """Get alerts for user"""
    try:
        if 'user_id' not in session:
            user_id = request.args.get('user_id', type=int)
            if not user_id:
                return create_response(
                    success=False,
                    message='user_id required or login required',
                    status_code=401
                )
        else:
            user_id = session['user_id']
        
        acknowledged = request.args.get('acknowledged')
        limit = min(request.args.get('limit', 50, type=int), 200)
        
        query = Alert.query.filter_by(user_id=user_id)
        
        if acknowledged is not None:
            ack_bool = acknowledged.lower() == 'true'
            query = query.filter_by(acknowledged=ack_bool)
        
        alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
        
        return create_response(
            success=True,
            data={
                'alerts': [alert.to_dict() for alert in alerts],
                'total': len(alerts)
            }
        )
        
    except Exception as e:
        app.logger.error(f'Error getting alerts: {str(e)}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

@app.route('/api/v1/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@limiter.limit("100 per minute")
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        alert = Alert.query.get(alert_id)
        
        if not alert:
            return create_response(
                success=False,
                message='Alert not found',
                status_code=404
            )
        
        # Verify user owns this alert
        if 'user_id' in session and alert.user_id != session['user_id']:
            return create_response(
                success=False,
                message='Unauthorized',
                status_code=403
            )
        
        alert.acknowledge()
        
        return create_response(
            success=True,
            data=alert.to_dict(),
            message='Alert acknowledged'
        )
        
    except Exception as e:
        app.logger.error(f'Error acknowledging alert: {str(e)}')
        return create_response(
            success=False,
            message=f'Error: {str(e)}',
            status_code=500
        )

# ==================== API ENDPOINTS - USER PROFILE ====================

@app.route('/api/v1/profile', methods=['GET', 'PUT'])
@login_required
def manage_profile():
    """Get or update user profile"""
    user_id = session['user_id']
    
    if request.method == 'GET':
        try:
            user = User.query.get(user_id)
            profile = ProfileManager.get_profile(user_id)
            
            return create_response(
                success=True,
                data={
                    'user': user.to_dict(include_profile=True),
                    'profile': profile.to_dict() if profile else None
                }
            )
            
        except Exception as e:
            app.logger.error(f'Error getting profile: {str(e)}')
            return create_response(
                success=False,
                message=f'Error: {str(e)}',
                status_code=500
            )
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            success, message = ProfileManager.update_profile(user_id, data)
            
            if success:
                return create_response(
                    success=True,
                    message=message
                )
            else:
                return create_response(
                    success=False,
                    message=message,
                    status_code=400
                )
                
        except Exception as e:
            app.logger.error(f'Error updating profile: {str(e)}')
            return create_response(
                success=False,
                message=f'Error: {str(e)}',
                status_code=500
            )

# ==================== API ENDPOINTS - SYSTEM ====================

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """System health check"""
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
        return create_response(
            success=False,
            data={'status': 'unhealthy', 'error': str(e)},
            status_code=500
        )

# ==================== MAIN ====================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )