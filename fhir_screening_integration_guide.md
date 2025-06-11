# FHIR Screening Types Configuration Integration Guide

## Overview

Your screening_types configuration has been updated to support:
- Manual keywords for flexible searching
- Document sections (labs, imaging, consults, vitals, immunizations, assessments, procedures, medications)
- LOINC/CPT codes with proper FHIR field naming
- Category mapping to FHIR observation categories
- FHIR ServiceRequest generation

## Configuration Structure

### FHIR-Compliant Screening Definition

```python
"screening_name": {
    "code": {
        "coding": [{
            "system": "http://loinc.org",
            "code": "4548-4",
            "display": "Hemoglobin A1c/Hemoglobin.total in Blood"
        }]
    },
    "category": [{
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "laboratory",
            "display": "Laboratory"
        }]
    }],
    "type": {
        "coding": [{
            "system": "http://loinc.org",
            "code": "4548-4",
            "display": "HbA1c measurement"
        }]
    },
    "manual_keywords": ["a1c", "hba1c", "hemoglobin a1c", "glycated hemoglobin"],
    "document_section": "labs",
    "priority": "high",
    "frequency": "3_months"
}
```

## Document Sections with FHIR Categories

| Section | FHIR Category | Type Code | Description |
|---------|---------------|-----------|-------------|
| `labs` | laboratory | LAB | Laboratory tests and results |
| `imaging` | imaging | RAD | Radiology and imaging studies |
| `procedures` | procedure | PROC | Medical procedures |
| `vitals` | vital-signs | VITAL | Vital signs measurements |
| `immunizations` | therapy | IMM | Vaccines and immunizations |
| `assessments` | survey | ASSESS | Clinical assessments and questionnaires |
| `consults` | exam | CONSULT | Consultation reports |
| `medications` | therapy | MED | Medication management |

## Available Functions

### Search by Keywords

```python
from screening_rules import get_screening_by_keyword

# Search for screening by manual keyword
result = get_screening_by_keyword("mammogram")
# Returns: {"id": "mammogram", "config": {...}}

result = get_screening_by_keyword("cholesterol")
# Returns: {"id": "lipid_panel", "config": {...}}
```

### Search by LOINC/CPT Codes

```python
from screening_rules import get_screening_by_loinc_code

# Find screening by LOINC code
result = get_screening_by_loinc_code("4548-4")  # HbA1c
# Returns: {"id": "hba1c", "config": {...}}

result = get_screening_by_loinc_code("24604-1")  # Mammography
# Returns: {"id": "mammogram", "config": {...}}
```

### Filter by Document Section

```python
from screening_rules import get_screenings_by_document_section

# Get all lab-related screenings
lab_screenings = get_screenings_by_document_section("labs")
# Returns: [{"id": "hba1c", "config": {...}}, {"id": "lipid_panel", "config": {...}}, ...]

# Get all imaging screenings
imaging_screenings = get_screenings_by_document_section("imaging")
# Returns: [{"id": "mammogram", "config": {...}}, {"id": "bone_density", "config": {...}}, ...]
```

### Generate FHIR ServiceRequests

```python
from screening_rules import create_fhir_screening_recommendation
from datetime import datetime

# Create FHIR ServiceRequest for a specific screening
mammogram_config = SCREENING_TYPES_CONFIG["mammogram"]
service_request = create_fhir_screening_recommendation(
    mammogram_config,
    "patient-123",
    datetime.now().date()
)
# Returns complete FHIR ServiceRequest resource
```

## Complete LOINC/CPT Code Mapping

### Laboratory Tests (Section: `labs`)

| Screening | LOINC Code | Display Name | Keywords |
|-----------|------------|--------------|----------|
| HbA1c | 4548-4 | Hemoglobin A1c/Hemoglobin.total in Blood | a1c, hba1c, hemoglobin a1c |
| Lipid Panel | 57698-3 | Lipid panel with direct LDL | lipid panel, cholesterol, hdl, ldl |
| PSA Test | 2857-1 | Prostate specific antigen | psa, prostate specific antigen |
| Pap Test | 10524-7 | Cervical or vaginal smear | pap test, pap smear, cervical screening |
| Hepatitis C | 13955-0 | Hepatitis C virus Ab | hepatitis c, hcv, hep c screening |

### Imaging Studies (Section: `imaging`)

