"""
FHIR Constants and Standard Values

This module contains FHIR R4 standard constants, code systems, and value sets
used throughout the FHIR mapping process.
"""

class FHIR_CONSTANTS:
    """FHIR R4 standard constants and code systems"""
    
    # FHIR Resource Types
    RESOURCE_TYPES = {
        'PATIENT': 'Patient',
        'OBSERVATION': 'Observation',
        'CONDITION': 'Condition',
        'APPOINTMENT': 'Appointment',
        'ENCOUNTER': 'Encounter',
        'MEDICATION_REQUEST': 'MedicationRequest',
        'IMMUNIZATION': 'Immunization',
        'DIAGNOSTIC_REPORT': 'DiagnosticReport',
        'DOCUMENT_REFERENCE': 'DocumentReference'
    }
    
    # Code Systems
    CODE_SYSTEMS = {
        'LOINC': 'http://loinc.org',
        'SNOMED_CT': 'http://snomed.info/sct',
        'ICD_10_CM': 'http://hl7.org/fhir/sid/icd-10-cm',
        'CPT': 'http://www.ama-assn.org/go/cpt',
        'HL7_ADMINISTRATIVE_GENDER': 'http://hl7.org/fhir/administrative-gender',
        'HL7_IDENTIFIER_TYPE': 'http://terminology.hl7.org/CodeSystem/v2-0203',
        'HL7_CONTACT_POINT_SYSTEM': 'http://hl7.org/fhir/contact-point-system',
        'HL7_CONTACT_POINT_USE': 'http://hl7.org/fhir/contact-point-use'
    }
    
    # Gender mapping from internal values to FHIR administrative-gender
    GENDER_MAPPING = {
        'Male': 'male',
        'Female': 'female',
        'Other': 'other',
        'Unknown': 'unknown'
    }
    
    # Identifier types
    IDENTIFIER_TYPES = {
        'MRN': {
            'system': 'http://terminology.hl7.org/CodeSystem/v2-0203',
            'code': 'MR',
            'display': 'Medical record number'
        },
        'SSN': {
            'system': 'http://terminology.hl7.org/CodeSystem/v2-0203',
            'code': 'SS',
            'display': 'Social Security number'
        }
    }
    
    # Contact point systems
    CONTACT_POINT_SYSTEMS = {
        'PHONE': 'phone',
        'EMAIL': 'email',
        'FAX': 'fax',
        'URL': 'url'
    }
    
    # Contact point uses
    CONTACT_POINT_USES = {
        'HOME': 'home',
        'WORK': 'work',
        'MOBILE': 'mobile',
        'TEMP': 'temp'
    }
    
    # Address types
    ADDRESS_TYPES = {
        'POSTAL': 'postal',
        'PHYSICAL': 'physical',
        'BOTH': 'both'
    }
    
    # Address uses
    ADDRESS_USES = {
        'HOME': 'home',
        'WORK': 'work',
        'TEMP': 'temp',
        'OLD': 'old'
    }
    
    # Name uses
    NAME_USES = {
        'USUAL': 'usual',
        'OFFICIAL': 'official',
        'TEMP': 'temp',
        'NICKNAME': 'nickname',
        'ANONYMOUS': 'anonymous',
        'OLD': 'old',
        'MAIDEN': 'maiden'
    }
    
    # FHIR Patient status codes
    PATIENT_STATUS = {
        'ACTIVE': 'active',
        'INACTIVE': 'inactive',
        'ENTERED_IN_ERROR': 'entered-in-error',
        'SUSPENDED': 'suspended'
    }