# FHIR Mapping Implementation Guide

## Overview

Your healthcare application now has complete FHIR R4 conversion capabilities for Patient, Encounter, and DocumentReference resources. This implementation converts your internal data objects into standard FHIR resources for healthcare interoperability:

- **Patient objects** (id, first_name, last_name, dob, sex, mrn) → FHIR Patient resources
- **Appointment objects** (appointment_id, patient_id, date, time, note, status) → FHIR Encounter resources
- **Medical Document objects** (id, patient_id, filename, upload_date, section, tags) → FHIR DocumentReference resources

## Quick Integration

### Simple Usage
```python
from fhir_utils import patient_to_fhir, appointment_to_fhir, document_to_fhir

# Convert patient to FHIR
patient = Patient.query.get(patient_id)
fhir_patient = patient_to_fhir(patient)

# Convert appointment to FHIR Encounter
appointment = Appointment.query.get(appointment_id)
fhir_encounter = appointment_to_fhir(appointment)

# Convert document to FHIR DocumentReference
document = MedicalDocument.query.get(document_id)
fhir_document_ref = document_to_fhir(document)
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
- `GET /fhir/Encounter/{id}` - Single appointment as FHIR Encounter
- `GET /fhir/Encounter?subject=Patient/{id}` - Patient's encounters
- `GET /fhir/Encounter?date=2024-06-15` - Encounters by date
- `GET /fhir/DocumentReference/{id}` - Single document as FHIR DocumentReference
- `GET /fhir/DocumentReference?subject=Patient/{id}` - Patient's documents
- `GET /fhir/DocumentReference?type=Lab%20Results` - Documents by type

## Files Created

### Core FHIR Mapping (`fhir_mapping/`)
- `constants.py` - FHIR R4 standard constants and mappings
- `base_mapper.py` - Base utilities for FHIR resource creation
- `patient_mapper.py` - Patient-specific FHIR conversion logic
- `encounter_mapper.py` - Appointment to Encounter FHIR conversion logic
- `__init__.py` - Module initialization

### Integration Files
- `fhir_utils.py` - Ready-to-use utility functions for both resources
- `fhir_integration.py` - Advanced integration features
- `test_fhir_conversion.py` - Patient conversion test suite
- `test_fhir_encounter_conversion.py` - Encounter conversion test suite
- `test_fhir_document_conversion.py` - DocumentReference conversion test suite

## Patient Field Mapping

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

## Appointment Field Mapping

| Internal Field | FHIR Encounter Field | Notes |
|---|---|---|
| `id` | `identifier.value` | Appointment ID as identifier |
| `patient_id` | `subject.reference` | Patient/{patient_id} reference |
| `appointment_date + appointment_time` | `period.start` | Combined datetime in ISO format |
| `status` | `status` | OOO→planned, waiting→arrived, provider→in-progress, seen→finished |
| `note` | `reasonCode.text` | Free text reason for encounter |
| `created_at` | `extension` | Custom appointment scheduled timestamp |
| `updated_at` | `meta.lastUpdated` | FHIR metadata |

## Medical Document Field Mapping

| Internal Field | FHIR DocumentReference Field | Notes |
|---|---|---|
| `id` | `identifier.value` | Document ID as official identifier |
| `patient_id` | `subject.reference` | Patient/{patient_id} reference |
| `filename` | `content.attachment.title` | Original filename as document title |
| `document_name` | `content.attachment.title` | Preferred over filename if available |
| `document_type` | `type.coding` | Maps to LOINC codes (Lab Results→11502-2, etc.) |
| `mime_type` | `content.attachment.contentType` | MIME type for content format |
| `document_date` | `date` | Document creation/authoring date |
| `provider` | `author.display` | Document author/provider |
| `source_system` | `authenticator.display` | Source EHR/system identifier |
| `is_processed` | `docStatus` | preliminary/final based on processing status |
| `doc_metadata` | `extension` | Custom extension for metadata JSON |
| `created_at` | `content.attachment.creation` | File creation timestamp |
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