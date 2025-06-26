"""
Unified Configuration Management System
Consolidates all environment variables, constants, and settings
"""

import os
import secrets
import logging
from datetime import timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environments"""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class DatabaseConfig:
    """Database configuration"""

    url: str
    track_modifications: bool = False
    pool_recycle: int = 300
    pool_pre_ping: bool = True
    pool_timeout: int = 10
    pool_size: int = 20
    max_overflow: int = 30
    connect_timeout: int = 10

    @property
    def engine_options(self) -> Dict[str, Any]:
        return {
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": False,  # Disable pre-ping for faster startup
            "pool_timeout": 1,  # Minimal timeout for immediate startup
            "pool_size": 1,  # Single connection for fastest startup
            "max_overflow": 1,  # Minimal overflow for fastest startup
            "connect_args": {
                "connect_timeout": 1,  # Ultra-fast timeout for immediate failure
                "application_name": "healthprep_app",
                "sslmode": "require",  # Enable SSL as required by Neon/PostgreSQL
            },
        }


@dataclass
class SecurityConfig:
    """Security configuration"""

    jwt_secret_key: str
    session_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    csrf_enabled: bool = True
    csrf_time_limit: int = 3600
    session_lifetime_hours: int = 24
    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "Lax"

    @property
    def jwt_expiration_delta(self) -> timedelta:
        return timedelta(hours=self.jwt_expiration_hours)

    @property
    def session_lifetime_delta(self) -> timedelta:
        return timedelta(hours=self.session_lifetime_hours)


@dataclass
class AdminConfig:
    """Admin user configuration"""

    username: str
    password: str
    email: str


@dataclass
class LoggingConfig:
    """Logging configuration"""

    level: str = "WARNING"
    structured_logging: bool = True
    log_directory: str = "/tmp/healthprep_logs"
    max_file_size_mb: int = 50
    backup_count: int = 10

    @property
    def log_level(self) -> int:
        return getattr(logging, self.level.upper(), logging.WARNING)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""

    default_per_day: int = 200
    default_per_hour: int = 50
    session_requests_per_minute: int = 20
    repository_requests_per_minute: int = 100
    automated_attack_threshold: int = 30


@dataclass
class FileUploadConfig:
    """File upload configuration"""

    max_content_length_mb: int = 1
    allowed_extensions: List[str] = None
    upload_folder: str = "/tmp/uploads"

    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = [
                ".pdf",
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".txt",
                ".csv",
                ".xlsx",
                ".xls",
                ".doc",
                ".docx",
            ]

    @property
    def max_content_length(self) -> int:
        return self.max_content_length_mb * 1024 * 1024


class ApplicationConfig:
    """Main application configuration class"""

    # Application Constants
    APP_NAME = "Healthcare Prep"
    APP_VERSION = "1.0.0"

    # Medical Constants
    VITAL_SIGNS = [
        "blood_pressure",
        "heart_rate",
        "temperature",
        "respiratory_rate",
        "oxygen_saturation",
        "weight",
        "height",
    ]
    APPOINTMENT_TYPES = ["routine", "urgent", "follow_up", "consultation", "procedure"]
    VISIT_TYPES = ["office_visit", "telemedicine", "hospital_visit", "emergency_visit"]

    # UI Constants
    PAGINATION_PER_PAGE = 25
    SEARCH_RESULTS_LIMIT = 100
    MAX_RECENT_PATIENTS = 10

    # Validation Constants
    MAX_NAME_LENGTH = 100
    MAX_NOTE_LENGTH = 5000
    MAX_EMAIL_LENGTH = 254
    MIN_PASSWORD_LENGTH = 8
    MAX_PHONE_LENGTH = 20
    MAX_MRN_LENGTH = 20

    # Security Patterns
    DANGEROUS_SQL_PATTERNS = [
        r"(union\s+select)",
        r"(drop\s+table)",
        r"(delete\s+from)",
        r"(insert\s+into)",
        r"(update\s+\w+\s+set)",
        r"(exec\s*\()",
        r"(script\s*>)",
        r"(javascript:)",
        r"(vbscript:)",
        r"(onload\s*=)",
        r"(onerror\s*=)",
        r"(\bor\b\s+1\s*=\s*1)",
        r"(\band\b\s+1\s*=\s*1)",
        r"(;\s*drop)",
        r"(;\s*delete)",
        r"(;\s*insert)",
        r"(;\s*update)",
        r"(--\s*)",
        r"(/\*.*?\*/)",
        r"(xp_cmdshell)",
        r"(sp_executesql)",
        r"(eval\s*\()",
        r"(<iframe)",
        r"(<object)",
        r"(<embed)",
        r"(<form)",
        r"(data:text/html)",
        r"(data:application)",
        r"(\bvoid\s*\()",
    ]

    SAFE_MIME_TYPES = [
        "text/plain",
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/gif",
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    SUSPICIOUS_USER_AGENTS = [
        "sqlmap",
        "nikto",
        "dirb",
        "dirbuster",
        "gobuster",
        "wfuzz",
        "burpsuite",
        "owasp",
        "netsparker",
        "acunetix",
        "appscan",
        "w3af",
        "skipfish",
        "arachni",
        "nuclei",
        "masscan",
        "nmap",
    ]

    def __init__(self):
        self.environment = self._get_environment()
        self.database = self._create_database_config()
        self.security = self._create_security_config()
        self.admin = self._create_admin_config()
        self.logging = self._create_logging_config()
        self.rate_limit = self._create_rate_limit_config()
        self.file_upload = self._create_file_upload_config()

        # Validate configuration
        self._validate_configuration()

    def _get_environment(self) -> Environment:
        """Get current environment"""
        env_str = os.environ.get("FLASK_ENV", "development").lower()
        try:
            return Environment(env_str)
        except ValueError:
            logger.warning(
                f"Unknown environment '{env_str}', defaulting to development"
            )
            return Environment.DEVELOPMENT

    def _create_database_config(self) -> DatabaseConfig:
        """Create database configuration"""
        database_url = os.environ.get("DATABASE_URL")

        # Handle potential "postgres://" format
        if database_url and database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        # Default to SQLite if no database URL is provided
        if not database_url:
            database_url = "sqlite:///healthcare.db"

        return DatabaseConfig(url=database_url)

    def _create_security_config(self) -> SecurityConfig:
        """Create security configuration"""
        jwt_secret = os.environ.get("JWT_SECRET_KEY")
        session_secret = os.environ.get("SESSION_SECRET")

        if not jwt_secret:
            raise ValueError("JWT_SECRET_KEY environment variable must be set")
        if not session_secret:
            raise ValueError("SESSION_SECRET environment variable must be set")

        return SecurityConfig(
            jwt_secret_key=jwt_secret,
            session_secret=session_secret,
            session_cookie_secure=self.environment == Environment.PRODUCTION,
            csrf_enabled=True,
        )

    def _create_admin_config(self) -> AdminConfig:
        """Create admin configuration"""
        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")
        email = os.environ.get("ADMIN_EMAIL", "admin@example.com")

        if not username or not password:
            raise ValueError(
                "ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set"
            )

        return AdminConfig(username=username, password=password, email=email)

    def _create_logging_config(self) -> LoggingConfig:
        """Create logging configuration"""
        log_level = os.environ.get("LOG_LEVEL", "WARNING").upper()

        return LoggingConfig(
            level=log_level,
            structured_logging=self.environment == Environment.PRODUCTION,
        )

    def _create_rate_limit_config(self) -> RateLimitConfig:
        """Create rate limiting configuration"""
        return RateLimitConfig()

    def _create_file_upload_config(self) -> FileUploadConfig:
        """Create file upload configuration"""
        return FileUploadConfig()

    def _validate_configuration(self):
        """Validate configuration for security and completeness"""
        issues = []

        # Validate JWT secret
        if len(self.security.jwt_secret_key) < 32:
            issues.append("JWT_SECRET_KEY should be at least 32 characters")

        # Check for insecure defaults
        insecure_defaults = [
            "dev_secret_key",
            "your-secret-key-change-in-production",
            "change-me",
            "default",
        ]

        if self.security.jwt_secret_key in insecure_defaults:
            issues.append("JWT_SECRET_KEY is using an insecure default value")

        if self.security.session_secret in insecure_defaults:
            issues.append("SESSION_SECRET is using an insecure default value")

        # Validate admin credentials
        if self.admin.username.lower() in ["admin", "administrator", "root", "user"]:
            issues.append("ADMIN_USERNAME should not use common default values")

        if len(self.admin.password) < self.MIN_PASSWORD_LENGTH:
            issues.append(
                f"ADMIN_PASSWORD should be at least {self.MIN_PASSWORD_LENGTH} characters"
            )

        # Report issues
        if issues:
            if self.environment == Environment.PRODUCTION:
                logger.error("Configuration validation failed:")
                for issue in issues:
                    logger.error(f"  - {issue}")
                raise ValueError("Critical configuration issues detected")
            else:
                logger.warning("Configuration validation issues:")
                for issue in issues:
                    logger.warning(f"  - {issue}")

    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask configuration dictionary"""
        return {
            # Core Flask settings
            "SECRET_KEY": self.security.session_secret,
            "PERMANENT_SESSION_LIFETIME": self.security.session_lifetime_delta,
            # Database settings
            "SQLALCHEMY_DATABASE_URI": self.database.url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": self.database.track_modifications,
            "SQLALCHEMY_ENGINE_OPTIONS": self.database.engine_options,
            # Security settings
            "WTF_CSRF_ENABLED": self.security.csrf_enabled,
            "WTF_CSRF_TIME_LIMIT": self.security.csrf_time_limit,
            "WTF_CSRF_SSL_STRICT": self.environment == Environment.PRODUCTION,
            "SESSION_COOKIE_SECURE": self.security.session_cookie_secure,
            "SESSION_COOKIE_HTTPONLY": self.security.session_cookie_httponly,
            "SESSION_COOKIE_SAMESITE": self.security.session_cookie_samesite,
            "SESSION_COOKIE_NAME": "healthprep_session",
            # File upload settings
            "MAX_CONTENT_LENGTH": self.file_upload.max_content_length,
            "UPLOAD_FOLDER": self.file_upload.upload_folder,
            # Cache settings
            "SEND_FILE_MAX_AGE_DEFAULT": (
                31536000 if self.environment == Environment.PRODUCTION else 0
            ),
        }

    def get_frontend_config(self) -> Dict[str, Any]:
        """Get configuration for frontend JavaScript"""
        return {
            "APP_NAME": self.APP_NAME,
            "APP_VERSION": self.APP_VERSION,
            "ENVIRONMENT": self.environment.value,
            "PAGINATION_PER_PAGE": self.PAGINATION_PER_PAGE,
            "SEARCH_RESULTS_LIMIT": self.SEARCH_RESULTS_LIMIT,
            "MAX_RECENT_PATIENTS": self.MAX_RECENT_PATIENTS,
            "VITAL_SIGNS": self.VITAL_SIGNS,
            "APPOINTMENT_TYPES": self.APPOINTMENT_TYPES,
            "VISIT_TYPES": self.VISIT_TYPES,
            "MAX_NAME_LENGTH": self.MAX_NAME_LENGTH,
            "MAX_NOTE_LENGTH": self.MAX_NOTE_LENGTH,
            "MAX_EMAIL_LENGTH": self.MAX_EMAIL_LENGTH,
            "MAX_PHONE_LENGTH": self.MAX_PHONE_LENGTH,
            "MAX_FILE_SIZE_MB": self.file_upload.max_content_length_mb,
            "ALLOWED_FILE_EXTENSIONS": self.file_upload.allowed_extensions,
        }

    @classmethod
    def generate_secure_secrets(cls) -> Dict[str, str]:
        """Generate secure secrets for initial setup"""
        return {
            "JWT_SECRET_KEY": secrets.token_urlsafe(64),
            "SESSION_SECRET": secrets.token_urlsafe(32),
        }


# Global configuration instance
config = ApplicationConfig()


# Convenience functions for backward compatibility
def get_config() -> ApplicationConfig:
    """Get the global configuration instance"""
    return config


def get_database_url() -> str:
    """Get database URL"""
    return config.database.url


def get_jwt_config() -> tuple:
    """Get JWT configuration"""
    return (
        config.security.jwt_secret_key,
        config.security.jwt_algorithm,
        config.security.jwt_expiration_delta,
    )


def is_production() -> bool:
    """Check if running in production"""
    return config.environment == Environment.PRODUCTION


def is_development() -> bool:
    """Check if running in development"""
    return config.environment == Environment.DEVELOPMENT
