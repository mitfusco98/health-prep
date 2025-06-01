"""
Environment Variable Validation Utility
Ensures all required secrets are properly configured
"""
import os
import sys
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class EnvironmentValidator:
    """Validates environment variables for security and completeness"""

    # Required environment variables
    REQUIRED_VARS = {
        'JWT_SECRET_KEY': {
            'min_length': 32,
            'description': 'JWT signing secret key'
        },
        'SESSION_SECRET': {
            'min_length': 16,
            'description': 'Flask session secret key'
        },
        'ADMIN_USERNAME': {
            'min_length': 3,
            'description': 'Admin username for initial user creation'
        },
        'ADMIN_PASSWORD': {
            'min_length': 8,
            'description': 'Admin password for initial user creation'
        }
    }

    # Optional but recommended variables
    OPTIONAL_VARS = {
        'DATABASE_URL': 'Database connection string',
        'ADMIN_EMAIL': 'Admin email address',
        'FLASK_ENV': 'Flask environment setting'
    }

    # Insecure default values that should not be used
    INSECURE_DEFAULTS = [
        'dev_secret_key',
        'your-secret-key-change-in-production',
        'change-me',
        'default',
        'admin',
        'password',
        '123456'
    ]

    @classmethod
    def validate_all(cls, strict: bool = True) -> bool:
        """
        Validate all environment variables

        Args:
            strict: If True, missing required variables cause failure

        Returns:
            bool: True if validation passes
        """
        success = True
        issues = []

        # Check required variables
        for var_name, config in cls.REQUIRED_VARS.items():
            value = os.environ.get(var_name)

            if not value:
                issues.append(f"MISSING: {var_name} - {config['description']}")
                success = False
                continue

            # Check minimum length
            if len(value) < config['min_length']:
                issues.append(f"TOO_SHORT: {var_name} must be at least {config['min_length']} characters")
                success = False

            # Check for insecure defaults
            if value.lower() in [default.lower() for default in cls.INSECURE_DEFAULTS]:
                issues.append(f"INSECURE: {var_name} is using a default/insecure value")
                success = False

        # Check optional variables
        for var_name, description in cls.OPTIONAL_VARS.items():
            value = os.environ.get(var_name)
            if not value:
                issues.append(f"OPTIONAL: {var_name} - {description} (not set)")

        # Report issues
        if issues:
            logger.warning("Environment variable validation issues found:")
            for issue in issues:
                logger.warning(f"  - {issue}")

            if not success and strict:
                logger.error("Validation failed due to missing or insecure required variables")
                print("\nEnvironment Variable Validation Failed!")
                print("=" * 50)
                for issue in issues:
                    if any(prefix in issue for prefix in ['MISSING:', 'TOO_SHORT:', 'INSECURE:']):
                        print(f"❌ {issue}")
                    else:
                        print(f"⚠️  {issue}")
                print("\nPlease fix these issues before starting the application.")
                print("Create a .env file or set environment variables directly.")
                return False

        if success:
            logger.info("All required environment variables are properly configured")

        return success

    @classmethod
    def generate_secure_keys(cls) -> Dict[str, str]:
        """Generate secure random keys for configuration"""
        import secrets
        import string

        def generate_key(length: int = 32) -> str:
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for _ in range(length))

        return {
            'JWT_SECRET_KEY': generate_key(64),
            'SESSION_SECRET': generate_key(32),
        }

    @classmethod
    def create_env_template(cls, filename: str = '.env.template') -> None:
        """Create a template .env file with secure examples"""
        secure_keys = cls.generate_secure_keys()

        template_content = f"""# Healthcare Prep Application Environment Variables
# Copy this file to .env and update the values

# REQUIRED: Security Keys (generate new values for each environment)
JWT_SECRET_KEY={secure_keys['JWT_SECRET_KEY']}
SESSION_SECRET={secure_keys['SESSION_SECRET']}

# REQUIRED: Admin User Configuration (set these in Replit Secrets)
# ADMIN_USERNAME=your_admin_username
# ADMIN_PASSWORD=your_secure_password
# ADMIN_EMAIL=your_email@example.com

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost/healthcare_db

# Optional: Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=true

# Add additional API keys and secrets here as needed
"""

        with open(filename, 'w') as f:
            f.write(template_content)

        print(f"Environment template created: {filename}")
        print("Copy this file to .env and update the values before starting the application.")

def validate_startup_environment():
    """Validate environment on application startup"""
    return EnvironmentValidator.validate_all(strict=True)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Environment Variable Validator')
    parser.add_argument('--generate-template', action='store_true', 
                       help='Generate a .env template file')
    parser.add_argument('--validate', action='store_true', 
                       help='Validate current environment')

    args = parser.parse_args()

    if args.generate_template:
        EnvironmentValidator.create_env_template()
    elif args.validate:
        success = EnvironmentValidator.validate_all()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

def validate_admin_credentials():
    """Validate admin credentials for security"""
    issues = []

    username = os.getenv('ADMIN_USERNAME')
    password = os.getenv('ADMIN_PASSWORD')

    # Check for insecure default usernames
    insecure_usernames = ['admin', 'administrator', 'root', 'user', 'test']
    if username and username.lower() in insecure_usernames:
        issues.append(f"CRITICAL: ADMIN_USERNAME '{username}' is a common default - MUST use a unique username")
        # This is a critical security issue - we should exit
        logger.critical(f"Insecure default username detected: {username}")

    # Check for insecure default passwords
    insecure_passwords = ['password', 'admin', '123456', 'password123', 'admin123', 'test', 'letmein', 'qwerty']
    if password and password.lower() in insecure_passwords:
        issues.append(f"CRITICAL: ADMIN_PASSWORD is a common default - MUST use a strong, unique password")
        # This is a critical security issue - we should exit
        logger.critical(f"Insecure default password detected")

    # Check password strength
    if password:
        if len(password) < 8:
            issues.append("SECURITY: ADMIN_PASSWORD should be at least 8 characters long")

        # Check for basic complexity
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            issues.append("SECURITY: ADMIN_PASSWORD should contain uppercase, lowercase, and numbers")

    return issues

def validate_environment():
    """Validate all environment variables and security settings"""
    logger.info("Starting environment validation...")

    issues = []
    critical_issues = []

    # Validate required variables
    required_issues = validate_required_variables()
    issues.extend(required_issues)

    # Validate optional variables
    optional_issues = validate_optional_variables()
    issues.extend(optional_issues)

    # Validate admin credentials
    admin_issues = validate_admin_credentials()
    issues.extend(admin_issues)

    # Check for critical security issues
    for issue in admin_issues:
        if issue.startswith("CRITICAL:"):
            critical_issues.append(issue)

    # Validate security settings
    security_issues = validate_security_settings()
    issues.extend(security_issues)

    # Report results
    if critical_issues:
        logger.critical("CRITICAL security issues found - application cannot start safely:")
        for issue in critical_issues:
            logger.critical(f"  - {issue}")
        # Exit the application for critical security issues
        raise SystemExit("Critical security issues detected. Please fix environment variables and restart.")

    if issues:
        logger.warning("Environment variable validation issues found:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("All environment variables are properly configured")

    return issues