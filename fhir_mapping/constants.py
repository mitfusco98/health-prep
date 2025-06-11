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
    
    # FHIR Encounter status mapping
    ENCOUNTER_STATUS_MAPPING = {
        'OOO': 'planned',          # Out of office/scheduled
        'waiting': 'arrived',      # Patient has arrived
        'provider': 'in-progress', # Provider is seeing patient
        'seen': 'finished'         # Encounter completed
    }
    
    # FHIR Encounter class codes
    ENCOUNTER_CLASS = {
        'AMBULATORY': {
            'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode',
            'code': 'AMB',
            'display': 'ambulatory'
        },
        'INPATIENT': {
            'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode',
            'code': 'IMP',
            'display': 'inpatient encounter'
        },
        'EMERGENCY': {
            'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode',
            'code': 'EMER',
            'display': 'emergency'
        }
    }
    
    # FHIR Encounter type codes
    ENCOUNTER_TYPE = {
        'CHECKUP': {
            'system': 'http://snomed.info/sct',
            'code': '185349003',
            'display': 'Encounter for check up'
        },
        'FOLLOWUP': {
            'system': 'http://snomed.info/sct',
            'code': '185389009',
            'display': 'Follow-up encounter'
        },
        'CONSULTATION': {
            'system': 'http://snomed.info/sct',
            'code': '11429006',
            'display': 'Consultation'
        }
    }
    
    # FHIR DocumentReference status codes
    DOCUMENT_STATUS = {
        'CURRENT': 'current',
        'SUPERSEDED': 'superseded',
        'ENTERED_IN_ERROR': 'entered-in-error'
    }
    
    # FHIR DocumentReference docStatus codes
    DOC_STATUS = {
        'PRELIMINARY': 'preliminary',
        'FINAL': 'final',
        'AMENDED': 'amended',
        'CANCELLED': 'cancelled'
    }
    
    # Document type mappings to FHIR coding
    DOCUMENT_TYPE_MAPPING = {
        'Lab Results': {
            'system': 'http://loinc.org',
            'code': '11502-2',
            'display': 'Laboratory report'
        },
        'Imaging': {
            'system': 'http://loinc.org',
            'code': '18748-4',
            'display': 'Diagnostic imaging study'
        },
        'Progress Notes': {
            'system': 'http://loinc.org',
            'code': '11506-3',
            'display': 'Progress note'
        },
        'Discharge Summary': {
            'system': 'http://loinc.org',
            'code': '18842-5',
            'display': 'Discharge summary'
        },
        'Consultation': {
            'system': 'http://loinc.org',
            'code': '11488-4',
            'display': 'Consultation note'
        },
        'Operative Note': {
            'system': 'http://loinc.org',
            'code': '11504-8',
            'display': 'Surgical operation note'
        },
        'Pathology': {
            'system': 'http://loinc.org',
            'code': '11526-1',
            'display': 'Pathology study'
        },
        'Radiology': {
            'system': 'http://loinc.org',
            'code': '18726-0',
            'display': 'Radiology studies'
        },
        'Other': {
            'system': 'http://loinc.org',
            'code': '34133-9',
            'display': 'Summarization of episode note'
        }
    }
    
    # Document category mappings
    DOCUMENT_CATEGORY = {
        'CLINICAL': {
            'system': 'http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category',
            'code': 'clinical-note',
            'display': 'Clinical Note'
        },
        'LABORATORY': {
            'system': 'http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category',
            'code': 'laboratory',
            'display': 'Laboratory'
        },
        'IMAGING': {
            'system': 'http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category',
            'code': 'imaging',
            'display': 'Imaging'
        }
    }
    
    # Content attachment formats
    CONTENT_FORMAT = {
        'PDF': {
            'system': 'http://ihe.net/fhir/ihe.formatcode.fhir/CodeSystem/formatcode',
            'code': 'urn:ihe:iti:xds:2017:mimeTypeSufficient',
            'display': 'mimeType Sufficient'
        },
        'TEXT': {
            'system': 'http://ihe.net/fhir/ihe.formatcode.fhir/CodeSystem/formatcode',
            'code': 'urn:ihe:iti:xds:2017:mimeTypeSufficient',
            'display': 'mimeType Sufficient'
        }
    }