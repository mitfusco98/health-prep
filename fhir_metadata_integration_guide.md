# FHIR-Style Document Metadata Integration Guide

## Overview

Your document metadata now supports FHIR-style field structures while keeping all existing database fields unchanged. The system stores FHIR metadata in your existing `doc_metadata` JSON field using standard patterns:

- `code.coding.code` - Primary document codes
- `code.coding.system` - Coding system URLs (LOINC, SNOMED CT)
- `type.coding.display` - Human-readable document types
- `effectiveDateTime` - When document becomes effective
- `category` - Document categories for organization

## Quick Integration

### 1. Enhance Document on Upload

```python
from document_fhir_helpers import enhance_document_on_upload

# In your document upload route
document = MedicalDocument(...)
form_data = {
    'test_type': 'CBC',
    'lab_id': 'LAB-2024-001',
    'lab_status': 'final'
}
enhance_document_on_upload(document, form_data)
db.session.commit()
```

### 2. Add FHIR Codes to Existing Documents

```python
from document_fhir_helpers import add_fhir_coding_to_document

document = MedicalDocument.query.get(document_id)
add_fhir_coding_to_document(
    document,
    code_system="http://loinc.org",
    code="11502-2",
    display="Laboratory report",
    coding_type="type"
)
```

### 3. Set Effective DateTime

```python
from document_fhir_helpers import set_document_effective_datetime

document = MedicalDocument.query.get(document_id)
set_document_effective_datetime(document, datetime(2024, 7, 1, 14, 30))
```

## Document Type Mappings

### Lab Results
- **FHIR Code**: Maps to specific LOINC codes (CBC→58410-2, BMP→51990-0)
- **FHIR Type**: Laboratory report (11502-2)
- **FHIR Category**: Laboratory
- **Extensions**: test_type, lab_id, status, reference_range

### Imaging Studies
- **FHIR Code**: Maps by modality (CT→18748-4, XRAY→18726-0)
- **FHIR Type**: Diagnostic imaging study (18748-4)
- **FHIR Category**: Imaging
- **Extensions**: modality, body_part, study_type, contrast_used

### Clinical Notes
- **FHIR Code**: Maps by note type (Progress→11506-3, Consultation→11488-4)
- **FHIR Type**: Varies by note type
- **FHIR Category**: Clinical Note
- **Extensions**: specialty, encounter_type, chief_complaint

## Metadata Structure Example

Your `doc_metadata` field now contains:

```json
{
  "fhir": {
    "code": {
      "coding": [{
        "system": "http://loinc.org",
        "code": "58410-2",
        "display": "Complete blood count (hemogram) panel - Blood by Automated count"
      }],
      "text": "CBC Lab Test"
    },
    "type": {
      "coding": [{
        "system": "http://loinc.org",
        "code": "11502-2",
        "display": "Laboratory report"
      }],
      "text": "Lab Results"
    },
    "category": {
      "coding": [{
        "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
        "code": "laboratory",
        "display": "Laboratory"
      }]
    },
    "effectiveDateTime": "2024-06-15T10:30:00",
    "extensions": {
      "test_type": "CBC",
      "lab_id": "LAB-2024-001",
      "status": "final",
      "provider": "Dr. Smith"
    }
  },
  "legacy": {
    "existing_field": "existing_value"
  }
}
```

## Search and Filter Functions

### Get FHIR Codes from Document

```python
from document_fhir_helpers import get_document_fhir_codes

codes = get_document_fhir_codes(document)
# Returns: {"code": [...], "type": [...], "category": [...]}
```

### Search Documents by FHIR Metadata

```python
from document_upload_with_fhir import search_documents_by_fhir_metadata

# Search lab results with specific test type
documents = search_documents_by_fhir_metadata(
    patient_id=123,
    filters={'test_type': 'CBC', 'type_code': '11502-2'}
)
```

### Get Display-Ready Metadata

```python
from document_fhir_helpers import get_document_display_metadata

display_data = get_document_display_metadata(document)
# Returns formatted metadata for UI display
```

