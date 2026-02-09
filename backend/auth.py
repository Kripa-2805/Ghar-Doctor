"""
GharDoc Authentication Module
User registration, login, and session management
"""

from flask import session, redirect, url_for, flash
from functools import wraps
from models import db, User, UserProfile, SystemLog
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def logout_required(f):
    """Decorator to redirect logged-in users away from login/signup"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


class AuthManager:
    """Handle user authentication"""
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email:
            return False, "Email is required"
        
        # Basic email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"
        
        # Check if email already exists
        existing = User.query.filter_by(email=email.lower()).first()
        if existing:
            return False, "Email already registered"
        
        return True, None
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone number (Indian format)"""
        if not phone:
            return False, "Phone number is required"
        
        # Remove spaces and hyphens
        phone = phone.replace(" ", "").replace("-", "")
        
        # Check Indian phone number format (10 digits)
        if not phone.isdigit() or len(phone) != 10:
            return False, "Phone number must be 10 digits"
        
        # Check if phone already exists
        existing = User.query.filter_by(phone=phone).first()
        if existing:
            return False, "Phone number already registered"
        
        return True, None
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password:
            return False, "Password is required"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        # Optional: Add more password rules
        # if not any(c.isupper() for c in password):
        #     return False, "Password must contain at least one uppercase letter"
        
        return True, None
    
    @staticmethod
    def validate_full_name(name):
        """Validate full name"""
        if not name:
            return False, "Full name is required"
        
        if len(name) < 3:
            return False, "Name must be at least 3 characters"
        
        if not all(c.isalpha() or c.isspace() for c in name):
            return False, "Name can only contain letters and spaces"
        
        return True, None
    
    @staticmethod
    def register_user(full_name, email, phone, password, ip_address=None):
        """
        Register a new user
        Returns: (success, user_or_error_message)
        """
        try:
            # Validate inputs
            valid, error = AuthManager.validate_full_name(full_name)
            if not valid:
                return False, error
            
            valid, error = AuthManager.validate_email(email)
            if not valid:
                return False, error
            
            valid, error = AuthManager.validate_phone(phone)
            if not valid:
                return False, error
            
            valid, error = AuthManager.validate_password(password)
            if not valid:
                return False, error
            
            # Create user
            user = User(
                full_name=full_name.strip(),
                email=email.lower().strip(),
                phone=phone.strip()
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Create empty profile
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            
            db.session.commit()
            
            # Log registration
            SystemLog.log(
                level='INFO',
                source='AuthManager',
                message=f'New user registered: {email}',
                user_id=user.id,
                ip_address=ip_address
            )
            
            logger.info(f"New user registered: {email}")
            
            return True, user
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            return False, "Registration failed. Please try again."
    
    @staticmethod
    def login_user(email, password, ip_address=None):
        """
        Authenticate user
        Returns: (success, user_or_error_message)
        """
        try:
            if not email or not password:
                return False, "Email and password are required"
            
            # Find user
            user = User.query.filter_by(email=email.lower().strip()).first()
            
            if not user:
                return False, "Invalid email or password"
            
            # Check password
            if not user.check_password(password):
                return False, "Invalid email or password"
            
            # Check if account is active
            if not user.is_active:
                return False, "Account is deactivated. Please contact support."
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log login
            SystemLog.log(
                level='INFO',
                source='AuthManager',
                message=f'User logged in: {email}',
                user_id=user.id,
                ip_address=ip_address
            )
            
            logger.info(f"User logged in: {email}")
            
            return True, user
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False, "Login failed. Please try again."
    
    @staticmethod
    def create_session(user):
        """Create user session"""
        session.permanent = True
        session['user_id'] = user.id
        session['user_name'] = user.full_name
        session['user_email'] = user.email
    
    @staticmethod
    def destroy_session():
        """Destroy user session (logout)"""
        session.clear()
    
    @staticmethod
    def get_current_user():
        """Get currently logged-in user"""
        user_id = session.get('user_id')
        if not user_id:
            return None
        
        return User.query.get(user_id)
    
    @staticmethod
    def is_logged_in():
        """Check if user is logged in"""
        return 'user_id' in session


class ProfileManager:
    """Manage user profiles"""
    
    @staticmethod
    def update_profile(user_id, profile_data):
        """Update user profile"""
        try:
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            
            if not profile:
                profile = UserProfile(user_id=user_id)
                db.session.add(profile)
            
            # Update fields if provided
            if 'age' in profile_data:
                profile.age = profile_data['age']
            if 'gender' in profile_data:
                profile.gender = profile_data['gender']
            if 'blood_group' in profile_data:
                profile.blood_group = profile_data['blood_group']
            if 'height' in profile_data:
                profile.height = profile_data['height']
            if 'weight' in profile_data:
                profile.weight = profile_data['weight']
            if 'address' in profile_data:
                profile.address = profile_data['address']
            if 'city' in profile_data:
                profile.city = profile_data['city']
            if 'state' in profile_data:
                profile.state = profile_data['state']
            if 'pincode' in profile_data:
                profile.pincode = profile_data['pincode']
            if 'emergency_contact' in profile_data:
                profile.emergency_contact = profile_data['emergency_contact']
            if 'emergency_contact_name' in profile_data:
                profile.emergency_contact_name = profile_data['emergency_contact_name']
            if 'known_allergies' in profile_data:
                profile.known_allergies = profile_data['known_allergies']
            if 'chronic_conditions' in profile_data:
                profile.chronic_conditions = profile_data['chronic_conditions']
            if 'current_medications' in profile_data:
                profile.current_medications = profile_data['current_medications']
            if 'device_id' in profile_data:
                profile.device_id = profile_data['device_id']
                profile.device_registered_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Profile updated for user {user_id}")
            
            return True, "Profile updated successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Profile update error: {str(e)}")
            return False, "Failed to update profile"
    
    @staticmethod
    def get_profile(user_id):
        """Get user profile"""
        return UserProfile.query.filter_by(user_id=user_id).first()