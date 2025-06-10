#!/usr/bin/env python3
"""
Script to change the default admin password for security.
Run this script to update the admin user's password to something secure.
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import getpass
import sys


def change_admin_password():
    """Change the admin user's password"""
    with app.app_context():
        # Find the admin user
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            print("Error: Admin user not found.")
            return False

        print("Current admin user found:")
        print(f"Username: {admin_user.username}")
        print(f"Email: {admin_user.email}")
        print()

        # Get new password
        while True:
            new_password = getpass.getpass("Enter new admin password: ")
            if len(new_password) < 8:
                print("Password must be at least 8 characters long.")
                continue

            confirm_password = getpass.getpass("Confirm new password: ")
            if new_password != confirm_password:
                print("Passwords do not match. Please try again.")
                continue
            break

        # Update password
        admin_user.password_hash = generate_password_hash(new_password)

        # Optionally update email
        update_email = (
            input("\nWould you like to update the admin email address? (y/n): ")
            .lower()
            .strip()
        )
        if update_email == "y":
            new_email = input("Enter new admin email: ").strip()
            if new_email:
                admin_user.email = new_email
                print(f"Email updated to: {new_email}")

        try:
            db.session.commit()
            print("\n✓ Admin password updated successfully!")
            print("The default credentials are no longer valid.")
            print("Please use the new password to log in.")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"\nError updating password: {e}")
            return False


if __name__ == "__main__":
    print("=== Admin Password Change Tool ===")
    print("This will change the default admin password for security.")
    print()

    proceed = input("Do you want to proceed? (y/n): ").lower().strip()
    if proceed != "y":
        print("Operation cancelled.")
        sys.exit(0)

    success = change_admin_password()
    if success:
        print("\nPassword change completed successfully.")
    else:
        print("\nPassword change failed.")
        sys.exit(1)
