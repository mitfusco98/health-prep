
# Healthcare Application API Documentation

## Overview
This healthcare application provides a RESTful API for managing patients, appointments, and medical data. All API endpoints require proper authentication unless specified otherwise.

## Base URL
- Development: `http://localhost:5000`
- Production: `https://your-app-url.replit.app`

## Authentication

### JWT Token Authentication
The API uses JWT tokens for authentication. Tokens are set as HTTP-only cookies.

#### Register User
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com", 
  "password": "password123"
}
```

**Response (201):**
```json
{
  "user": {
    "id": 1,
    "username": "newuser",
    "email": "user@example.com",
    "is_admin": false
  }
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123" 
}
```

**Response (200):**
```json
{
  "user": {
    "id": 1,
    "username": "user@example.com", 
    "email": "user@example.com",
    "is_admin": false
  }
}
```

#### Verify Token
```http
GET /api/auth/verify
```

**Response (200):**
```json
{
  "valid": true,
  "user": {
    "id": 1,
    "username": "user@example.com",
    "is_admin": false
  }
}
```

#### Refresh Token
```http
POST /api/auth/refresh
```

#### Logout
```http
POST /api/auth/logout
```

## Patients API

### Get Patients
```http
GET /api/patients?page=1&per_page=20&search=john&sort=name&order=asc
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)
- `search` (optional): Search term for name or MRN
- `sort` (optional): Sort field (name, mrn, age, created_at)
- `order` (optional): Sort order (asc, desc)

**Response (200):**
```json
{
  "patients": [
    {
      "id": 1,
      "mrn": "MRN001",
      "first_name": "John",
      "last_name": "Doe", 
      "full_name": "John Doe",
      "date_of_birth": "1980-01-01",
      "age": 44,
      "sex": "Male",
      "phone": "555-0123",
      "email": "john.doe@example.com",
      "address": "123 Main St",
      "insurance": "Blue Cross",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 50,
    "pages": 3,
    "has_next": true,
    "has_prev": false,
    "next_num": 2,
    "prev_num": null
  }
}
```

### Get Patient Details
```http
GET /api/patients/{patient_id}
```

**Response (200):**
```json
{
  "id": 1,
  "mrn": "MRN001",
  "first_name": "John",
  "last_name": "Doe",
  "conditions": [
    {
      "id": 1,
      "name": "Hypertension",
      "code": "I10",
      "diagnosed_date": "2023-01-01",
      "notes": "Well controlled"
    }
  ],
  "recent_vitals": [...],
  "recent_visits": [...],
  "screenings": [...],
  "alerts": [...]
}
```

### Create Patient
```http
POST /api/patients
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith",
  "date_of_birth": "1985-05-15",
  "sex": "Female",
  "phone": "555-0124",
  "email": "jane.smith@example.com",
  "address": "456 Oak Ave",
  "insurance": "Aetna"
}
```

**Response (201):**
```json
{
  "id": 2,
  "mrn": "MRN002",
  "first_name": "Jane",
  "last_name": "Smith",
  "full_name": "Jane Smith",
  "date_of_birth": "1985-05-15",
  "age": 39,
  "sex": "Female",
  "phone": "555-0124",
  "email": "jane.smith@example.com",
  "address": "456 Oak Ave", 
  "insurance": "Aetna",
  "created_at": "2024-01-01T00:00:00"
}
```

## Appointments API

### Get Appointments
```http
GET /api/appointments?date=2024-01-01
```

**Query Parameters:**
- `date` (optional): Date in YYYY-MM-DD format (default: today)

**Response (200):**
```json
{
  "date": "2024-01-01",
  "appointments": [
    {
      "id": 1,
      "patient_id": 1,
      "patient_name": "John Doe",
      "patient_mrn": "MRN001",
      "appointment_date": "2024-01-01",
      "appointment_time": "09:00",
      "note": "Annual checkup",
      "status": "OOO"
    }
  ],
  "total": 1
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

### Authentication Errors
```json
{
  "error": "Authentication required"
}
```

### Validation Errors
```json
{
  "error": "Validation failed",
  "details": [
    "first_name is required",
    "Invalid email format"
  ]
}
```

### Server Errors
```json
{
  "error": "Internal server error",
  "error_id": "abc123"
}
```

## Rate Limiting
- API endpoints are rate limited to prevent abuse
- Rate limit: 100 requests per minute per IP
- Rate limit headers are included in responses

## Data Validation
- All input data is validated
- Required fields must be provided
- Email addresses must be valid format
- Dates must be in YYYY-MM-DD format
- Phone numbers must contain 10-15 digits

## Security
- All endpoints require JWT authentication except auth endpoints
- HTTPS is enforced in production
- Input sanitization is applied to prevent injection attacks
- Sensitive data is never logged
