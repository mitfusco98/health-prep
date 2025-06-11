# FHIR DocumentReference Mapping Implementation Guide

## Overview

Your medical documents are now fully convertible to FHIR R4 DocumentReference resources. This enables seamless integration with healthcare systems for document sharing, clinical data exchange, and comprehensive patient record management.

## Field Mapping

| Internal Document Field | FHIR DocumentReference Field | Mapping Details |
|---|---|---|
| `id` | `identifier.value` | Document ID as official identifier |
| `patient_id` | `subject.reference` | Patient/{patient_id} reference |
| `filename` | `content.attachment.title` | Original filename as title |
| `document_name` | `content.attachment.title` | Preferred over filename if available |
| `document_type` | `type.coding` | Maps to LOINC codes for document types |
| `mime_type` | `content.attachment.contentType` | MIME type for content format |
| `document_date` | `date` | Document creation/authoring date |
| `provider` | `author.display` | Document author/provider |
| `source_system` | `authenticator.display` | Source EHR/system |
| `is_processed` | `docStatus` | preliminary/final based on processing |
| `doc_metadata` | `extension` | Custom extension for metadata |
| `created_at` | `content.attachment.creation` | File creation timestamp |
| `updated_at` | `meta.lastUpdated` | FHIR metadata |

## Document Type Mapping

Your document types automatically map to standard LOINC codes:

- **Lab Results** → Laboratory report (11502-2)
- **Imaging** → Diagnostic imaging study (18748-4)
- **Progress Notes** → Progress note (11506-3)
- **Discharge Summary** → Discharge summary (18842-5)
- **Consultation** → Consultation note (11488-4)
- **Operative Note** → Surgical operation note (11504-8)
- **Pathology** → Pathology study (11526-1)
- **Radiology** → Radiology studies (18726-0)
- **Other** → Summarization of episode note (34133-9)

## Document Categories

Documents are automatically categorized:

- **Lab Results** → Laboratory
- **Imaging, Radiology** → Imaging
- **All Others** → Clinical Note

## Usage Examples

### Basic Conversion
```python
from fhir_utils import document_to_fhir

document = MedicalDocument.query.get(document_id)
fhir_document_ref = document_to_fhir(document)
```

### API Integration
```python
from fhir_utils import add_fhir_routes
add_fhir_routes(app)

# This creates these endpoints:
# GET /fhir/DocumentReference/{id} - Single document as FHIR DocumentReference
# GET /fhir/DocumentReference?subject=Patient/{id} - Patient's documents
# GET /fhir/DocumentReference?type=Lab%20Results - Documents by type
# GET /fhir/DocumentReference?date=2024-06-15 - Documents by date
```

### Bulk Export
```python
from fhir_utils import create_document_bundle

documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()
document_bundle = create_document_bundle(documents)
```

## Example FHIR Output

```json
{
  "resourceType": "DocumentReference",
  "id": "789",
  "status": "current",
  "docStatus": "final",
  "type": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "11502-2",
      "display": "Laboratory report"
    }],
    "text": "Lab Results"
  },
  "category": [{
    "coding": [{
      "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
      "code": "laboratory",
      "display": "Laboratory"
    }]
  }],
  "subject": {
    "reference": "Patient/12345",
    "display": "Patient 12345"
  },
  "date": "2024-06-15T10:30:00Z",
  "author": [{
    "display": "Dr. Sarah Johnson"
  }],
  "content": [{
    "attachment": {
      "contentType": "application/pdf",
      "title": "CBC Lab Results",
      "url": "http://your-organization.com/documents/789",
      "size": 53,
      "creation": "2024-06-15T10:30:00Z"
    }
  }]
}
```

## Binary vs Text Documents

The mapper handles both binary and text documents:

- **Binary Documents** (PDFs, images): Uses `content.attachment.contentType` and `size`
- **Text Documents**: Uses `content.attachment.contentType` as "text/plain"
- **URL Reference**: Constructs document access URL automatically

## Standards Compliance

- **FHIR Version**: R4 (4.0.1)
- **Resource Type**: DocumentReference
- **Coding Systems**: LOINC for document types, US Core for categories
- **Extensions**: Custom extensions for internal metadata
- **Content Format**: IHE format codes for attachment types

## Integration Benefits

1. **Document Sharing**: Enable document exchange with other healthcare systems
2. **Clinical Context**: Provide document metadata for better care coordination
3. **Audit Trail**: Track document access and modifications through FHIR
4. **Interoperability**: Standard format for EHR integrations
5. **Search Capability**: FHIR-based document search and filtering