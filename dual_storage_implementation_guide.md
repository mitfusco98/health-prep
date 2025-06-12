# Dual Storage Implementation Guide

## Overview

Your healthcare application now supports dual storage for documents and prep sheets, storing both:
- **Internal keys** (tag, section, matched_screening) - for backward compatibility
- **FHIR-style keys** (code.coding.code, category, effectiveDateTime) - for Epic/FHIR exports

This maintains full backward compatibility while enabling standards-compliant healthcare data exchange.

## Database Schema Changes

### MedicalDocument Table - New Columns Added
```sql
-- Internal keys (backward compatibility)
ALTER TABLE medical_document ADD COLUMN tag VARCHAR(100);
ALTER TABLE medical_document ADD COLUMN section VARCHAR(100);
ALTER TABLE medical_document ADD COLUMN matched_screening VARCHAR(100);

-- FHIR-style keys (Epic/FHIR exports)
ALTER TABLE medical_document ADD COLUMN fhir_code_system VARCHAR(255);
ALTER TABLE medical_document ADD COLUMN fhir_code_code VARCHAR(50);
ALTER TABLE medical_document ADD COLUMN fhir_code_display VARCHAR(255);
ALTER TABLE medical_document ADD COLUMN fhir_category_system VARCHAR(255);
ALTER TABLE medical_document ADD COLUMN fhir_category_code VARCHAR(50);
ALTER TABLE medical_document ADD COLUMN fhir_category_display VARCHAR(255);
ALTER TABLE medical_document ADD COLUMN fhir_effective_datetime TIMESTAMP;
```

### New PrepSheet Table
```sql
CREATE TABLE prep_sheet (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patient(id),
    appointment_date DATE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    content TEXT,
    prep_data TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Internal keys
    tag VARCHAR(100),
    section VARCHAR(100),
    matched_screening VARCHAR(100),
    
    -- FHIR-style keys
    fhir_code_system VARCHAR(255),
    fhir_code_code VARCHAR(50),
    fhir_code_display VARCHAR(255),
    fhir_category_system VARCHAR(255),
    fhir_category_code VARCHAR(50),
    fhir_category_display VARCHAR(255),
    fhir_effective_datetime TIMESTAMP
);
```

## Integration with Existing Routes

### Document Upload Route Enhancement
```python
@app.route('/add_document/<int:patient_id>', methods=['POST'])
def add_document(patient_id):
    # Your existing validation code stays the same
    patient = Patient.query.get_or_404(patient_id)
    
    # Create document as before
    document = MedicalDocument(
        patient_id=patient_id,
        filename=secure_filename(file.filename),
        document_name=form.document_name.data,
        document_type=form.document_type.data,
        content=content,
        document_date=form.document_date.data
    )
    
    # NEW: Use enhanced processor for dual storage
    from enhanced_document_processor import process_document_with_dual_storage
    success = process_document_with_dual_storage(document, user_id=current_user.id)
    
    if success:
        flash('Document uploaded and processed successfully', 'success')
        # Admin logging is automatic
    else:
        flash('Error processing document', 'error')
    
    return redirect(url_for('patient_detail', patient_id=patient_id))
```

### Prep Sheet Generation Enhancement
```python
@app.route('/generate_prep_sheet/<int:patient_id>')
def generate_prep_sheet(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointment_date = request.args.get('date', date.today())
    
    # Your existing prep sheet generation logic
    prep_content = generate_prep_sheet_content(patient, appointment_date)
    
    # NEW: Create PrepSheet record with dual storage
    from models import PrepSheet
    from dual_storage_handler import save_prep_sheet_dual_storage
    
    prep_sheet = PrepSheet(
        patient_id=patient_id,
        appointment_date=appointment_date,
        filename=f"prep_sheet_{patient_id}_{appointment_date}.pdf",
        content=prep_content
    )
    
    # Save with dual storage and admin logging
    success = save_prep_sheet_dual_storage(
        prep_sheet=prep_sheet,
        matched_screening="annual_exam,preventive_care"
    )
    
    if success:
        return send_file(prep_sheet.file_path, as_attachment=True)
    else:
        flash('Error generating prep sheet', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
```

## Backward Compatibility

### Existing Code Continues to Work
```python
# Your existing document queries work unchanged
documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()

# Existing document properties work as before
for doc in documents:
    print(f"Document: {doc.filename}")
    print(f"Type: {doc.document_type}")
    print(f"Content: {doc.content}")
```

### New Dual Storage Features Available
```python
# NEW: Access internal keys
internal_keys = document.get_internal_keys()
# Returns: {'tag': 'lab', 'section': 'laboratory_results', 'matched_screening': 'diabetes'}

# NEW: Access FHIR keys
fhir_keys = document.get_fhir_keys()
# Returns: {
#   'code': {'system': 'http://loinc.org', 'code': '11502-2', 'display': 'Laboratory report'},
#   'category': {'system': '...', 'code': 'laboratory', 'display': 'Laboratory'},
#   'effectiveDateTime': datetime_obj
# }
```

