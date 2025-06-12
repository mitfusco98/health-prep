# FHIR Object Mapping Integration Guide

## Overview

Your healthcare application now has comprehensive FHIR mapping functions that convert internal objects (Patient, Appointment, MedicalDocument) to FHIR-compliant resources for prep sheet logic and external API compatibility.

## Core Mapping Functions

### Patient Mapping
```python
from fhir_object_mappers import patient_to_fhir

# Convert patient to FHIR Patient resource
fhir_patient = patient_to_fhir(patient)

# Result: Complete FHIR Patient resource with:
# - US Core Patient profile compliance
# - Proper identifiers (MRN mapping)
# - Demographics (name, gender, birthDate)
# - Contact information (telecom, address)
# - Extensions for insurance and custom metadata
```

### Appointment Mapping
```python
from fhir_object_mappers import appointment_to_fhir_encounter

# Convert appointment to FHIR Encounter resource
fhir_encounter = appointment_to_fhir_encounter(appointment)

# Result: FHIR Encounter resource with:
# - Status mapping (OOO→planned, provider→in-progress, seen→finished)
# - Ambulatory encounter class
# - Proper period timing (start from appointment datetime)
# - Patient reference and service provider information
```

### Document Mapping
```python
from fhir_object_mappers import document_to_fhir_document_reference

# Convert document to FHIR DocumentReference resource
fhir_doc_ref = document_to_fhir_document_reference(document)

# Result: FHIR DocumentReference resource with:
# - Document type mapping (Lab Report→11502-2, Radiology→18748-4)
# - Category classification (laboratory, imaging, exam)
# - Content attachment with proper MIME types
# - Preserved FHIR metadata from enhanced parser
```

## Integration with Prep Sheet Logic

### Enhanced Prep Sheet Generation
```python
from fhir_prep_sheet_integration import generate_fhir_prep_sheet

# Generate FHIR-compliant prep sheet
prep_sheet_bundle = generate_fhir_prep_sheet(patient, appointment_date)

# Result: Complete FHIR Bundle containing:
# - Patient demographics (FHIR Patient resource)
# - Screening recommendations (FHIR ServiceRequest resources)
# - Recent encounters (FHIR Encounter resources)
# - Active conditions (FHIR Condition resources)
# - Recent vitals (FHIR Observation resources)
# - Immunization history (FHIR Immunization resources)
# - Relevant documents (FHIR DocumentReference resources)
```

### Update Existing Prep Sheet Route
```python
@app.route('/generate_prep_sheet/<int:patient_id>')
def generate_prep_sheet(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointment_date = date.today()
    
    # Use FHIR-compliant prep sheet generation
    fhir_prep_data = generate_fhir_prep_sheet(patient, appointment_date)
    
    # Extract data for template rendering
    prep_data = {
        'patient': extract_patient_from_fhir(fhir_prep_data),
        'screenings': extract_screenings_from_fhir(fhir_prep_data),
        'conditions': extract_conditions_from_fhir(fhir_prep_data),
        'vitals': extract_vitals_from_fhir(fhir_prep_data),
        'documents': extract_documents_from_fhir(fhir_prep_data)
    }
    
    return render_template('prep_sheet.html', **prep_data)
```

## External API Compatibility

### FHIR API Endpoints
```python
# Register FHIR routes in your main app
from fhir_api_routes import register_fhir_routes
register_fhir_routes(app)

# Available endpoints:
# GET /fhir/Patient/{id} - Individual patient
# GET /fhir/Patient/{id}/$everything - Complete patient bundle
# GET /fhir/Patient?name=smith&birthdate=1985-06-15 - Patient search
# GET /fhir/Encounter/{id} - Appointment as encounter
# GET /fhir/DocumentReference/{id} - Document reference
# GET /fhir/Patient/{id}/prep-sheet - FHIR prep sheet bundle
```

### External System Integration
```python
# Export patient data for external EHR systems
from fhir_prep_sheet_integration import export_patient_as_fhir_bundle

# Complete patient export
patient_bundle = export_patient_as_fhir_bundle(
    patient_id=123, 
    include_documents=True
)

# Send to external FHIR server
import requests
response = requests.post(
    'https://external-ehr.com/fhir',
    json=patient_bundle,
    headers={'Content-Type': 'application/fhir+json'}
)
```

## Comprehensive Resource Mapping

### Conditions
```python
from fhir_object_mappers import fhir_mapper

# Map conditions to FHIR Condition resources
for condition in patient.conditions:
    fhir_condition = fhir_mapper.map_condition_to_fhir(condition)
    # Result: FHIR Condition with ICD-10 codes and SNOMED CT mappings
```

### Vital Signs
```python
# Map vitals to FHIR Observation resources
for vital in patient.vitals:
    fhir_observations = fhir_mapper.map_vital_to_fhir_observation(vital)
    # Result: Multiple FHIR Observations (one per vital sign)
    # - Blood pressure as component observation
    # - Individual observations for weight, height, BMI, etc.
    # - Proper LOINC codes for each measurement
```

### Immunizations
```python
# Map immunizations to FHIR Immunization resources
for immunization in patient.immunizations:
    fhir_immunization = fhir_mapper.map_immunization_to_fhir(immunization)
    # Result: FHIR Immunization with CVX vaccine codes
```

## Template Integration

