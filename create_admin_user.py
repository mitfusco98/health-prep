
"""
Script to create an admin user in the database using environment variables.
"""
import os
from app import app, db
from models import User
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user():
    """Create an admin user using environment variables"""
    try:
        with app.app_context():
            # Get admin credentials from environment variables
            admin_username = os.environ.get('ADMIN_USERNAME')
            admin_password = os.environ.get('ADMIN_PASSWORD')
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@healthprep.com')
            
            # Validate required environment variables
            if not admin_username:
                logger.error("ADMIN_USERNAME environment variable is required")
                print("Error: ADMIN_USERNAME environment variable is required")
                print("Please set it in your environment or .env file")
                return False
                
            if not admin_password:
                logger.error("ADMIN_PASSWORD environment variable is required")
                print("Error: ADMIN_PASSWORD environment variable is required")
                print("Please set it in your environment or .env file")
                return False
            
            # Validate password strength
            if len(admin_password) < 8:
                logger.error("Admin password must be at least 8 characters long")
                print("Error: Admin password must be at least 8 characters long")
                return False
            
            # Check if admin user already exists
            existing_admin = User.query.filter_by(username=admin_username).first()
            if existing_admin:
                logger.info(f"Admin user '{admin_username}' already exists")
                print(f"Admin user '{admin_username}' already exists")
                
                # Update password if it's different
                if not existing_admin.check_password(admin_password):
                    existing_admin.set_password(admin_password)
                    existing_admin.email = admin_email
                    db.session.commit()
                    logger.info(f"Admin user '{admin_username}' password updated")
                    print(f"Admin user '{admin_username}' password updated")
                
                return True
            
            # Create admin user
            admin_user = User(
                username=admin_username,
                email=admin_email,
                is_admin=True
            )
            admin_user.set_password(admin_password)
            
            db.session.add(admin_user)
            db.session.commit()
            
            logger.info(f"Admin user '{admin_username}' created successfully")
            print(f"Admin user '{admin_username}' created successfully")
            print(f"Username: {admin_username}")
            print(f"Email: {admin_email}")
            print("Admin privileges: Yes")
            print("Password: [Hidden for security]")
            
            return True
            
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        print(f"Error creating admin user: {str(e)}")
        db.session.rollback()
        return False

def validate_environment_variables():
    """Validate that all required environment variables are set"""
    required_vars = ['ADMIN_USERNAME', 'ADMIN_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your environment or create a .env file")
        return False
    
    return True

if __name__ == "__main__":
    if validate_environment_variables():
        success = create_admin_user()
        if not success:
            exit(1)
    else:
        exit(1)
