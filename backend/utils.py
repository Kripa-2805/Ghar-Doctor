"""
GharDoc Utility Functions
Validation, alerts, and helper functions
"""

from models import db, Alert, SystemLog, MedicalData
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MedicalDataValidator:
    """Validate medical readings"""
    
    @staticmethod
    def validate_temperature(temp, min_val=30.0, max_val=45.0):
        """Validate body temperature (°C)"""
        if temp is None:
            return False, "Temperature value is missing"
        
        try:
            temp = float(temp)
            if temp < min_val or temp > max_val:
                return False, f"Temperature {temp}°F out of valid range ({min_val}-{max_val})"
            return True, None
        except (ValueError, TypeError):
            return False, "Invalid temperature format"
    
    @staticmethod
    def validate_pulse(pulse, min_val=40, max_val=200):
        """Validate pulse rate (bpm)"""
        if pulse is None:
            return False, "Pulse rate is missing"
        
        try:
            pulse = int(pulse)
            if pulse < min_val or pulse > max_val:
                return False, f"Pulse {pulse} bpm out of valid range ({min_val}-{max_val})"
            return True, None
        except (ValueError, TypeError):
            return False, "Invalid pulse format"
    
    @staticmethod
    def validate_heart_rate(hr, min_val=40, max_val=200):
        """Validate heart rate (bpm)"""
        if hr is None:
            return False, "Heart rate is missing"
        
        try:
            hr = int(hr)
            if hr < min_val or hr > max_val:
                return False, f"Heart rate {hr} bpm out of valid range ({min_val}-{max_val})"
            return True, None
        except (ValueError, TypeError):
            return False, "Invalid heart rate format"
    
    @staticmethod
    def validate_spo2(spo2, min_val=70, max_val=100):
        """Validate SpO2 (%)"""
        if spo2 is None:
            return True, None  # SpO2 is optional
        
        try:
            spo2 = float(spo2)
            if spo2 < min_val or spo2 > max_val:
                return False, f"SpO2 {spo2}% out of valid range ({min_val}-{max_val})"
            return True, None
        except (ValueError, TypeError):
            return False, "Invalid SpO2 format"
    
    @staticmethod
    def validate_medical_reading(data, config):
        """
        Validate complete medical reading
        Returns: (is_valid, errors_dict)
        """
        errors = {}
        
        # Validate temperature
        if 'body_temperature' in data:
            valid, error = MedicalDataValidator.validate_temperature(
                data['body_temperature'],
                config.BODY_TEMP_MIN,
                config.BODY_TEMP_MAX
            )
            if not valid:
                errors['body_temperature'] = error
        else:
            errors['body_temperature'] = "Temperature is required"
        
        # Validate pulse
        if 'pulse_rate' in data:
            valid, error = MedicalDataValidator.validate_pulse(
                data['pulse_rate'],
                config.PULSE_MIN,
                config.PULSE_MAX
            )
            if not valid:
                errors['pulse_rate'] = error
        else:
            errors['pulse_rate'] = "Pulse rate is required"
        
        # Validate heart rate
        if 'heart_rate' in data:
            valid, error = MedicalDataValidator.validate_heart_rate(
                data['heart_rate'],
                config.HEART_RATE_MIN,
                config.HEART_RATE_MAX
            )
            if not valid:
                errors['heart_rate'] = error
        else:
            errors['heart_rate'] = "Heart rate is required"
        
        # Validate SpO2 (optional)
        if 'spo2' in data:
            valid, error = MedicalDataValidator.validate_spo2(
                data['spo2'],
                config.SPO2_MIN,
                config.SPO2_MAX
            )
            if not valid:
                errors['spo2'] = error
        
        # Validate battery level (optional)
        if 'battery_level' in data and data['battery_level'] is not None:
            try:
                battery = float(data['battery_level'])
                if battery < 0 or battery > 100:
                    errors['battery_level'] = "Battery level must be 0-100%"
            except (ValueError, TypeError):
                errors['battery_level'] = "Invalid battery level format"
        
        return len(errors) == 0, errors


