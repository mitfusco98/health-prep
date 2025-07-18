# Variant Screening Implementation Guide

## Overview
This guide explains how to properly implement variant screenings that have different patient eligibility criteria based on medical conditions, age, gender, or other factors.

## Core Issue Fixed (July 18, 2025)
The system was incorrectly applying variant screenings to all patients, regardless of their medical conditions. For example:
- **Problem**: Non-diabetic patients were getting A1C screenings with 3-month frequency
- **Root Cause**: `_patient_has_trigger_conditions` method wasn't properly matching SNOMED codes and condition names
- **Solution**: Enhanced trigger condition matching with proper SNOMED code validation and condition name matching

## How Variant Screening Logic Works

### 1. Patient Eligibility Check
The system uses `unified_screening_engine.py` to determine if a patient qualifies for a screening:

```python
def is_patient_eligible(patient, screening_type):
    # 1. Age filtering (min_age, max_age)
    # 2. Gender filtering (gender_specific)
    # 3. Trigger conditions (medical conditions required)
    # 4. Returns (True/False, reason)
```

### 2. Trigger Condition Matching
For medical condition-based variants, the system matches:
- **SNOMED Codes**: Exact match on patient condition codes
- **Condition Names**: Partial match on condition display names
- **Diabetes-specific**: Special handling for diabetes variations

### 3. Screening Assignment
Only eligible patients receive the screening with the appropriate frequency.

## Creating New Variant Screenings

### Step 1: Define the Screening Type
In `/screenings?tab=types`, create a new screening type with:
- **Name**: Descriptive name (e.g., "Vaccination History - Seniors")
- **Frequency**: Structured frequency (e.g., 1 year)
- **Trigger Conditions**: JSON array of required conditions

### Step 2: Set Trigger Conditions
For medical condition-based variants, use this JSON format:
```json
[
  {
    "system": "http://snomed.info/sct",
    "code": "73211009",
    "display": "Diabetes mellitus"
  }
]
```

For age-based variants:
- Set `min_age` and/or `max_age` fields
- Leave `trigger_conditions` empty for age-only variants

### Step 3: Configure Demographics
- **Gender-specific**: Set to "male", "female", or leave blank for both
- **Age ranges**: Set min_age and max_age as needed
- **Trigger conditions**: Add JSON for medical conditions

### Step 4: Add Keywords
Configure parsing rules for document matching:
- **Content Keywords**: Medical terms found in document content
- **Filename Keywords**: Terms found in document filenames
- **Document Type Keywords**: Document types that match this screening

## Example: Creating Vaccination History for Seniors (65+)

### Configuration:
```
Name: Vaccination History - Seniors
Frequency: 1 year
Min Age: 65
Max Age: (blank)
Gender: (blank - applies to both)
Trigger Conditions: (blank - age-only variant)

Content Keywords: ["vaccination", "immunization", "vaccine", "shot", "flu shot", "pneumonia vaccine", "shingles vaccine"]
Filename Keywords: ["vaccination", "immunization", "vaccine"]
Document Type Keywords: ["IMMUNIZATION_RECORD", "VACCINATION_RECORD"]
```

### Result:
- Only patients 65+ will receive this screening
- Younger patients will use the standard "Vaccination History" screening
- Each has unique keywords for different vaccine types

## Example: Creating A1C Variants

### For Diabetic Patients:
```
Name: HbA1c Test
Frequency: 3 months
Trigger Conditions: [{"system": "http://snomed.info/sct", "code": "73211009", "display": "Diabetes mellitus"}]
```

### For Non-Diabetic Patients (if needed):
```
Name: HbA1c Test - General
Frequency: 1 year
Trigger Conditions: (blank - no conditions required)
```

## Best Practices

### 1. Test Patient Eligibility
Before creating variants, check:
- What conditions exist in your patient database?
- Do the SNOMED codes match patient condition codes?
- Are condition names consistent?

### 2. Use Proper SNOMED Codes
- Look up official SNOMED CT codes
- Use standard medical terminology
- Include both code and display text

### 3. Create Unique Keywords
- Each variant should have distinct keywords
- Avoid overlapping terms that cause conflicts
- Use specific medical terminology

### 4. Test Before Deployment
```python
# Test eligibility logic
from unified_screening_engine import UnifiedScreeningEngine
engine = UnifiedScreeningEngine()
engine.debug_mode = True

# Test with sample patients
is_eligible, reason = engine.is_patient_eligible(patient, screening_type)
print(f"Patient eligible: {is_eligible} - {reason}")
```

## Common Medical Conditions and SNOMED Codes

### Diabetes:
- Type 1: `E10` (ICD-10) or `46635009` (SNOMED)
- Type 2: `E11.9` (ICD-10) or `44054006` (SNOMED)
- General: `73211009` (SNOMED)

### Hypertension:
- Essential: `I10` (ICD-10) or `59621000` (SNOMED)
- General: `38341003` (SNOMED)

### Heart Disease:
- Coronary: `414.9` (ICD-9) or `53741008` (SNOMED)
- Heart failure: `428.0` (ICD-9) or `84114007` (SNOMED)

## Troubleshooting

### Issue: Variant not applying to eligible patients
**Check:**
1. Are trigger conditions properly formatted JSON?
2. Do patient condition codes match trigger codes?
3. Are condition names spelled correctly?
4. Is the screening type active?

### Issue: Variant applying to wrong patients
**Check:**
1. Are trigger conditions too broad?
2. Are age/gender filters correct?
3. Are there competing screening types?
4. Check eligibility logic with debug mode

### Issue: No documents matching
**Check:**
1. Are keywords properly configured?
2. Do keywords match actual document content?
3. Are document types correctly specified?
4. Test with sample documents

## System Architecture

### Key Files:
- `unified_screening_engine.py`: Core eligibility and matching logic
- `models.py`: Patient, Condition, ScreeningType models
- `automated_screening_engine.py`: Screening generation
- `demo_routes.py`: Screening management routes

### Database Tables:
- `screening_type`: Screening definitions and trigger conditions
- `condition`: Patient medical conditions
- `screening`: Individual patient screening assignments
- `screening_documents`: Document-screening relationships

## Conclusion

The variant screening system now properly respects medical conditions and demographic criteria. Follow this guide to create new variants that accurately target specific patient populations without incorrectly applying to ineligible patients.