## Form Integration

Your upload forms can now include FHIR-specific fields:

```html
<!-- Lab Results Fields -->
<div id="lab-fields">
    <select name="lab_test_type">
        <option value="CBC">Complete Blood Count</option>
        <option value="BMP">Basic Metabolic Panel</option>
        <option value="Lipid Panel">Lipid Panel</option>
    </select>
    
    <input name="lab_id" placeholder="LAB-2024-001">
    
    <select name="lab_status">
        <option value="final">Final</option>
        <option value="preliminary">Preliminary</option>
    </select>
</div>

<!-- Imaging Fields -->
<div id="imaging-fields">
    <select name="imaging_modality">
        <option value="XRAY">X-Ray</option>
        <option value="CT">CT Scan</option>
        <option value="MRI">MRI</option>
    </select>
    
    <input name="body_part" placeholder="Chest, Head, etc.">
</div>
```

## Enhanced Document Model Methods

Add these convenience methods to your MedicalDocument model:

```python
# In models.py, add to MedicalDocument class:

def get_fhir_type_display(self):
    """Get FHIR type display text"""
    from document_fhir_helpers import get_fhir_type_display
    return get_fhir_type_display(self)

def get_fhir_category_display(self):
    """Get FHIR category display text"""
    from document_fhir_helpers import get_fhir_category_display
    return get_fhir_category_display(self)

def has_fhir_metadata(self):
    """Check if document has FHIR metadata"""
    from document_fhir_helpers import has_fhir_metadata
    return has_fhir_metadata(self)

def get_fhir_summary(self):
    """Get FHIR metadata summary for display"""
    from document_upload_with_fhir import get_document_fhir_summary
    return get_document_fhir_summary(self)
```

## Migration for Existing Documents

Enhance existing documents with FHIR metadata:

```python
from document_fhir_helpers import bulk_enhance_existing_documents

# Enhance all documents for a patient
documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()
results = bulk_enhance_existing_documents(documents)
db.session.commit()

print(f"Enhanced: {results['enhanced']}")
print(f"Skipped: {results['skipped']}")
print(f"Errors: {results['errors']}")
```

## Benefits of FHIR-Style Metadata

1. **Standards Compliance**: Uses LOINC, SNOMED CT, and HL7 coding systems
2. **Interoperability**: Ready for healthcare system integrations
3. **Structured Search**: Filter documents by FHIR codes and categories
4. **Future-Proof**: Extensible metadata structure
5. **Backward Compatible**: All existing fields and data preserved

## Template Integration

In your Jinja2 templates:

```html
<!-- Display FHIR metadata in document lists -->
{% if document.has_fhir_metadata() %}
    <span class="badge badge-info">
        {{ document.get_fhir_type_display() }}
    </span>
    <small class="text-muted">
        Category: {{ document.get_fhir_category_display() }}
    </small>
{% endif %}

<!-- Show FHIR summary -->
{% set fhir_summary = document.get_fhir_summary() %}
{% if fhir_summary.has_fhir %}
    <div class="fhir-metadata">
        {% if fhir_summary.test_type %}
            <span>Test: {{ fhir_summary.test_type }}</span>
        {% endif %}
        {% if fhir_summary.modality %}
            <span>Modality: {{ fhir_summary.modality }}</span>
        {% endif %}
        {% if fhir_summary.specialty %}
            <span>Specialty: {{ fhir_summary.specialty }}</span>
        {% endif %}
    </div>
{% endif %}
```

## Implementation Checklist

- [ ] Add FHIR metadata to new document uploads using `enhance_document_on_upload()`
- [ ] Update upload forms with FHIR-specific fields
- [ ] Add convenience methods to MedicalDocument model
- [ ] Enhance existing documents with `bulk_enhance_existing_documents()`
- [ ] Update document display templates to show FHIR metadata
- [ ] Implement FHIR-based search and filtering
- [ ] Test FHIR metadata structure compliance

Your documents now have rich, standardized metadata while maintaining complete backward compatibility with existing data and workflows.