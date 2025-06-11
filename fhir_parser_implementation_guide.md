# FHIR Document Parser Implementation Guide

## Overview

Your document parser has been enhanced to extract tags from filenames and content and return them in the exact FHIR format you specified:

```json
{
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "4548-4",
      "display": "Hemoglobin A1C"
    }]
  }
}
```

## Implementation

### Enhanced Parser Functions

```python
# Main extraction function
from enhanced_parser_integration import extract_tags_from_document

# Extract primary FHIR code
result = extract_tags_from_document(content, filename)
# Returns: { 'code': { 'coding': [{ 'system': '...', 'code': '...', 'display': '...' }] } }

# Get all FHIR codes found
from enhanced_parser_integration import get_all_document_codes
all_codes = get_all_document_codes(content, filename)
# Returns: List of FHIR code dictionaries

# Complete document analysis
from enhanced_parser_integration import enhanced_classify_document
analysis = enhanced_classify_document(content, filename)
```

## Supported Extractions

### Lab Tests (LOINC Codes)

| Pattern | LOINC Code | Display Name |
|---------|------------|--------------|
| `hemoglobin a1c`, `hba1c` | 4548-4 | Hemoglobin A1c/Hemoglobin.total in Blood |
| `complete blood count`, `cbc` | 58410-2 | Complete blood count (hemogram) panel |
| `basic metabolic panel`, `bmp` | 51990-0 | Basic metabolic panel - Blood |
| `comprehensive metabolic panel`, `cmp` | 24323-8 | Comprehensive metabolic panel - Blood |
| `lipid panel`, `cholesterol panel` | 57698-3 | Lipid panel with direct LDL |
| `thyroid stimulating hormone`, `tsh` | 3016-3 | Thyrotropin [Units/volume] in Serum |
| `glucose`, `blood sugar` | 2339-0 | Glucose [Mass/volume] in Blood |
| `creatinine` | 2160-0 | Creatinine [Mass/volume] in Serum |

### Imaging Studies (LOINC Codes)

| Pattern | LOINC Code | Display Name |
|---------|------------|--------------|
| `chest x-ray`, `chest radiograph` | 36643-5 | Chest X-ray |
| `ct scan`, `computed tomography` | 18748-4 | Diagnostic imaging study |
| `mri`, `magnetic resonance` | 18755-9 | MR study |
| `ultrasound`, `sonogram` | 18760-9 | Ultrasound study |

### Clinical Documents (LOINC Codes)

| Pattern | LOINC Code | Display Name |
|---------|------------|--------------|
| `discharge summary` | 18842-5 | Discharge summary |
| `progress note` | 11506-3 | Progress note |
| `consultation note`, `consult` | 11488-4 | Consultation note |

## Usage Examples

### Example 1: HbA1c Lab Result

```python
content = "Laboratory results show elevated Hemoglobin A1C at 7.2%"
filename = "hba1c_lab_results_2024.pdf"

result = extract_tags_from_document(content, filename)
print(result)
```

Output:
```json
{
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "4548-4",
      "display": "Hemoglobin A1c/Hemoglobin.total in Blood"
    }]
  }
}
```

### Example 2: Chest X-ray Report

```python
content = "Chest X-ray demonstrates clear lung fields"
filename = "chest_xray_pa_lateral.pdf"

result = extract_tags_from_document(content, filename)
print(result)
```

Output:
```json
{
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "36643-5",
      "display": "Chest X-ray"
    }]
  }
}
```

### Example 3: Multiple Lab Tests

```python
content = """
Complete Blood Count (CBC) results:
- Hemoglobin: 14.2 g/dL
Basic Metabolic Panel (BMP):
- Glucose: 98 mg/dL
"""

all_codes = get_all_document_codes(content)
for code_info in all_codes:
    coding = code_info['code']['coding'][0]
    print(f"{coding['display']} ({coding['code']})")
```

Output:
```
Complete blood count (hemogram) panel (58410-2)
Basic metabolic panel - Blood (51990-0)
```

## Integration with Existing Code

### Replace Your Current DocumentClassifier

