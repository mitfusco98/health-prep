# Healthcare Prep Application - System Architecture Summary

## Overview

A comprehensive healthcare application for managing patient preparation workflows, appointments, medical documents, and screening management. The system provides both traditional web interfaces and FHIR-compliant APIs for healthcare interoperability.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python 3.11)
- **Database**: PostgreSQL 16 with SQLAlchemy ORM
- **Authentication**: JWT tokens with HTTP-only cookies
- **Session Management**: Flask sessions with CSRF protection
- **API Design**: RESTful APIs with FHIR R4 compliance
- **Deployment**: Gunicorn WSGI server with autoscale deployment

### Frontend Architecture
- **Template Engine**: Jinja2 templates
- **Styling**: Custom CSS with utility classes
- **JavaScript**: Vanilla JS for dynamic interactions
- **Forms**: Flask-WTF with CSRF protection
- **File Upload**: Werkzeug secure file handling

## Key Components

### Core Models
- **Patient**: Complete patient demographics and medical record numbers
- **Appointment**: Scheduling system with conflict detection
- **MedicalDocument**: Document management with FHIR metadata support
- **Screening**: Medical screening workflows and recommendations
- **ScreeningType**: Configurable screening definitions with trigger conditions
- **Condition**: Patient medical conditions with FHIR coding
- **Vital**: Patient vital signs tracking
- **PatientAlert**: Clinical alerts and warnings

### Business Logic Services
- **Document Processing**: Automated FHIR code extraction from medical documents
- **Screening Engine**: Intelligent screening recommendations based on patient demographics and conditions
- **FHIR Mapping**: Bidirectional conversion between internal models and FHIR R4 resources
- **Prep Sheet Generation**: Automated patient preparation workflows
- **Admin Logging**: Comprehensive audit trail for all system activities

### Security & Compliance
- **JWT Authentication**: Secure token-based authentication
- **Admin Role Protection**: Role-based access control for sensitive operations
- **Input Validation**: Comprehensive validation middleware
- **CSRF Protection**: Cross-site request forgery prevention
- **Audit Logging**: Detailed activity logging for compliance

## Data Flow

### Patient Management Workflow
1. Patient registration with demographic validation
2. Medical document upload with automatic FHIR code extraction
3. Condition tracking with standardized coding systems
4. Screening requirement evaluation based on demographics and conditions
5. Appointment scheduling with preparation workflow generation

### Document Processing Pipeline
1. File upload with secure filename handling
2. Content analysis for automatic categorization
3. FHIR metadata extraction (LOINC, SNOMED CT codes)
4. Document-to-screening matching for workflow triggers
5. Dual storage with internal and FHIR-compliant keys

### FHIR Integration Flow
1. Internal object mapping to FHIR R4 resources
2. Standards-compliant API endpoints for external systems
3. Bidirectional data conversion for EHR integration
4. Bundle creation for comprehensive patient data export

## External Dependencies

### Required Services
- **PostgreSQL**: Primary database storage
- **Redis**: Optional caching layer (falls back to memory cache)
- **File System**: Document storage with configurable paths

### FHIR Standards Support
- **FHIR R4**: Complete resource mapping for Patient, Encounter, DocumentReference
- **LOINC**: Laboratory test coding
- **SNOMED CT**: Clinical terminology
- **ICD-10**: Diagnosis coding
- **US Core**: FHIR implementation guide compliance

### Optional Integrations
- **EHR Systems**: Epic, Cerner, Allscripts integration capabilities
- **External APIs**: Configurable for additional healthcare services

## Deployment Strategy

### Production Configuration
- **Server**: Gunicorn with autoscale deployment target
- **Port Mapping**: Internal 5000 → External 80
- **Process Management**: Parallel workflow execution
- **Database**: Connection pooling with retry mechanisms
- **Monitoring**: Structured logging with correlation IDs

### Environment Management
- **Configuration**: Unified config system with environment-specific settings
- **Secrets**: Environment variable management for sensitive data
- **Database Migration**: SQLAlchemy migration support
- **Health Checks**: Built-in endpoint monitoring

### Performance Optimizations
- **Caching**: Multi-tier caching with Redis and memory fallback
- **Database**: Connection pooling and query optimization
- **Async Operations**: Non-blocking operations for heavy workloads
- **Compression**: Flask-Compress for response optimization

## Changelog
- June 24, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.