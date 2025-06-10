#!/usr/bin/env python3
"""
Script to secure the default admin account by updating the password.
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import secrets
import string


def generate_secure_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = "".join(secrets.choice(alphabet) for i in range(length))
    return password


def secure_admin_account():
    """Update the admin account with a secure password"""
    with app.app_context():
        # Find the admin user
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            print("Error: Admin user not found.")
            return False

        # Generate a new secure password
        new_password = generate_secure_password(16)

        # Update password
        admin_user.password_hash = generate_password_hash(new_password)

        # Update email to something more secure
        admin_user.email = "admin@healthcare-system.local"

        try:
            db.session.commit()
            print("Admin account secured successfully!")
            print(f"New admin credentials:")
            print(f"Username: admin")
            print(f"Password: {new_password}")
            print(f"Email: {admin_user.email}")
            print("\nPlease save these credentials securely and use them to log in.")
            print("The default password 'password' is no longer valid.")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error securing admin account: {e}")
            return False


if __name__ == "__main__":
    print("Securing admin account...")
    secure_admin_account()
