# ScreeningType Dynamic Parsing Guide

## Overview
The ScreeningType model now stores all required fields for dynamic prep sheet parsing. The `match_document_to_screening()` function uses these fields to intelligently match medical documents to appropriate screening types.

## Enhanced ScreeningType Fields

### Core Matching Fields
- **content_keywords**: JSON array for document content parsing
- **document_keywords**: JSON array for document type/section parsing  
- **filename_keywords**: JSON array for filename parsing
- **trigger_conditions**: JSON array of FHIR condition codes
- **status**: Screening status (active/inactive/draft)

### Demographic Fields
- **frequency_number** + **frequency_unit**: Structured frequency (e.g., 1 years, 6 months)
- **min_age**, **max_age**: Age range criteria
- **gender_specific**: Gender requirements (Male/Female/None)

## Parsing Logic Flow

### 1. Demographics Filter
Uses conditions, gender, and age to filter applicable screenings:
```python
# Age filtering
if patient.age < screening_type.min_age:
    return demographic_mismatch

# Gender filtering  
if patient.sex != screening_type.gender_specific:
    return demographic_mismatch
```

### 2. Filename Matching
Matches filename_keywords in document name:
```python
filename_keywords = ["mammo", "breast", "mammography"]
if any(keyword in document.filename.lower() for keyword in filename_keywords):
    return matched_filename
```

### 3. Content Matching
Matches keywords in document content:
```python
content_keywords = ["mammogram", "breast imaging", "bilateral mammography"]
if any(keyword in document.content.lower() for keyword in content_keywords):
    return matched_content
```

### 4. Section Matching
Matches document.section with screening_type document keywords:
```python
document_keywords = ["radiology", "imaging"]
if document.section.lower() in [kw.lower() for kw in document_keywords]:
    return matched_section
```

## Return Format

The function returns a standardized result:
```python
{
    'matched': True/False,
    'match_method': 'content' | 'filename' | 'keywords',
    'document_id': int,
    'notes': 'Detailed explanation',
    'status': 'matched_content' | 'demographic_mismatch' | 'no_keyword_match'
}
```

## Example Screening Configuration

### Mammography Screening
```python
{
    'name': 'Mammography Screening',
    'min_age': 40,
    'max_age': 75, 
    'gender_specific': 'Female',
    'frequency_number': 1,
    'frequency_unit': 'years',
    'content_keywords': [
        'mammogram', 'breast imaging', 'breast cancer screening', 
        'bilateral mammography', 'bi-rads'
    ],
    'filename_keywords': [
        'mammo', 'breast', 'mammography'
    ],
    'document_keywords': [
        'radiology', 'imaging', 'breast imaging'
    ]
}
```

### Matching Example
Document: `mammography_bilateral_2024.pdf`
Patient: 45-year-old Female

1. Demographics: ✓ (age 45 in range 40-75, gender Female matches)
2. Filename: ✓ (contains "mammography") 
3. Result: `matched=True, match_method='filename', status='matched_filename'`

## Integration Points

### Database Structure
All fields are stored in the `screening_type` table:
```sql
SELECT name, content_keywords, document_keywords, filename_keywords, 
       frequency_number, frequency_unit, min_age, max_age, gender_specific, status
FROM screening_type WHERE status = 'active';
```

### API Integration  
The enhanced keyword API serves data from new fields with fallback to old system:
```python
# New fields take precedence
keywords = screening_type.get_content_keywords()
if not keywords:
    # Fallback to old keyword manager
    keywords = old_keyword_system.get_keywords()
```

### Form Integration
The `/screenings?tab=types` interface processes new keyword fields while maintaining existing form behavior:
- Content keywords stored in `content_keywords` field
- Filename keywords stored in `filename_keywords` field  
- Document sections stored in `document_keywords` field

## Usage

```python
from document_screening_matcher import match_document_to_screening

# Match single document to screening
result = match_document_to_screening(screening_type, document, patient)

# Find all matches for a document
matcher = DocumentScreeningMatcher()
all_matches = matcher.find_matching_screenings(document, patient)

# Get patient recommendations
recommendations = matcher.get_screening_recommendations(patient)
```

This system provides comprehensive document-to-screening matching for dynamic prep sheet generation while maintaining full compatibility with existing functionality.