class HealthAlertManager:
    """Manage health alerts based on vital signs"""
    
    @staticmethod
    def check_and_create_alerts(medical_data, config):
        """
        Check medical reading against thresholds and create alerts
        Returns: list of created alerts
        """
        alerts_created = []
        user_id = medical_data.user_id
        
        # Check body temperature
        if medical_data.body_temperature:
            if medical_data.body_temperature >= config.TEMP_ALERT_HIGH:
                alert = Alert(
                    user_id=user_id,
                    medical_data_id=medical_data.id,
                    alert_type='temperature_high',
                    severity='warning' if medical_data.body_temperature < 102 else 'critical',
                    message=f'High body temperature detected: {medical_data.body_temperature}°C (Fever)',
                    value=medical_data.body_temperature,
                    threshold=config.TEMP_ALERT_HIGH
                )
                db.session.add(alert)
                alerts_created.append(alert)
                logger.warning(f"High temperature alert for user {user_id}: {medical_data.body_temperature}°C")
            
            elif medical_data.body_temperature <= config.TEMP_ALERT_LOW:
                alert = Alert(
                    user_id=user_id,
                    medical_data_id=medical_data.id,
                    alert_type='temperature_low',
                    severity='warning',
                    message=f'Low body temperature detected: {medical_data.body_temperature}°C',
                    value=medical_data.body_temperature,
                    threshold=config.TEMP_ALERT_LOW
                )
                db.session.add(alert)
                alerts_created.append(alert)
                logger.warning(f"Low temperature alert for user {user_id}: {medical_data.body_temperature}°C")
        
        # Check pulse rate
        if medical_data.pulse_rate:
            if medical_data.pulse_rate >= config.PULSE_ALERT_HIGH:
                alert = Alert(
                    user_id=user_id,
                    medical_data_id=medical_data.id,
                    alert_type='pulse_high',
                    severity='warning',
                    message=f'High pulse rate detected: {medical_data.pulse_rate} bpm (Tachycardia)',
                    value=medical_data.pulse_rate,
                    threshold=config.PULSE_ALERT_HIGH
                )
                db.session.add(alert)
                alerts_created.append(alert)
                logger.warning(f"High pulse alert for user {user_id}: {medical_data.pulse_rate} bpm")
            
            elif medical_data.pulse_rate <= config.PULSE_ALERT_LOW:
                alert = Alert(
                    user_id=user_id,
                    medical_data_id=medical_data.id,
                    alert_type='pulse_low',
                    severity='warning',
                    message=f'Low pulse rate detected: {medical_data.pulse_rate} bpm (Bradycardia)',
                    value=medical_data.pulse_rate,
                    threshold=config.PULSE_ALERT_LOW
                )
                db.session.add(alert)
                alerts_created.append(alert)
                logger.warning(f"Low pulse alert for user {user_id}: {medical_data.pulse_rate} bpm")
        
        # Check heart rate
        if medical_data.heart_rate:
            if medical_data.heart_rate >= config.HEART_RATE_ALERT_HIGH:
                alert = Alert(
                    user_id=user_id,
                    medical_data_id=medical_data.id,
                    alert_type='heart_rate_high',
                    severity='warning',
                    message=f'High heart rate detected: {medical_data.heart_rate} bpm',
                    value=medical_data.heart_rate,
                    threshold=config.HEART_RATE_ALERT_HIGH
                )
                db.session.add(alert)
                alerts_created.append(alert)
        
        # Check SpO2 (oxygen saturation)
        if medical_data.spo2 and medical_data.spo2 < config.SPO2_ALERT_LOW:
            alert = Alert(
                user_id=user_id,
                medical_data_id=medical_data.id,
                alert_type='spo2_low',
                severity='critical',
                message=f'Low oxygen saturation: {medical_data.spo2}% (Hypoxia)',
                value=medical_data.spo2,
                threshold=config.SPO2_ALERT_LOW
            )
            db.session.add(alert)
            alerts_created.append(alert)
            logger.critical(f"Low SpO2 alert for user {user_id}: {medical_data.spo2}%")
        
        # Check battery level
        if medical_data.battery_level and medical_data.battery_level < 15:
            alert = Alert(
                user_id=user_id,
                medical_data_id=medical_data.id,
                alert_type='battery_low',
                severity='info',
                message=f'GharDoc device battery low: {medical_data.battery_level}%',
                value=medical_data.battery_level,
                threshold=15.0
            )
            db.session.add(alert)
            alerts_created.append(alert)
        
        if alerts_created:
            db.session.commit()
        
        return alerts_created


