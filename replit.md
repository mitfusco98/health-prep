# Healthcare Prep Application

## Overview
A comprehensive Flask-based healthcare preparation application designed to manage patient data, appointments, medical documents, and screening requirements. It offers web interfaces and API endpoints with JWT authentication, admin logging, and FHIR compliance. The application features advanced screening type management, including intelligent data preservation during activation/deactivation cycles, aiming to streamline healthcare workflows and improve patient care coordination.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- **Templates**: Jinja2 with Bootstrap CSS framework for a responsive design suitable for clinical workflows.
- **JavaScript**: Vanilla JavaScript with AJAX for dynamic interactions.
- **Color Scheme/Design Approach**: Not explicitly detailed, but implied by Bootstrap and focus on clinical usability.

### Technical Implementations
- **Backend Framework**: Flask 3.x with Python 3.11.
- **Architecture Pattern**: Monolithic with modular route organization.
- **Database ORM**: SQLAlchemy with Alembic for migrations.
- **Authentication**: JWT tokens with HTTP-only cookies and refresh tokens.
- **API Design**: RESTful endpoints with CSRF protection.
- **Security**: Role-based access control (admin/user), comprehensive input validation, Flask-Limiter for rate limiting, and extensive admin logging for audit trails.
- **Core Models**: Patient, Appointment, MedicalDocument (with FHIR metadata and dual storage keys), Screening, ScreeningType, Condition (with FHIR code mapping), AdminLog.
- **Route Organization**: Modular routes for Patient, Appointment, Medical, Screening, Admin, and API operations.
- **Business Logic Services**: Document Processing (automated tagging, FHIR metadata extraction), Unified Screening Architecture (consolidated engines, shared base classes for demographic filtering, document matching, status determination), Automated Screening Engine (intelligent status determination), FHIR Integration, and Prep Sheet Generation.
- **Data Flow**: Defined flows for patient management, document processing, and authentication.
- **Screening System**: Intelligent document prioritization based on recency and frequency, PHI filtering for HIPAA compliance, confidence-based color coding for document matching, and a comprehensive variant recognition system.
- **Document Handling**: Universal document viewing for PDF, image, and text with automatic OCR processing, including confidence scoring and PHI filtering. Critical fixes for document upload binary content and OCR integration.
- **Data Preservation**: Implemented a system for screening type deactivation/reactivation that preserves data integrity, ensuring smart refresh functionality.

### Feature Specifications
- **Patient Management**: CRUD operations, demographic validation, MRN assignment, medical data association, appointment scheduling, and prep sheet generation.
- **Appointment Management**: Scheduling with conflict detection and status tracking.
- **Medical Document Management**: Secure file storage, content extraction, automated tagging, FHIR metadata generation, and integration with patient records.
- **Screening Management**: Configuration and evaluation of screening types, automated status determination, and consistent data display across interfaces.
- **API**: RESTful endpoints for all core functionalities.
- **Security**: JWT-based authentication, role-based authorization, rate limiting, and comprehensive audit logging.
- **FHIR Compliance**: Data mapping and integration for healthcare interoperability.
- **Prep Sheet Generation**: Automated creation of preparation sheets based on medical history and screening status.
- **OCR Integration**: Automatic OCR for all document uploads, with PHI filtering and real-time screening updates.
- **System Stability**: Includes solutions for worker timeouts, JSON parsing errors, and robust document deletion cascade.
- **Keyword Matching**: Enhanced phrase matching, comprehensive diagnostic tools, and critical fixes for filename separator handling.
- **Data Consistency**: Ensures consistency between prep sheet and screening data through a single source of truth for screening data.
- **Variant Management**: Unified status management for screening variants, preventing false matches and ensuring medical accuracy.
- **Database Access Layer**: Enterprise-grade with prepared statements, transaction handling, connection pooling, and specialized handlers for complex operations.

## External Dependencies

- **Web Framework**: Flask (v3.x)
- **Database ORM**: SQLAlchemy
- **Primary Database**: PostgreSQL
- **Caching/Session Management**: Redis (optional)
- **WSGI Server**: Gunicorn
- **JWT Handling**: PyJWT
- **Security Utilities**: Werkzeug (for password hashing), Flask-Limiter (for rate limiting), Flask-CSRF (for CSRF protection)
- **Healthcare Standards**: FHIR Libraries
- **Document Processing**: Tesseract (for OCR), various libraries for text extraction and medical coding.
- **Medical Data Validation**: Specific validation libraries for medical data.
- **Optional Integrations**: EHR Systems (Epic, Cerner), Cloud Storage, Monitoring (structured logging).