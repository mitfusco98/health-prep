# Healthcare Prep Application

## Overview

A comprehensive healthcare preparation application built with Flask that manages patient data, appointments, medical documents, and screening requirements. The application provides both traditional web interfaces and modern API endpoints with JWT authentication, admin logging, and FHIR (Fast Healthcare Interoperability Resources) compliance for healthcare data exchange.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap CSS framework
- **JavaScript**: Vanilla JavaScript with AJAX for dynamic interactions
- **Static Assets**: CSS organized in modular stylesheets with audit capabilities
- **Responsive Design**: Mobile-friendly interfaces for clinical workflows

### Backend Architecture
- **Framework**: Flask 3.x with Python 3.11
- **Architecture Pattern**: Monolithic with modular route organization
- **Database ORM**: SQLAlchemy with Alembic migrations
- **Authentication**: JWT tokens with HTTP-only cookies
- **API Design**: RESTful endpoints with CSRF protection

### Security Layer
- **Authentication**: JWT-based with refresh tokens
- **Authorization**: Role-based access control (admin/user)
- **Input Validation**: Comprehensive validation middleware
- **Rate Limiting**: Flask-Limiter for API endpoint protection
- **Admin Logging**: Comprehensive audit trail for all operations

## Key Components

### Core Models
- **Patient**: Demographics, contact information, medical record numbers
- **Appointment**: Scheduling with conflict detection and status tracking
- **MedicalDocument**: File storage with FHIR metadata and dual storage keys
- **Screening**: Medical screening types with trigger conditions
- **Condition**: Patient medical conditions with FHIR code mapping
- **AdminLog**: Comprehensive audit logging system

### Route Organization
- **Patient Routes**: CRUD operations for patient management
- **Appointment Routes**: Scheduling system with conflict detection
- **Medical Routes**: Document upload, medical data management
- **Screening Routes**: Screening type configuration and evaluation
- **Admin Routes**: Administrative functions and audit logs
- **API Routes**: RESTful endpoints with JWT authentication

### Business Logic Services
- **Document Processing**: Automated tagging and FHIR metadata extraction
- **Screening Evaluation**: Rule-based screening recommendations
- **FHIR Integration**: Standards-compliant healthcare data mapping
- **Prep Sheet Generation**: Automated preparation sheet creation

## Data Flow

### Patient Management Flow
1. Patient registration/import via web forms or CSV
2. Demographic validation and MRN assignment
3. Medical data association (conditions, documents, screenings)
4. Appointment scheduling with conflict detection
5. Prep sheet generation based on medical history

### Document Processing Flow
1. File upload with security validation
2. Content extraction and automated tagging
3. FHIR metadata generation and storage
4. Screening type matching based on content
5. Integration with patient medical record

### Authentication Flow
1. User login with credential validation
2. JWT token generation and secure cookie storage
3. Request authentication via middleware
4. Role-based access control enforcement
5. Admin action logging for audit compliance

## External Dependencies

### Core Dependencies
- **Flask**: Web framework (v3.x)
- **SQLAlchemy**: Database ORM
- **PostgreSQL**: Primary database
- **Redis**: Optional caching layer
- **Gunicorn**: WSGI server for production

### Security Dependencies
- **PyJWT**: JWT token handling
- **Werkzeug**: Password hashing and security utilities
- **Flask-Limiter**: Rate limiting
- **Flask-CSRF**: CSRF protection

### Healthcare Dependencies
- **FHIR Libraries**: Standards-compliant data mapping
- **Document Processing**: Text extraction and medical coding
- **Validation Libraries**: Medical data validation

### Optional Integrations
- **EHR Systems**: Epic, Cerner integration capabilities
- **File Storage**: Local filesystem with cloud storage options
- **Monitoring**: Structured logging and performance monitoring

## Deployment Strategy

### Development Environment
- **Replit Integration**: Configured for Replit deployment
- **Environment Variables**: Sensitive configuration in Replit Secrets
- **Database**: PostgreSQL with connection pooling
- **Hot Reload**: Gunicorn with reload capability

### Production Configuration
- **Server**: Gunicorn with multiple workers
- **Database**: PostgreSQL with SSL connections
- **Caching**: Redis for session storage and caching
- **Security**: Environment-based secrets management
- **Monitoring**: Structured logging with admin audit trails

### Database Schema Management
- **Migrations**: SQLAlchemy-based database versioning
- **Backup Strategy**: Regular database backups
- **Connection Pooling**: Optimized for concurrent users
- **Performance**: Indexed queries and caching layers

## Changelog
- June 25, 2025. Initial setup
- June 25, 2025. Replaced checkbox system with multiselect dropdown for screening type selection in /screenings?tab=checklist to fix multiple selection issues

## User Preferences

Preferred communication style: Simple, everyday language.