class DataProcessor:
    """Process and analyze medical data"""
    
    @staticmethod
    def calculate_bmi(weight_kg, height_cm):
        """Calculate BMI"""
        if not weight_kg or not height_cm:
            return None
        
        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)
        return round(bmi, 1)
    
    @staticmethod
    def get_bmi_category(bmi):
        """Get BMI category"""
        if bmi is None:
            return "Unknown"
        
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"
    
    @staticmethod
    def get_health_summary(user_id, days=7):
        """Get comprehensive health summary for a user"""
        # Get statistics
        stats = MedicalData.get_statistics(user_id, days)
        
        # Get latest reading
        latest = MedicalData.get_latest_by_user(user_id)
        
        # Get active alerts
        active_alerts = Alert.query.filter_by(
            user_id=user_id,
            acknowledged=False
        ).order_by(Alert.created_at.desc()).limit(10).all()
        
        # Check for concerning trends
        concerns = []
        if stats['body_temperature']['average'] and stats['body_temperature']['average'] > 99:
            concerns.append("Elevated average temperature")
        if stats['pulse_rate']['average'] and stats['pulse_rate']['average'] > 100:
            concerns.append("Elevated average pulse rate")
        
        return {
            'statistics': stats,
            'latest_reading': latest.to_dict() if latest else None,
            'active_alerts': [alert.to_dict() for alert in active_alerts],
            'concerns': concerns,
            'period_days': days
        }


class DataExporter:
    """Export medical data in various formats"""
    
    @staticmethod
    def to_csv(medical_data_list):
        """Convert medical data to CSV format"""
        if not medical_data_list:
            return ""
        
        # CSV header
        csv_lines = [
            "ID,User ID,Date,Time,Body Temperature (°C),Pulse Rate (bpm),Heart Rate (bpm),SpO2 (%),Blood Pressure,Battery (%),Valid"
        ]
        
        # Data rows
        for data in medical_data_list:
            timestamp = data.timestamp or data.recorded_at
            date_str = timestamp.strftime("%Y-%m-%d") if timestamp else ""
            time_str = timestamp.strftime("%H:%M:%S") if timestamp else ""
            
            bp = f"{data.blood_pressure_systolic}/{data.blood_pressure_diastolic}" \
                if data.blood_pressure_systolic else ""
            
            row = [
                str(data.id),
                str(data.user_id),
                date_str,
                time_str,
                str(data.body_temperature) if data.body_temperature else "",
                str(data.pulse_rate) if data.pulse_rate else "",
                str(data.heart_rate) if data.heart_rate else "",
                str(data.spo2) if data.spo2 else "",
                bp,
                str(data.battery_level) if data.battery_level else "",
                "Yes" if data.is_valid else "No"
            ]
            csv_lines.append(",".join(row))
        
        return "\n".join(csv_lines)


def clean_old_data(days=90):
    """Clean up old data (keep last 90 days)"""
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Delete old medical data
    deleted_medical = MedicalData.query.filter(
        MedicalData.timestamp < cutoff_date
    ).delete()
    
    # Delete old logs
    deleted_logs = SystemLog.query.filter(
        SystemLog.timestamp < cutoff_date
    ).delete()
    
    db.session.commit()
    
    logger.info(f"Cleaned up {deleted_medical} old readings and {deleted_logs} old logs")
    
    return {
        'medical_data_deleted': deleted_medical,
        'logs_deleted': deleted_logs
    }