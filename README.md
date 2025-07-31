
# 🩺 Health-Prep: AI-Powered Chart Prep Automation

**Health-Prep** is a provider-facing tool that automates chart preparation using a configurable screening engine. It streamlines medical document review by matching incoming files against customizable keyword sets, reducing the prep burden on medical assistants, nurses, and clinical teams.

---

## 🚀 Features

### Core Functionality
- ✅ **Customizable Screening Engine**  
  Match uploaded or EMR-sourced documents to user-defined keywords, phrases, or file naming patterns with confidence scoring.

- ⚙️ **Automated Prep Sheet Generation**  
  Auto-generates prep sheets for upcoming appointments — continuously updated as new documents arrive with FHIR compliance.

- 🧠 **Smart Specialty-Based Presets**  
  Create and share screening configurations tailored by medical specialty (e.g., cardiology, pediatrics) with variant detection.

- 🔁 **Prep-All and Bulk Generation**  
  Instantly generate prep sheets for a full day's schedule — built to scale to 500+ patients at once with high-performance optimization.

### Advanced Features
- 🔒 **HIPAA-Oriented Design**  
  Includes PHI redaction tools, comprehensive admin logging, and patient data safety features.

- 📊 **Real-time Performance Monitoring**  
  Built-in profiler tracks database queries, response times, and system performance.

- 🔄 **Async Processing**  
  Background workers handle document processing and screening recommendations asynchronously.

- 🏥 **FHIR R4 Compliance**  
  Full FHIR mapping for Patient, Document, and Encounter resources with export capabilities.

- 🔐 **Enterprise Security**  
  JWT authentication, rate limiting, CSRF protection, and comprehensive audit trails.

---

## 🛠️ Technical Architecture

### Backend Stack
- **Framework**: Flask 3.x with Python 3.11
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT with HTTP-only cookies
- **Caching**: Multi-layer caching with Redis-compatible backends
- **Security**: Comprehensive input validation and SQL injection prevention

### Frontend
- **Templates**: Jinja2 with Bootstrap CSS framework
- **JavaScript**: Vanilla JS with AJAX for dynamic interactions
- **UI**: Responsive design optimized for clinical workflows

### Performance Features
- **Query Optimization**: Intelligent caching and pagination
- **Async Processing**: Background workers for heavy operations
- **Database Profiling**: Real-time query performance monitoring
- **Memory Management**: Efficient handling of large document repositories

---

## 📁 Repository Structure

```bash
health-prep/
│
├── app.py                     # Main Flask application with middleware
├── main.py                    # Application entry point
├── config.py                  # Unified configuration management
│
├── organized/                 # Modular application components
│   ├── routes/               # Route handlers by feature
│   │   ├── screening_routes.py    # Screening management
│   │   ├── patient_routes.py      # Patient CRUD operations
│   │   ├── document_routes.py     # Document upload/management
│   │   └── api_routes.py          # REST API endpoints
│   ├── services/             # Business logic layer
│   │   ├── patient_service.py     # Patient data operations
│   │   └── cache_manager.py       # Caching strategies
│   ├── utils/                # Helper utilities
│   │   ├── security_jwt_utils.py  # JWT authentication
│   │   ├── validation_*.py        # Input validation
│   │   └── helper_*.py            # Various utilities
│   └── models/               # Database models
│       └── healthcare_models.py   # SQLAlchemy models
│
├── fhir_mapping/             # FHIR R4 compliance layer
│   ├── patient_mapper.py     # Patient resource mapping
│   ├── document_reference_mapper.py  # Document mapping
│   └── encounter_mapper.py   # Encounter resource mapping
│
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS, JavaScript, and assets
├── attached_assets/          # Test documents (non-PHI)
│
├── models.py                 # Core database models
├── demo_routes.py           # Main application routes
├── auth_routes.py           # Authentication endpoints
├── api_routes.py            # REST API implementation
└── screening_*.py           # Screening engine components
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (or SQLite for development)
- Environment variables configured

### Environment Setup
1. **Configure Environment Variables** (in Replit Secrets or `.env`):
   ```bash
   DATABASE_URL=postgresql://user:pass@host:port/dbname
   JWT_SECRET_KEY=your-secure-jwt-secret
   SESSION_SECRET=your-session-secret
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=secure-password
   ```

2. **Run the Application**:
   ```bash
   # The application auto-installs dependencies
   # Click the Run button or execute:
   python main.py
   ```

3. **Access the Application**:
   - Main app: `https://your-repl-name.replit.app`
   - API endpoints: `https://your-repl-name.replit.app/api/`
   - Admin dashboard: `https://your-repl-name.replit.app/admin/`

