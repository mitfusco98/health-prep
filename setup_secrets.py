
#!/usr/bin/env python3
"""
Setup script for configuring application secrets
Run this script to generate secure configuration
"""
import os
import sys
from env_validator import EnvironmentValidator

def main():
    print("Healthcare Prep Application - Secret Setup")
    print("=" * 50)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        print("Warning: .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return
    
    # Generate template
    EnvironmentValidator.create_env_template('.env')
    
    print("\n✅ Environment file created!")
    print("\nNext steps:")
    print("1. Set ADMIN_USERNAME, ADMIN_PASSWORD, and ADMIN_EMAIL in Replit Secrets")
    print("2. Set JWT_SECRET_KEY and SESSION_SECRET in Replit Secrets")
    print("3. Set DATABASE_URL if using PostgreSQL")
    print("4. Run 'python create_admin_user.py' to create the admin user")
    print("5. Start the application")
    
    print("\n⚠️  Important Security Notes:")
    print("- Use Replit Secrets for all sensitive configuration")
    print("- Never commit sensitive values to version control")
    print("- Use strong, unique passwords")
    print("- The generated JWT and session keys are cryptographically secure")

if __name__ == "__main__":
    main()
