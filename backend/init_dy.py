# init_db.py
from app import app, db
from models import User

print("🔄 Initializing GharDoc Database...")

with app.app_context():
    # Drop all tables (ONLY for fresh start)
    db.drop_all()
    print("⚠️  Dropped existing tables")
    
    # Create all tables
    db.create_all()
    print("✅ Database tables created:")
    print("   - users")
    print("   - user_profiles")
    print("   - medical_data")
    print("   - alerts")
    print("   - system_logs")
    
    # Create test user
    test_user = User(
        full_name="Test User",
        email="test@ghardoctor.com",
        phone="9876543210"
    )
    test_user.set_password("test123")
    
    db.session.add(test_user)
    db.session.commit()
    
    print("\n✅ Test user created:")
    print(f"   Email: test@ghardoctor.com")
    print(f"   Password: test123")
    print(f"   User ID: {test_user.id}")

print("\n🚀 Database ready! You can now run: python app.py")