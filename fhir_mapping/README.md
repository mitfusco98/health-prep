# FHIR Patient Mapping

This module provides comprehensive functionality to convert your internal Patient objects to FHIR R4 Patient resources and vice versa, enabling seamless healthcare data interoperability.

## Overview

The FHIR (Fast Healthcare Interoperability Resources) standard is widely used for exchanging healthcare information between systems. This mapping module ensures your patient data can be easily shared with other healthcare systems, EHR platforms, and health information exchanges.

## Quick Start

```python
from fhir_mapping import PatientMapper

# Initialize the mapper
mapper = PatientMapper()

# Convert your patient to FHIR format
fhir_patient = mapper.to_fhir(your_patient_object)

# Convert FHIR back to internal format
patient_data = mapper.from_fhir(fhir_patient)
```

## Patient Fields Mapping

### Required Fields
- `id` → FHIR `identifier` (internal ID)
- `first_name` → FHIR `name.given[0]`
- `last_name` → FHIR `name.family`
- `date_of_birth` → FHIR `birthDate`
- `sex` → FHIR `gender` (mapped: Male→male, Female→female, Other→other)
- `mrn` → FHIR `identifier` (Medical Record Number)

### Optional Fields
- `phone` → FHIR `telecom` (system: phone)
- `email` → FHIR `telecom` (system: email)
- `address` → FHIR `address`
- `insurance` → FHIR `extension` (custom extension)
- `created_at` → FHIR `extension` (custom extension)
- `updated_at` → FHIR `meta.lastUpdated`

## Usage Examples

### Basic Conversion
```python
from fhir_mapping import PatientMapper
from models import Patient  # Your patient model

# Get a patient from your database
patient = Patient.query.filter_by(mrn='MRN123456').first()

# Convert to FHIR
mapper = PatientMapper()
fhir_patient = mapper.to_fhir(patient)

# The result is a complete FHIR R4 Patient resource
print(json.dumps(fhir_patient, indent=2))
```

### Integration with API Endpoints
```python
from flask import jsonify
from fhir_mapping import PatientMapper

@app.route('/api/patients/<int:patient_id>/fhir')
def get_patient_fhir(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    mapper = PatientMapper()
    fhir_patient = mapper.to_fhir(patient)
    return jsonify(fhir_patient)
```

### Bulk Export
```python
def export_patients_to_fhir():
    patients = Patient.query.all()
    mapper = PatientMapper()
    
    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": []
    }
    
    for patient in patients:
        fhir_patient = mapper.to_fhir(patient)
        fhir_bundle["entry"].append({
            "resource": fhir_patient
        })
    
    return fhir_bundle
```

## FHIR Compliance

This implementation follows FHIR R4 specifications:

- **Resource Type**: Patient
- **Profile**: Base FHIR Patient resource
- **Identifiers**: Properly typed MRN and internal ID
- **Contact Information**: Standard telecom and address formats
- **Extensions**: Custom extensions for non-standard fields
- **Validation**: Built-in validation for required fields

## Data Quality Features

- **Field Validation**: Ensures required FHIR fields are present
- **Type Safety**: Proper date/datetime formatting
- **Clean Output**: Removes empty fields from final FHIR resource
- **Error Handling**: Clear error messages for missing required data
- **Reversible Mapping**: Can convert FHIR back to internal format

## File Structure

```
fhir_mapping/
├── __init__.py          # Module initialization
├── base_mapper.py       # Base FHIR mapping utilities
├── constants.py         # FHIR constants and mappings
├── patient_mapper.py    # Patient-specific FHIR mapping
├── example_usage.py     # Usage examples and testing
└── README.md           # This documentation
```

## Error Handling

The mapper includes comprehensive error handling:

```python
try:
    fhir_patient = mapper.to_fhir(patient)
except ValueError as e:
    # Handle missing required fields
    print(f"Patient data incomplete: {e}")
except Exception as e:
    # Handle unexpected errors
    print(f"Conversion failed: {e}")
```

## Extending the Mapper

To add support for additional patient fields:

1. Update `constants.py` with new FHIR mappings
2. Extend the `to_fhir()` method in `patient_mapper.py`
3. Update the `from_fhir()` method for reverse conversion
4. Add validation rules as needed

## Testing

Run the example to test the conversion:

```bash
python fhir_mapping/example_usage.py
```

This will demonstrate the conversion process with sample data and validate the output.

## Standards Compliance

- **FHIR Version**: R4 (4.0.1)
- **Format**: JSON
- **Validation**: Built-in FHIR structure validation
- **Interoperability**: Compatible with standard FHIR servers and APIs