| Screening | LOINC Code | Display Name | Keywords |
|-----------|------------|--------------|----------|
| Mammogram | 24604-1 | Mammography study | mammogram, mammography, breast imaging |
| Bone Density | 38269-7 | DXA scan | bone density, dexa scan, dxa |
| CT Lung | 30621-7 | CT Chest | low dose ct, lung screening, ct chest |
| AAA Ultrasound | 45036-0 | Abdominal aorta Ultrasound | abdominal ultrasound, aaa screening |

### Procedures (Section: `procedures`)

| Screening | LOINC Code | Display Name | Keywords |
|-----------|------------|--------------|----------|
| Colorectal | 45398-4 | Colonoscopy study | colonoscopy, fit test, cologuard |

### Vital Signs (Section: `vitals`)

| Screening | LOINC Code | Display Name | Keywords |
|-----------|------------|--------------|----------|
| Blood Pressure | 85354-9 | Blood pressure panel | blood pressure, bp, hypertension screening |

### Immunizations (Section: `immunizations`)

| Screening | CVX Code | Display Name | Keywords |
|-----------|----------|--------------|----------|
| Influenza | 141 | Influenza, seasonal, injectable | flu shot, influenza vaccine |
| Shingles | 187 | Zoster vaccine recombinant | shingles vaccine, zoster vaccine |
| Pneumococcal | 133 | Pneumococcal conjugate PCV 13 | pneumonia vaccine, pneumococcal vaccine |

### Assessments (Section: `assessments`)

| Screening | LOINC Code | Display Name | Keywords |
|-----------|------------|--------------|----------|
| Depression | 44249-1 | PHQ-9 quick depression assessment | depression screening, phq9 |

## Integration with Existing Routes

### Update Screening List Route

```python
from screening_rules import SCREENING_TYPES_CONFIG, get_screenings_by_document_section

@app.route('/screening_list')
def screening_list():
    # Get screenings by section for organized display
    sections = {
        'Laboratory Tests': get_screenings_by_document_section('labs'),
        'Imaging Studies': get_screenings_by_document_section('imaging'),
        'Procedures': get_screenings_by_document_section('procedures'),
        'Vital Signs': get_screenings_by_document_section('vitals'),
        'Immunizations': get_screenings_by_document_section('immunizations'),
        'Assessments': get_screenings_by_document_section('assessments')
    }
    
    return render_template('screening_list.html', sections=sections)
```

### Add Keyword Search Route

```python
from screening_rules import get_screening_by_keyword

@app.route('/search_screening')
def search_screening():
    keyword = request.args.get('keyword', '')
    
    if keyword:
        result = get_screening_by_keyword(keyword)
        if result:
            return jsonify({
                'success': True,
                'screening': result,
                'fhir_code': result['config']['code']
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No screening found for keyword: {keyword}'
            })
    
    return jsonify({'success': False, 'message': 'Keyword required'})
```

### Update Patient Screening Recommendations

```python
from screening_rules import apply_screening_rules, get_screening_recommendations_by_section

@app.route('/patient_screening_recommendations/<int:patient_id>')
def patient_screening_recommendations(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Get patient conditions
    condition_names = [condition.condition_name.lower() for condition in patient.conditions]
    
    # Get all FHIR-compliant recommendations
    recommendations = apply_screening_rules(patient, condition_names)
    
    # Group by document section
    sections = {}
    for rec in recommendations:
        # Get document section from screening config
        section = None
        for screening_id, config in SCREENING_TYPES_CONFIG.items():
            if config['code']['coding'][0]['code'] == rec['code']['coding'][0]['code']:
                section = config['document_section']
                break
        
        if section:
            if section not in sections:
                sections[section] = []
            sections[section].append(rec)
    
    return render_template('patient_screening_recommendations.html', 
                         patient=patient, 
                         sections=sections)
```

## Template Updates

### Enhanced Screening List Template

```html
<!-- templates/screening_list.html -->
<div class="screening-sections">
    {% for section_name, screenings in sections.items() %}
    <div class="screening-section">
        <h3>{{ section_name }}</h3>
        
        {% for screening in screenings %}
        {% set config = screening.config %}
        {% set coding = config.code.coding[0] %}
        
        <div class="screening-item">
            <div class="screening-header">
                <h5>{{ coding.display }}</h5>
                <span class="badge badge-{{ config.priority }}">{{ config.priority|title }}</span>
            </div>
            
            <div class="screening-details">
                <p><strong>LOINC/Code:</strong> {{ coding.code }}</p>
                <p><strong>System:</strong> {{ coding.system }}</p>
                <p><strong>Keywords:</strong> {{ config.manual_keywords|join(', ') }}</p>
                <p><strong>Frequency:</strong> {{ config.frequency|replace('_', ' ')|title }}</p>
                <p><strong>Section:</strong> {{ config.document_section|title }}</p>
            </div>
            
            <div class="fhir-category">
                {% set category = config.category[0].coding[0] %}
                <small class="text-muted">
                    FHIR Category: {{ category.display }} ({{ category.code }})
                </small>
            </div>
        </div>
        {% endfor %}
    </div>
    {% endfor %}
</div>
```

