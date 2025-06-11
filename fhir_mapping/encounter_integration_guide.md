# FHIR Encounter Mapping Implementation Guide

## Overview

Your appointment objects are now fully convertible to FHIR R4 Encounter resources. This enables seamless integration with healthcare systems that need encounter data for scheduling, billing, and care coordination.

## Field Mapping

| Internal Appointment Field | FHIR Encounter Field | Mapping Details |
|---|---|---|
| `id` | `identifier.value` | Appointment ID as official identifier |
| `patient_id` | `subject.reference` | Patient/{patient_id} reference |
| `appointment_date` + `appointment_time` | `period.start` | Combined datetime in ISO format |
| `status` | `status` | OOO→planned, waiting→arrived, provider→in-progress, seen→finished |
| `note` | `reasonCode.text` | Free text reason for encounter |
| `created_at` | `extension` | Custom appointment scheduled timestamp |
| `updated_at` | `meta.lastUpdated` | FHIR metadata |

## Status Mapping

Your internal appointment statuses map to FHIR encounter statuses:

- **OOO** → `planned` (Scheduled but not started)
- **waiting** → `arrived` (Patient has arrived)
- **provider** → `in-progress` (Provider seeing patient)
- **seen** → `finished` (Encounter completed)

## Encounter Type Detection

The system automatically detects encounter types from appointment notes:

- **"checkup", "check-up", "annual", "physical"** → Encounter for check up
- **"follow-up", "followup", "follow up"** → Follow-up encounter
- **Default** → Consultation

## Usage Examples

### Basic Conversion
```python
from fhir_utils import appointment_to_fhir

appointment = Appointment.query.get(appointment_id)
fhir_encounter = appointment_to_fhir(appointment)
```

### API Integration
```python
from fhir_utils import add_fhir_routes
add_fhir_routes(app)

# This creates these endpoints:
# GET /fhir/Encounter/{id} - Single appointment as FHIR Encounter
# GET /fhir/Encounter?subject=Patient/{id} - Patient's encounters
# GET /fhir/Encounter?date=2024-06-15 - Encounters by date
```

### Bulk Export
```python
from fhir_utils import create_encounter_bundle

appointments = Appointment.query.filter_by(appointment_date=today).all()
encounter_bundle = create_encounter_bundle(appointments)
```

## Example FHIR Output

```json
{
  "resourceType": "Encounter",
  "id": "67890",
  "status": "arrived",
  "class": {
    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
    "code": "AMB",
    "display": "ambulatory"
  },
  "type": [{
    "coding": [{
      "system": "http://snomed.info/sct",
      "code": "185389009",
      "display": "Follow-up encounter"
    }],
    "text": "Follow-up encounter"
  }],
  "subject": {
    "reference": "Patient/12345",
    "display": "John Doe"
  },
  "period": {
    "start": "2024-06-15T14:30:00Z"
  },
  "reasonCode": [{
    "text": "Follow-up visit for blood pressure monitoring"
  }],
  "identifier": [{
    "use": "official",
    "system": "http://your-organization.com/appointment-id",
    "value": "67890"
  }]
}
```

## Standards Compliance

- **FHIR Version**: R4 (4.0.1)
- **Resource Type**: Encounter
- **Class**: Ambulatory (outpatient appointments)
- **Coding Systems**: SNOMED CT for encounter types, HL7 ActCode for classes
- **Extensions**: Custom extensions for appointment-specific data

## Integration Benefits

1. **Healthcare Interoperability**: Share appointment data with EHR systems
2. **Care Coordination**: Enable other providers to see patient encounters
3. **Analytics**: Export encounter data for reporting and analysis
4. **Billing Integration**: Provide encounter context for billing systems
5. **Care Continuity**: Track patient care episodes across systems