```python
# Old way
from utils import classify_document
doc_type, metadata = classify_document(content, filename)

# New way with FHIR codes
from enhanced_parser_integration import enhanced_classify_document
result = enhanced_classify_document(content, filename)

# Access the data
document_type = result['document_type']
primary_fhir_code = result['primary_fhir_code']
all_fhir_codes = result['all_fhir_codes']
```

### Update Document Upload Process

```python
# In your document upload route
def upload_document():
    # ... existing upload logic ...
    
    # Extract FHIR codes from document
    fhir_codes = extract_tags_from_document(content, filename)
    
    # Store in document metadata
    document.doc_metadata = json.dumps({
        'fhir_primary_code': fhir_codes,
        'extracted_at': datetime.utcnow().isoformat()
    })
    
    db.session.commit()
```

### Search Documents by FHIR Codes

```python
def search_documents_by_loinc_code(loinc_code):
    """Search documents by specific LOINC code"""
    documents = MedicalDocument.query.all()
    matching_docs = []
    
    for doc in documents:
        if doc.doc_metadata:
            metadata = json.loads(doc.doc_metadata)
            fhir_code = metadata.get('fhir_primary_code', {})
            if fhir_code.get('code', {}).get('coding', [{}])[0].get('code') == loinc_code:
                matching_docs.append(doc)
    
    return matching_docs

# Usage
hba1c_documents = search_documents_by_loinc_code('4548-4')
```

## Template Integration

### Display FHIR Codes in Document Lists

```html
<!-- In your document list template -->
{% for document in documents %}
<div class="document-item">
    <h5>{{ document.document_name }}</h5>
    
    {% if document.doc_metadata %}
        {% set metadata = document.doc_metadata | fromjson %}
        {% if metadata.fhir_primary_code %}
            {% set coding = metadata.fhir_primary_code.code.coding[0] %}
            <span class="badge badge-info">
                {{ coding.display }}
            </span>
            <small class="text-muted">
                LOINC: {{ coding.code }}
            </small>
        {% endif %}
    {% endif %}
    
    <p>{{ document.filename }}</p>
</div>
{% endfor %}
```

## Migration Strategy

### Step 1: Update Existing Documents

```python
def migrate_existing_documents():
    """Add FHIR codes to existing documents"""
    from enhanced_parser_integration import extract_tags_from_document
    
    documents = MedicalDocument.query.all()
    
    for doc in documents:
        if doc.content or doc.filename:
            # Extract FHIR codes
            fhir_codes = extract_tags_from_document(
                doc.content or "", 
                doc.filename
            )
            
            # Update metadata
            existing_metadata = {}
            if doc.doc_metadata:
                existing_metadata = json.loads(doc.doc_metadata)
            
            existing_metadata['fhir_primary_code'] = fhir_codes
            existing_metadata['fhir_migration_date'] = datetime.utcnow().isoformat()
            
            doc.doc_metadata = json.dumps(existing_metadata)
    
    db.session.commit()
    print(f"Migrated {len(documents)} documents with FHIR codes")
```

### Step 2: Update Upload Routes

Replace calls to your existing `classify_document` function with the new FHIR-enabled version.

### Step 3: Update Search and Filter Functions

Add FHIR code-based search capabilities to your document management system.

## Benefits

1. **Standards Compliance**: Uses official LOINC codes for medical terminology
2. **Interoperability**: Ready for healthcare system integrations
3. **Structured Search**: Filter documents by specific medical codes
4. **Future-Proof**: Extensible for additional FHIR resource types
5. **Backward Compatible**: Works alongside existing document classification

## Configuration

### Adding New Patterns

To add new extraction patterns, update the pattern dictionaries in `enhanced_parser_integration.py`:

```python
# Add new lab test
self.lab_patterns[r'vitamin\s+d'] = {
    'system': 'http://loinc.org',
    'code': '25-hydroxyvitamin-d-code',
    'display': 'Vitamin D [25(OH)D] measurement'
}
```

### Custom FHIR Systems

You can also use other coding systems:

```python
# SNOMED CT example
{
    'system': 'http://snomed.info/sct',
    'code': '123456789',
    'display': 'Custom medical concept'
}
```

Your document parser now extracts tags in the exact FHIR format requested and provides a complete foundation for standards-based medical document processing.