### Patient Recommendations Template

```html
<!-- templates/patient_screening_recommendations.html -->
<div class="patient-recommendations">
    <h2>Screening Recommendations for {{ patient.first_name }} {{ patient.last_name }}</h2>
    
    {% for section_name, recommendations in sections.items() %}
    <div class="recommendation-section">
        <h4>{{ section_name|title }} Screenings</h4>
        
        {% for rec in recommendations %}
        {% set coding = rec.code.coding[0] %}
        
        <div class="fhir-service-request">
            <div class="service-request-header">
                <h6>{{ coding.display }}</h6>
                <span class="badge badge-{{ rec.priority }}">{{ rec.priority|title }}</span>
            </div>
            
            <div class="service-request-details">
                <p><strong>LOINC Code:</strong> {{ coding.code }}</p>
                <p><strong>Due Date:</strong> {{ rec.occurrenceDateTime }}</p>
                <p><strong>Status:</strong> {{ rec.status|title }}</p>
                <p><strong>Intent:</strong> {{ rec.intent|title }}</p>
                
                {% if rec.note %}
                <p><strong>Notes:</strong> {{ rec.note[0].text }}</p>
                {% endif %}
            </div>
            
            <div class="fhir-metadata">
                <small class="text-muted">
                    Resource Type: {{ rec.resourceType }} | 
                    Patient: {{ rec.subject.reference }}
                </small>
            </div>
        </div>
        {% endfor %}
    </div>
    {% endfor %}
</div>
```

## Search Integration

### JavaScript for Dynamic Screening Search

```javascript
// Static search functionality
function searchScreenings() {
    const keyword = document.getElementById('screening-search').value;
    
    if (keyword.length < 2) return;
    
    fetch(`/search_screening?keyword=${encodeURIComponent(keyword)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayScreeningResult(data.screening);
            } else {
                displayNoResults(data.message);
            }
        })
        .catch(error => {
            console.error('Search error:', error);
        });
}

function displayScreeningResult(screening) {
    const config = screening.config;
    const coding = config.code.coding[0];
    
    const resultHtml = `
        <div class="search-result">
            <h5>${coding.display}</h5>
            <p><strong>LOINC Code:</strong> ${coding.code}</p>
            <p><strong>Keywords:</strong> ${config.manual_keywords.join(', ')}</p>
            <p><strong>Section:</strong> ${config.document_section}</p>
            <p><strong>Priority:</strong> ${config.priority}</p>
        </div>
    `;
    
    document.getElementById('search-results').innerHTML = resultHtml;
}
```

## Migration Guide

### Step 1: Update Existing Screening Routes

Replace calls to old screening functions with new FHIR-compliant versions:

```python
# Old way
from some_old_module import get_screenings

# New way
from screening_rules import (
    get_screening_by_keyword,
    get_screenings_by_document_section,
    apply_screening_rules
)
```

### Step 2: Update Database Schema (Optional)

Add FHIR metadata columns to screening tables:

```sql
ALTER TABLE screening_recommendations 
ADD COLUMN fhir_service_request TEXT,
ADD COLUMN loinc_code VARCHAR(20),
ADD COLUMN document_section VARCHAR(50);
```

### Step 3: Migrate Existing Data

```python
def migrate_screening_data():
    """Migrate existing screening data to FHIR format"""
    from screening_rules import SCREENING_TYPES_CONFIG
    
    # Update existing screening recommendations
    screenings = ScreeningRecommendation.query.all()
    
    for screening in screenings:
        # Try to match with new config
        for screening_id, config in SCREENING_TYPES_CONFIG.items():
            if any(keyword in screening.type.lower() for keyword in config['manual_keywords']):
                screening.loinc_code = config['code']['coding'][0]['code']
                screening.document_section = config['document_section']
                break
    
    db.session.commit()
```

Your screening_types configuration now provides complete FHIR compliance with manual keywords, document section organization, and standardized LOINC/CPT code mapping for comprehensive healthcare data interoperability.