## Search Enhancement

### Search by Internal Keys (Backward Compatible)
```python
# Find documents by internal classification
lab_docs = MedicalDocument.query.filter(MedicalDocument.tag.like('%lab%')).all()
imaging_docs = MedicalDocument.query.filter(MedicalDocument.section == 'imaging_studies').all()
diabetes_docs = MedicalDocument.query.filter(MedicalDocument.matched_screening == 'diabetes').all()
```

### Search by FHIR Keys (New Capability)
```python
# Find documents by FHIR codes
loinc_docs = MedicalDocument.query.filter(MedicalDocument.fhir_code_system == 'http://loinc.org').all()
lab_category = MedicalDocument.query.filter(MedicalDocument.fhir_category_code == 'laboratory').all()

# Search by specific LOINC code
hba1c_docs = MedicalDocument.query.filter(MedicalDocument.fhir_code_code == '4548-4').all()
```

## Admin Logging

### Automatic Logging for Document Operations
Every document and prep sheet save/delete operation is automatically logged with:
- Date and time
- Filename and action type (save/delete)
- User performing the action
- Patient ID and document details
- Both internal and FHIR keys
- IP address and user agent

### View Admin Logs
```python
from admin_log_viewer import admin_logs

# Admin logs show entries like:
# {
#   "action_type": "document_save",
#   "filename": "hba1c_results_2024.pdf",
#   "patient_id": 123,
#   "timestamp": "2024-12-12T10:30:00Z",
#   "internal_keys": {"tag": "lab", "section": "laboratory_results"},
#   "fhir_keys": {"code": {"system": "http://loinc.org", "code": "4548-4"}},
#   "user_id": 1
# }
```

## FHIR Export for Epic Integration

### Document Export to FHIR Format
```python
from fhir_object_mappers import document_to_fhir_document_reference

# Export document as FHIR DocumentReference
fhir_doc_ref = document_to_fhir_document_reference(document)

# Uses stored FHIR keys for proper Epic compatibility
# Result: Complete FHIR DocumentReference with proper LOINC codes
```

### Patient Data Export for External EHRs
```python
from fhir_prep_sheet_integration import export_patient_as_fhir_bundle

# Export complete patient data for Epic/external EHR
fhir_bundle = export_patient_as_fhir_bundle(patient_id=123, include_documents=True)

# Result: Complete FHIR Bundle ready for Epic import
```

## Migration for Existing Data

### Update Existing Documents
```python
from enhanced_document_processor import update_legacy_documents

# Migrate existing documents to dual storage format
stats = update_legacy_documents(batch_size=100)
# Processes existing documents and adds both internal and FHIR keys
```

## Key Benefits

### 1. Backward Compatibility
- All existing code continues to work unchanged
- No breaking changes to current functionality
- Gradual adoption of new features possible

### 2. Standards Compliance
- FHIR R4 compliant document references
- Proper LOINC, SNOMED CT, and ICD-10 coding
- Epic and external EHR integration ready

### 3. Enhanced Search and Organization
- Search by both internal and FHIR classifications
- Better document categorization
- Improved prep sheet tracking

### 4. Comprehensive Audit Trail
- All document operations logged automatically
- Admin compliance for healthcare regulations
- Security monitoring for patient data access

### 5. Future-Proof Architecture
- Ready for healthcare interoperability requirements
- Supports multiple data export formats
- Extensible for additional healthcare standards

## Usage Examples

### Save Document with Automatic Dual Storage
```python
from enhanced_document_processor import process_document_with_dual_storage

# Document automatically gets both internal and FHIR keys
success = process_document_with_dual_storage(document, user_id=current_user.id)
```

### Manual Dual Storage Assignment
```python
from dual_storage_handler import save_document_dual_storage

# Specify both internal and FHIR keys manually
success = save_document_dual_storage(
    document=document,
    tag='lab_diabetes',
    section='laboratory_results',
    matched_screening='diabetes',
    fhir_code={'system': 'http://loinc.org', 'code': '4548-4', 'display': 'Hemoglobin A1c'},
    fhir_category={'system': 'http://terminology.hl7.org/CodeSystem/observation-category', 'code': 'laboratory', 'display': 'Laboratory'}
)
```

### Access Both Key Formats
```python
# Get internal keys (backward compatible)
internal = document.get_internal_keys()
print(f"Tag: {internal['tag']}")

# Get FHIR keys (new functionality)
fhir = document.get_fhir_keys()
print(f"LOINC Code: {fhir['code']['code']}")
```

Your healthcare application now supports dual storage that maintains backward compatibility while enabling Epic and FHIR export capabilities, with comprehensive admin logging for all document and prep sheet operations.