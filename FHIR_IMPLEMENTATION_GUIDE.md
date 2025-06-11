# FHIR Patient Mapping Implementation Guide

## Overview

Your healthcare application now has complete FHIR R4 Patient resource conversion capabilities. This implementation converts your internal Patient objects (with fields: id, first_name, last_name, dob, sex, mrn) into standard FHIR Patient resources for healthcare interoperability.

## Quick Integration

### Simple Usage
```python
from fhir_utils import patient_to_fhir

# Convert any patient to FHIR
patient = Patient.query.get(patient_id)
fhir_resource = patient_to_fhir(patient)
```

### Add FHIR API Endpoints
```python
from fhir_utils import add_fhir_routes

# Add to your app.py
add_fhir_routes(app)
```

This creates:
- `GET /fhir/Patient/{id}` - Single patient as FHIR resource
- `GET /fhir/Patient?identifier={mrn}` - Search by MRN
- `GET /fhir/Patient` - All patients as FHIR Bundle

## Files Created

### Core FHIR Mapping (`fhir_mapping/`)
- `constants.py` - FHIR R4 standard constants and mappings
- `base_mapper.py` - Base utilities for FHIR resource creation
- `patient_mapper.py` - Patient-specific FHIR conversion logic
- `__init__.py` - Module initialization

### Integration Files
- `fhir_utils.py` - Ready-to-use utility functions
- `fhir_integration.py` - Advanced integration features
- `test_fhir_conversion.py` - Comprehensive test suite

## Field Mapping

| Internal Field | FHIR Field | Notes |
|---|---|---|
| `id` | `identifier` (secondary) | Internal system ID |
| `mrn` | `identifier` (official) | Medical Record Number |
| `first_name` | `name.given[0]` | Given name |
| `last_name` | `name.family` | Family name |
| `date_of_birth` | `birthDate` | ISO date format |
| `sex` | `gender` | Male→male, Female→female, Other→other |
| `phone` | `telecom` (phone) | Contact information |
| `email` | `telecom` (email) | Contact information |
| `address` | `address` | Parsed into FHIR address components |
| `insurance` | `extension` | Custom extension |
| `created_at` | `extension` | Custom extension |
| `updated_at` | `meta.lastUpdated` | FHIR metadata |

## Example FHIR Output

```json
{
  "resourceType": "Patient",
  "id": "12345",
  "active": true,
  "identifier": [
    {
      "use": "official",
      "type": {
        "coding": [{
          "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
          "code": "MR",
          "display": "Medical record number"
        }]
      },
      "value": "MRN123456"
    }
  ],
  "name": [{
    "use": "official",
    "family": "Doe",
    "given": ["John"]
  }],
  "telecom": [
    {
      "system": "phone",
      "value": "555-123-4567",
      "use": "home"
    },
    {
      "system": "email", 
      "value": "john.doe@example.com",
      "use": "home"
    }
  ],
  "gender": "male",
  "birthDate": "1985-03-15",
  "address": [{
    "use": "home",
    "type": "physical",
    "line": ["123 Main St"],
    "city": "Anytown",
    "state": "NY",
    "postalCode": "12345"
  }]
}
```

## Validation & Error Handling

The implementation includes:
- Required field validation
- Proper FHIR structure validation
- Type-safe date/datetime formatting
- Graceful handling of missing optional fields
- Clear error messages for incomplete data

## Use Cases

### Healthcare Data Exchange
Export patient data to other EHR systems, health information exchanges, or clinical applications.

### API Integration
Provide FHIR-compliant patient data endpoints for third-party integrations.

### Bulk Export
Export all patients as FHIR Bundle for backup, migration, or analytics.

### Interoperability
Enable seamless data sharing with FHIR-compatible healthcare systems.

## Testing

The implementation has been thoroughly tested with:
- Complete patient records (all fields)
- Minimal patient records (required fields only)
- Round-trip conversion (internal → FHIR → internal)
- FHIR validation compliance
- Error handling for incomplete data

Run tests:
```bash
python test_fhir_conversion.py
```

## Standards Compliance

- **FHIR Version**: R4 (4.0.1)
- **Resource Type**: Patient
- **Format**: JSON
- **Identifiers**: Properly typed with standard code systems
- **Extensions**: Used for non-standard fields
- **Validation**: Built-in FHIR structure validation

## Next Steps

1. **Import to Routes**: Add `from fhir_utils import add_fhir_routes; add_fhir_routes(app)` to your main app
2. **Test Endpoints**: Use the new FHIR API endpoints with real patient data
3. **Extend Mapping**: Add support for additional resources (Observation, Condition, etc.)
4. **Integration**: Connect with external FHIR servers or healthcare systems

Your FHIR patient mapping is production-ready and follows healthcare industry standards for data interoperability.