### Initial Setup
1. **Add Sample Data**:
   ```bash
   python add_test_patients.py
   python add_default_screening_types.py
   ```

2. **Create Admin User**:
   ```bash
   python create_admin_user.py
   ```

---

## 🔧 Key Components

### Screening Engine
- **Keyword Matching**: Intelligent document-to-screening matching
- **Confidence Scoring**: Machine learning-inspired confidence levels
- **Variant Management**: Handles screening type variations (e.g., "A1C" vs "HbA1c")
- **Performance Optimization**: Cached queries and bulk processing

### Document Processing
- **OCR Support**: Extract text from scanned documents
- **FHIR Integration**: Automatic FHIR DocumentReference creation
- **PHI Filtering**: Configurable PII/PHI redaction
- **Dual Storage**: Internal and FHIR-compliant metadata storage

### Admin Features
- **Comprehensive Logging**: All user actions and system events
- **Performance Dashboard**: Real-time system metrics
- **Security Monitoring**: Failed login attempts and suspicious activity
- **Data Validation**: Integrity checks and automated cleanup

---

## 📊 Performance Features

### Optimization Techniques
- **Database Query Caching**: Intelligent caching with automatic invalidation
- **Async Processing**: Background workers for heavy operations
- **Pagination**: Efficient handling of large datasets
- **Connection Pooling**: Optimized database connections

### Monitoring
- **Query Profiler**: Tracks slow database queries (>100ms)
- **Performance Metrics**: Response times, memory usage, and throughput
- **Error Tracking**: Comprehensive error logging with unique IDs
- **Admin Dashboard**: Real-time system health monitoring

---

## 🔒 Security Features

### Authentication & Authorization
- **JWT Authentication**: Secure token-based authentication
- **Session Management**: Secure session handling with timeout
- **Role-Based Access**: Admin and user permission levels
- **Rate Limiting**: Prevents brute force and DoS attacks

### Data Protection
- **Input Validation**: Comprehensive sanitization and validation
- **SQL Injection Prevention**: Parameterized queries and ORM usage
- **XSS Protection**: Content Security Policy and output escaping
- **CSRF Protection**: Token-based CSRF prevention

### Compliance
- **Admin Logging**: Complete audit trail of all operations
- **PHI Redaction**: Configurable PII/PHI filtering
- **Data Encryption**: Secure data transmission and storage
- **Access Controls**: Fine-grained permission management

---

## 🏥 FHIR Integration

### Supported Resources
- **Patient**: Complete demographic and contact information
- **DocumentReference**: Medical document metadata and content
- **Encounter**: Visit and appointment information
- **Condition**: Medical conditions and diagnoses

### Features
- **FHIR R4 Compliance**: Full specification compliance
- **Bidirectional Mapping**: Convert to/from FHIR format
- **Bulk Export**: FHIR Bundle generation for data exchange
- **Validation**: Built-in FHIR resource validation

---

## 📈 Scalability

### Performance Benchmarks
- **Patient Capacity**: Tested with 1000+ patients
- **Document Processing**: Handles 500+ documents per batch
- **Concurrent Users**: Supports 50+ simultaneous users
- **Response Times**: <200ms for most operations

### Deployment on Replit
- **Auto-scaling**: Automatic resource allocation
- **Database**: PostgreSQL with connection pooling
- **Static Assets**: Optimized CSS/JS delivery
- **Monitoring**: Built-in performance tracking

---

## 🤝 Contributing

### Development Workflow
1. Fork the repository in Replit
2. Make your changes in a development branch
3. Test thoroughly with sample data
4. Submit a pull request with detailed description

### Code Standards
- **Python**: Follow PEP 8 styling guidelines
- **Security**: All inputs must be validated and sanitized
- **Testing**: Include tests for new functionality
- **Documentation**: Update README and inline docs

---

## 📝 License

This project is designed for healthcare environments. Please ensure compliance with HIPAA, HITECH, and other applicable regulations when handling patient data.

---

## 🆘 Support

### Troubleshooting
- Check the console logs for detailed error messages
- Use the admin dashboard for system health monitoring
- Review the comprehensive logging for debugging

### Performance Issues
- Check database query performance in the profiler
- Monitor memory usage and response times
- Use the cache clearing endpoints if needed

### Security Concerns
- Review admin logs for suspicious activity
- Check rate limiting and failed authentication attempts
- Ensure all environment variables are properly configured

---

**Built for healthcare providers who need efficient, secure, and scalable chart preparation automation.**