### Enhanced Prep Sheet Template
```html
<!-- templates/prep_sheet_fhir.html -->
<div class="prep-sheet-fhir">
    <div class="patient-header">
        <h2>{{ fhir_patient.name[0].given[0] }} {{ fhir_patient.name[0].family }}</h2>
        <p>MRN: {{ fhir_patient.identifier[0].value }}</p>
        <p>DOB: {{ fhir_patient.birthDate }} ({{ age }} years old)</p>
    </div>
    
    <div class="screening-recommendations">
        <h3>Recommended Screenings</h3>
        {% for screening in fhir_screenings %}
        <div class="screening-item">
            <h5>{{ screening.code.coding[0].display }}</h5>
            <p><strong>LOINC Code:</strong> {{ screening.code.coding[0].code }}</p>
            <p><strong>Priority:</strong> {{ screening.priority|title }}</p>
            <p><strong>Due:</strong> {{ screening.occurrenceDateTime }}</p>
            {% if screening.note %}
            <p><strong>Notes:</strong> {{ screening.note[0].text }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <div class="current-conditions">
        <h3>Active Medical Conditions</h3>
        {% for condition in fhir_conditions %}
        <div class="condition-item">
            <h5>{{ condition.code.text }}</h5>
            <p><strong>Status:</strong> {{ condition.clinicalStatus.coding[0].display }}</p>
            {% if condition.onsetDateTime %}
            <p><strong>Onset:</strong> {{ condition.onsetDateTime }}</p>
            {% endif %}
            {% if condition.code.coding %}
            <p><strong>ICD-10:</strong> {{ condition.code.coding[0].code }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <div class="recent-vitals">
        <h3>Recent Vital Signs</h3>
        {% for observation in fhir_observations %}
        <div class="vital-item">
            <span class="vital-name">{{ observation.code.coding[0].display }}:</span>
            {% if observation.valueQuantity %}
            <span class="vital-value">{{ observation.valueQuantity.value }} {{ observation.valueQuantity.unit }}</span>
            {% elif observation.component %}
            <span class="vital-value">
                {% for comp in observation.component %}
                {{ comp.valueQuantity.value }} {{ comp.valueQuantity.unit }}
                {% if not loop.last %} / {% endif %}
                {% endfor %}
            </span>
            {% endif %}
            <span class="vital-date">({{ observation.effectiveDateTime }})</span>
        </div>
        {% endfor %}
    </div>
</div>
```

## Database Integration

### Store FHIR Resources
```python
# Add FHIR resource storage columns to existing tables
class Patient(db.Model):
    # ... existing fields ...
    fhir_resource = db.Column(db.Text)  # JSON string of FHIR Patient resource
    
    def update_fhir_resource(self):
        """Update stored FHIR resource when patient data changes"""
        self.fhir_resource = json.dumps(patient_to_fhir(self))

class Appointment(db.Model):
    # ... existing fields ...
    fhir_encounter = db.Column(db.Text)  # JSON string of FHIR Encounter resource
    
    def update_fhir_encounter(self):
        """Update stored FHIR encounter when appointment changes"""
        self.fhir_encounter = json.dumps(appointment_to_fhir_encounter(self))
```

### Migration Script
```python
def migrate_to_fhir_resources():
    """Migrate existing data to include FHIR resources"""
    patients = Patient.query.all()
    
    for patient in patients:
        patient.update_fhir_resource()
    
    appointments = Appointment.query.all()
    
    for appointment in appointments:
        appointment.update_fhir_encounter()
    
    db.session.commit()
    print(f"Migrated {len(patients)} patients and {len(appointments)} appointments to FHIR format")
```

## Search and Query Enhancement

### FHIR-Based Patient Search
```python
@app.route('/api/patients/search')
def search_patients_fhir_api():
    search_params = {
        'name': request.args.get('name'),
        'birthdate': request.args.get('birthdate'),
        'identifier': request.args.get('identifier')
    }
    
    # Use FHIR search functionality
    fhir_bundle = search_patients_as_fhir(search_params)
    
    return jsonify(fhir_bundle)
```

### Enhanced Document Search
```python
def search_documents_by_fhir_codes(patient_id, loinc_codes):
    """Search documents using FHIR LOINC codes"""
    documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()
    matching_docs = []
    
    for doc in documents:
        if doc.doc_metadata:
            try:
                metadata = json.loads(doc.doc_metadata)
                if 'fhir_primary_code' in metadata:
                    doc_code = metadata['fhir_primary_code']['code']['coding'][0]['code']
                    if doc_code in loinc_codes:
                        matching_docs.append(document_to_fhir_document_reference(doc))
            except (json.JSONDecodeError, KeyError):
                continue
    
    return matching_docs
```

## Benefits of FHIR Integration

### Standardization
- **Consistent Data Format**: All healthcare data follows FHIR R4 standard
- **Interoperability**: Ready for integration with external EHR systems
- **Coding Systems**: Proper use of LOINC, SNOMED CT, ICD-10, and CVX codes

### Enhanced Functionality
- **Rich Metadata**: Preserved document metadata with FHIR codes
- **Structured Searching**: Search by standardized medical codes
- **Complete Patient View**: Comprehensive bundles with all related data

### External API Ready
- **FHIR Endpoints**: Standard FHIR API for external system integration
- **Search Operations**: FHIR-compliant patient and resource search
- **Data Export**: Complete patient data export in standard format

### Prep Sheet Enhancement
- **Structured Recommendations**: Screening recommendations as FHIR ServiceRequests
- **Organized Sections**: Clear categorization of medical data
- **Standards Compliance**: All prep sheet data follows healthcare standards

## Implementation Steps

1. **Register FHIR Routes**: Add FHIR API endpoints to your application
2. **Update Prep Sheet Logic**: Replace internal prep sheet generation with FHIR-based version
3. **Enhance Templates**: Update templates to display FHIR-structured data
4. **Database Migration**: Add FHIR resource storage columns and migrate existing data
5. **External Integration**: Configure external EHR system connections using FHIR endpoints

Your healthcare application now provides complete FHIR compliance for internal operations and external API compatibility while maintaining all existing functionality with enhanced standardization.