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
- **Automated Screening Engine**: Intelligent screening status determination based on document parsing rules and patient eligibility
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
- July 12, 2025: **CRITICAL DATE CORRECTION - MEDICAL EVENT vs SYSTEM DATES**: Fixed fundamental issue where "last completed" dates showed system upload dates instead of actual medical event dates. Updated automated screening engine to prioritize document_date (actual medical event) over created_at (system upload). Cam Davis's eye exam now correctly shows completion date of 01/02/2025 (when exam was performed) instead of 07/09/2025 (when document was uploaded). Enhanced screening engine with proper date prioritization logic and fallback handling. Medical accuracy now maintained throughout the system.
- July 12, 2025: **ENHANCED PHRASE MATCHING SYSTEM**: Implemented multi-word phrase support for medical keyword matching. Fixed "US" false positive issue by supporting "breast US" as a legitimate medical phrase while eliminating random "US" matches in unrelated text. Created enhanced keyword matcher with context-aware matching, word boundaries, and flexible spacing/punctuation handling. Updated mammogram parsing rules to use phrase-based approach. Charlotte Taylor's 9 documents now correctly show no false positive matches.
- July 12, 2025: **COMPREHENSIVE KEYWORD DIAGNOSTIC TOOL**: Created advanced diagnostic system to analyze keyword triggers and document matching logic. Identified and resolved Charlotte Taylor's mammogram screening false positives - 5 documents incorrectly matched due to overly broad "US" keyword. Updated mammogram parsing rules from generic keywords to specific medical terms, added document type filtering (RADIOLOGY_REPORT, IMAGING_REPORT), and implemented word boundary matching. Created diagnostic tool capable of analyzing keyword matches for any patient/screening combination, showing exact text context, match confidence, and trigger sources. Tool successfully eliminated false positives while maintaining legitimate matches.
- July 11, 2025: **CRITICAL LOGIC FIX - SCREENING STATUS VALIDATION**: Fixed fundamental logical contradiction where screenings were marked "Complete" without matched documents. Enhanced automated screening engine with strict validation ensuring Complete status only occurs with actual document relationships. Added multi-layered validation in screening update process, including pre-save document validation, final verification after document linking, and SQL-based cleanup of invalid existing records. Fixed 8 existing "Complete" screenings that lacked documents. System now enforces rule: Complete status requires matched documents based on parsing rules and eligibility criteria.
- July 11, 2025: **COMPREHENSIVE ERROR HANDLING FOR DOCUMENT-SCREENING RELATIONSHIPS**: Implemented robust error handling system for document-screening many-to-many relationships. Added validation methods to Screening model to detect and clean up orphaned document relationships. Enhanced view_document route with proper 404 error handling, permission validation, and graceful redirects. Updated templates with client-side error handling for document links, including visual feedback and user alerts. Created admin utilities for validating and cleaning up orphaned relationships system-wide. Added automated cleanup during screening refresh operations. Error handling gracefully manages cases where documents are deleted but relationships persist, ensures users get appropriate feedback, and maintains data integrity throughout the system.
- July 11, 2025: **ENHANCED AUTOMATED SCREENING SYSTEM**: Updated screening generation logic in demo_routes.py to work seamlessly with the new document relationship system. The refresh functionality now creates proper many-to-many database relationships instead of storing document matches in notes field. System integrates with both /screenings?tab=types parsing rules and /screenings?tab=checklist settings. Enhanced error handling and logging for document linking process. Automated screening engine now successfully generates screenings based on patient eligibility (age, sex, trigger conditions) and matches documents using content, filename, and document type keywords from ScreeningType parsing rules.
- July 11, 2025: **MAJOR ARCHITECTURAL ENHANCEMENT - Many-to-Many Document Relationships**: Replaced fragile pipe-separated document ID storage in screening.notes with proper many-to-many relationship table (screening_documents). Created association table with foreign keys between Screening and MedicalDocument models, added documents relationship property to Screening model, updated automated screening engine to use proper relationships instead of parsing notes, enhanced template to display linked documents using the relationship, and included confidence scoring and match source tracking in the association table.
- July 10, 2025: **PERFORMANCE OPTIMIZATION & UI IMPROVEMENT**: Optimized automated screening system to only regenerate on explicit request (regenerate=true parameter) instead of every page load, significantly improving performance. Restructured /screenings interface to match previous design with search bar, status/type filters instead of status counters, removed due date column, enhanced last completed to show document match dates, and made notes column display hyperlinked matched documents that redirect to document view pages.
- July 10, 2025: **MAJOR ARCHITECTURAL CHANGE - Automated Screening System**: Replaced manual screening management with intelligent automated screening generation based on parsing rules. Migrated 'priority' column to 'status' column with values 'Due', 'Due Soon', 'Incomplete', 'Complete'. Created automated screening engine that analyzes patient documents against screening type parsing rules to determine status. System now automatically generates screenings based on age, gender, medical conditions, and document matching. Added automated screening routes and management interface.
- July 7, 2025: Replaced "screenings" medical data subsection with "other" subsection for miscellaneous documents. Updated both frontend patient detail template and prep sheet template to display uncategorized documents (those not classified as lab, imaging, consult, or hospital documents). Backend now categorizes documents and provides other_documents data to both patient detail and prep sheet views.
- July 1, 2025: Enhanced document screening functionality with multi-criteria matching system. Added confidence scoring, match source tracking, and integrated document matching into prep sheet template. Created 18 sample medical documents (8 matching, 10 non-matching) to test screening logic. Documents now display in status/notes boxes with confidence badges and visual styling.
- June 26, 2025: Streamlined keyword and screening management system to eliminate redundant API calls and "old system" references. Created efficient screening matcher that uses only current 'manage screening types' system with keyword caching.
- June 26, 2025: Fixed Flask application startup issues by replacing complex middleware system with minimal working healthcare app. Resolved route import errors and template build failures.
- June 26, 2025: Added automatic session timeout with 10-minute inactivity logout. Users can stay logged in when accessing admin pages and receive warnings before timeout. Session extends automatically on user activity.
- June 26, 2025: Rebuilt screening checklist settings page due to persistent multiple selection issues. Created simplified button-based interface with reliable form processing.
- June 25, 2025: Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.