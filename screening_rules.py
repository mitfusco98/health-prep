from datetime import datetime, timedelta
from typing import Dict, List, Any


# FHIR-compliant screening types configuration
SCREENING_TYPES_CONFIG = {
    "mammogram": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "24604-1",
                "display": "Mammography study"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "imaging",
                "display": "Imaging"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "71651007",
                "display": "Mammography"
            }]
        },
        "manual_keywords": ["mammogram", "mammography", "breast imaging", "breast screening"],
        "document_section": "imaging",
        "priority": "high",
        "frequency": "annual"
    },
    
    "colorectal_screening": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "45398-4",
                "display": "Colonoscopy study"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "procedure",
                "display": "Procedure"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "73761001",
                "display": "Colonoscopy"
            }]
        },
        "manual_keywords": ["colonoscopy", "fit test", "cologuard", "colorectal screening", "sigmoidoscopy"],
        "document_section": "procedures",
        "priority": "high",
        "frequency": "10_years"
    },
    
    "pap_test": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10524-7",
                "display": "Cervical or vaginal smear or scraping study"
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
                "system": "http://snomed.info/sct",
                "code": "171149006",
                "display": "Papanicolaou smear"
            }]
        },
        "manual_keywords": ["pap test", "pap smear", "cervical screening", "hpv test"],
        "document_section": "labs",
        "priority": "high",
        "frequency": "3_years"
    },
    
    "psa_test": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "2857-1",
                "display": "Prostate specific antigen [Mass/volume] in Serum or Plasma"
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
                "code": "2857-1",
                "display": "PSA measurement"
            }]
        },
        "manual_keywords": ["psa", "prostate specific antigen", "prostate screening"],
        "document_section": "labs",
        "priority": "medium",
        "frequency": "annual"
    },
    
    "lipid_panel": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "57698-3",
                "display": "Lipid panel with direct LDL - Serum or Plasma"
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
                "code": "57698-3",
                "display": "Lipid panel"
            }]
        },
        "manual_keywords": ["lipid panel", "cholesterol", "hdl", "ldl", "triglycerides"],
        "document_section": "labs",
        "priority": "medium",
        "frequency": "annual"
    },
    
    "hba1c": {
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
    },
    
    "blood_pressure": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel with all children optional"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure measurement"
            }]
        },
        "manual_keywords": ["blood pressure", "bp", "hypertension screening"],
        "document_section": "vitals",
        "priority": "medium",
        "frequency": "annual"
    },
    
    "bone_density": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "38269-7",
                "display": "DXA scan"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "imaging",
                "display": "Imaging"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "312681000",
                "display": "Bone density scan"
            }]
        },
        "manual_keywords": ["bone density", "dexa scan", "dxa", "osteoporosis screening"],
        "document_section": "imaging",
        "priority": "medium",
        "frequency": "2_years"
    },
    
    "ct_lung": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "30621-7",
                "display": "CT Chest"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "imaging",
                "display": "Imaging"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "169069000",
                "display": "CT scan of chest"
            }]
        },
        "manual_keywords": ["low dose ct", "lung screening", "ct chest", "lung cancer screening"],
        "document_section": "imaging",
        "priority": "high",
        "frequency": "annual"
    },
    
    "aaa_ultrasound": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "45036-0",
                "display": "Abdominal aorta Ultrasound"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "imaging",
                "display": "Imaging"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "241501005",
                "display": "Abdominal ultrasound"
            }]
        },
        "manual_keywords": ["abdominal ultrasound", "aaa screening", "aortic aneurysm"],
        "document_section": "imaging",
        "priority": "medium",
        "frequency": "once"
    },
    
    "hepatitis_c": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "13955-0",
                "display": "Hepatitis C virus Ab [Presence] in Serum"
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
                "code": "13955-0",
                "display": "Hepatitis C screening"
            }]
        },
        "manual_keywords": ["hepatitis c", "hcv", "hep c screening"],
        "document_section": "labs",
        "priority": "low",
        "frequency": "once"
    },
    
    "depression_screening": {
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "44249-1",
                "display": "PHQ-9 quick depression assessment panel"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "survey",
                "display": "Survey"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "171207006",
                "display": "Depression screening"
            }]
        },
        "manual_keywords": ["depression screening", "phq9", "mental health screening"],
        "document_section": "assessments",
        "priority": "medium",
        "frequency": "annual"
    },
    
    "influenza_vaccine": {
        "code": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/cvx",
                "code": "141",
                "display": "Influenza, seasonal, injectable"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "therapy",
                "display": "Therapy"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "86198006",
                "display": "Influenza vaccination"
            }]
        },
        "manual_keywords": ["flu shot", "influenza vaccine", "flu vaccine"],
        "document_section": "immunizations",
        "priority": "medium",
        "frequency": "annual"
    },
    
    "shingles_vaccine": {
        "code": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/cvx",
                "code": "187",
                "display": "Zoster vaccine recombinant"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "therapy",
                "display": "Therapy"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "408751008",
                "display": "Zoster vaccination"
            }]
        },
        "manual_keywords": ["shingles vaccine", "zoster vaccine", "shingrix"],
        "document_section": "immunizations",
        "priority": "medium",
        "frequency": "once"
    },
    
    "pneumococcal_vaccine": {
        "code": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/cvx",
                "code": "133",
                "display": "Pneumococcal conjugate PCV 13"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "therapy",
                "display": "Therapy"
            }]
        }],
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "12866006",
                "display": "Pneumococcal vaccination"
            }]
        },
        "manual_keywords": ["pneumonia vaccine", "pneumococcal vaccine", "prevnar"],
        "document_section": "immunizations",
        "priority": "medium",
        "frequency": "once"
    }
}

# FHIR document section mapping
FHIR_DOCUMENT_SECTIONS = {
    "labs": {
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "type_code": "LAB"
    },
    "imaging": {
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "imaging",
                "display": "Imaging"
            }]
        }],
        "type_code": "RAD"
    },
    "procedures": {
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "procedure",
                "display": "Procedure"
            }]
        }],
        "type_code": "PROC"
    },
    "vitals": {
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "type_code": "VITAL"
    },
    "immunizations": {
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "therapy",
                "display": "Therapy"
            }]
        }],
        "type_code": "IMM"
    },
    "assessments": {
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "survey",
                "display": "Survey"
            }]
        }],
        "type_code": "ASSESS"
    },
    "consults": {
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "exam",
                "display": "Exam"
            }]
        }],
        "type_code": "CONSULT"
    },
    "medications": {
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "therapy",
                "display": "Therapy"
            }]
        }],
        "type_code": "MED"
    }
}


def get_screening_by_keyword(keyword: str) -> Dict[str, Any]:
    """
    Find screening type by manual keyword match
    
    Args:
        keyword: Search keyword
        
    Returns:
        Screening configuration dict or None
    """
    keyword_lower = keyword.lower()
    
    for screening_id, config in SCREENING_TYPES_CONFIG.items():
        if keyword_lower in [k.lower() for k in config["manual_keywords"]]:
            return {
                "id": screening_id,
                "config": config
            }
    
    return None


def get_screening_by_loinc_code(loinc_code: str) -> Dict[str, Any]:
    """
    Find screening type by LOINC code
    
    Args:
        loinc_code: LOINC code to search for
        
    Returns:
        Screening configuration dict or None
    """
    for screening_id, config in SCREENING_TYPES_CONFIG.items():
        for coding in config["code"]["coding"]:
            if coding.get("code") == loinc_code and "loinc.org" in coding.get("system", ""):
                return {
                    "id": screening_id,
                    "config": config
                }
    
    return None


def get_screenings_by_document_section(section: str) -> List[Dict[str, Any]]:
    """
    Get all screenings for a specific document section
    
    Args:
        section: Document section (labs, imaging, procedures, etc.)
        
    Returns:
        List of screening configurations
    """
    matching_screenings = []
    
    for screening_id, config in SCREENING_TYPES_CONFIG.items():
        if config["document_section"] == section:
            matching_screenings.append({
                "id": screening_id,
                "config": config
            })
    
    return matching_screenings


def create_fhir_screening_recommendation(screening_config: Dict[str, Any], patient_id: str, due_date: datetime) -> Dict[str, Any]:
    """
    Create a FHIR-compliant screening recommendation
    
    Args:
        screening_config: Screening configuration from SCREENING_TYPES_CONFIG
        patient_id: Patient identifier
        due_date: When screening is due
        
    Returns:
        FHIR ServiceRequest resource structure
    """
    return {
        "resourceType": "ServiceRequest",
        "status": "draft",
        "intent": "plan",
        "category": screening_config["category"],
        "code": screening_config["code"],
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "occurrenceDateTime": due_date.isoformat(),
        "priority": screening_config["priority"],
        "reasonCode": [{
            "text": f"Routine {screening_config['type']['coding'][0]['display'].lower()} screening"
        }],
        "note": [{
            "text": f"Frequency: {screening_config['frequency']}"
        }]
    }


def apply_screening_rules(patient, condition_names):
    """
    Apply FHIR-compliant screening rules to a patient based on demographics and conditions.
    Returns a list of FHIR-structured screening recommendations.

    Args:
        patient: Patient object with demographics
        condition_names: List of patient's condition names (lowercase)

    Returns:
        list: List of FHIR ServiceRequest resources for screening recommendations
    """
    recommendations = []
    today = datetime.now().date()
    
    # Age of patient
    age = patient.age
    sex = patient.sex.lower()

    # Breast Cancer Screening - Mammogram
    if sex == "female" and age >= 40:
        mammogram_config = SCREENING_TYPES_CONFIG["mammogram"]
        frequency = "2_years" if age >= 55 else "annual"
        notes = "Recommended biennial screening for women 55 and older" if age >= 55 else "Recommended annual screening for women 40-54"
        
        recommendation = create_fhir_screening_recommendation(
            mammogram_config, 
            str(patient.id), 
            today
        )
        recommendation["note"] = [{"text": notes}]
        recommendations.append(recommendation)

    # Colorectal Cancer Screening
    if age >= 45 and age <= 75:
        colorectal_config = SCREENING_TYPES_CONFIG["colorectal_screening"]
        recommendation = create_fhir_screening_recommendation(
            colorectal_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{
            "text": "Options include: colonoscopy every 10 years, FIT test annually, or flexible sigmoidoscopy every 5 years"
        }]
        recommendations.append(recommendation)

    # Cervical Cancer Screening - Pap Test
    if sex == "female" and age >= 21 and age <= 65:
        pap_config = SCREENING_TYPES_CONFIG["pap_test"]
        notes = "Recommended Pap test every 3 years for women 21-29" if age < 30 else "Recommended Pap and HPV co-testing every 5 years for women 30-65"
        
        recommendation = create_fhir_screening_recommendation(
            pap_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{"text": notes}]
        recommendations.append(recommendation)

    # Prostate Cancer Screening - PSA Test
    if sex == "male" and age >= 50 and age <= 70:
        psa_config = SCREENING_TYPES_CONFIG["psa_test"]
        recommendation = create_fhir_screening_recommendation(
            psa_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{
            "text": "Consider PSA testing based on individual risk factors and after discussion of benefits and harms"
        }]
        recommendations.append(recommendation)

    # Lipid Panel
    if age >= 40 or any(c in condition_names for c in ["diabetes", "hypertension", "heart disease", "hyperlipidemia"]):
        lipid_config = SCREENING_TYPES_CONFIG["lipid_panel"]
        recommendation = create_fhir_screening_recommendation(
            lipid_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{
            "text": "Recommended annually or more frequently based on risk factors"
        }]
        recommendations.append(recommendation)

    # HbA1C for Diabetes
    if any(c in condition_names for c in ["diabetes", "pre-diabetes", "gestational diabetes"]):
        hba1c_config = SCREENING_TYPES_CONFIG["hba1c"]
        notes = "Monitor glycemic control - Every 3 months for diabetes" if "diabetes" in condition_names else "Monitor glycemic control - Every 6 months for pre-diabetes"
        
        recommendation = create_fhir_screening_recommendation(
            hba1c_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{"text": notes}]
        recommendations.append(recommendation)
    elif age >= 45 or any(c in condition_names for c in ["hypertension", "obesity", "pcos"]):
        hba1c_config = SCREENING_TYPES_CONFIG["hba1c"]
        recommendation = create_fhir_screening_recommendation(
            hba1c_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{
            "text": "Screening for diabetes in higher risk individuals"
        }]
        recommendations.append(recommendation)

    # Blood Pressure Screening
    bp_config = SCREENING_TYPES_CONFIG["blood_pressure"]
    recommendation = create_fhir_screening_recommendation(
        bp_config,
        str(patient.id),
        today
    )
    recommendation["note"] = [{"text": "Recommended for all adults"}]
    recommendations.append(recommendation)

    # Bone Density Screening
    if (sex == "female" and age >= 65) or any(c in condition_names for c in ["osteoporosis", "osteopenia"]):
        bone_density_config = SCREENING_TYPES_CONFIG["bone_density"]
        recommendation = create_fhir_screening_recommendation(
            bone_density_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{
            "text": "Recommended for women 65+ or those with risk factors"
        }]
        recommendations.append(recommendation)

    # Lung Cancer Screening
    if age >= 50 and age <= 80 and any(c in condition_names for c in ["smoking", "tobacco use"]):
        ct_lung_config = SCREENING_TYPES_CONFIG["ct_lung"]
        recommendation = create_fhir_screening_recommendation(
            ct_lung_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{
            "text": "Recommended for adults 50-80 with significant smoking history"
        }]
        recommendations.append(recommendation)

    # Abdominal Aortic Aneurysm Screening
    if sex == "male" and age >= 65 and "smoking" in condition_names:
        aaa_config = SCREENING_TYPES_CONFIG["aaa_ultrasound"]
        recommendation = create_fhir_screening_recommendation(
            aaa_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{
            "text": "One-time screening for men 65-75 who have ever smoked"
        }]
        recommendations.append(recommendation)

    # Hepatitis C Screening
    if age >= 18 and age <= 79:
        hep_c_config = SCREENING_TYPES_CONFIG["hepatitis_c"]
        recommendation = create_fhir_screening_recommendation(
            hep_c_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{
            "text": "One-time screening for all adults born between 1945 and 1965"
        }]
        recommendations.append(recommendation)

    # Depression Screening
    depression_config = SCREENING_TYPES_CONFIG["depression_screening"]
    recommendation = create_fhir_screening_recommendation(
        depression_config,
        str(patient.id),
        today
    )
    recommendation["note"] = [{"text": "Recommended for all adults"}]
    recommendations.append(recommendation)

    # Immunizations
    # Influenza Vaccine
    flu_config = SCREENING_TYPES_CONFIG["influenza_vaccine"]
    recommendation = create_fhir_screening_recommendation(
        flu_config,
        str(patient.id),
        today
    )
    recommendation["note"] = [{"text": "Recommended annually for all adults"}]
    recommendations.append(recommendation)

    # Shingles Vaccine
    if age >= 50:
        shingles_config = SCREENING_TYPES_CONFIG["shingles_vaccine"]
        recommendation = create_fhir_screening_recommendation(
            shingles_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{"text": "Recommended for adults 50+"}]
        recommendations.append(recommendation)

    # Pneumococcal Vaccine
    if age >= 65:
        pneumo_config = SCREENING_TYPES_CONFIG["pneumococcal_vaccine"]
        recommendation = create_fhir_screening_recommendation(
            pneumo_config,
            str(patient.id),
            today
        )
        recommendation["note"] = [{"text": "Recommended for adults 65+"}]
        recommendations.append(recommendation)

    return recommendations


def get_screening_recommendations_by_section(patient, condition_names, section: str) -> List[Dict[str, Any]]:
    """
    Get screening recommendations filtered by document section
    
    Args:
        patient: Patient object
        condition_names: List of condition names
        section: Document section (labs, imaging, procedures, etc.)
        
    Returns:
        List of FHIR ServiceRequest resources for specific section
    """
    all_recommendations = apply_screening_rules(patient, condition_names)
    section_screenings = get_screenings_by_document_section(section)
    section_codes = [s["config"]["code"]["coding"][0]["code"] for s in section_screenings]
    
    filtered_recommendations = []
    for rec in all_recommendations:
        if rec["code"]["coding"][0]["code"] in section_codes:
            filtered_recommendations.append(rec)
    
    return filtered_recommendations


def search_screening_by_keyword(keyword: str, patient=None, condition_names=None) -> Dict[str, Any]:
    """
    Search for screening recommendations by keyword
    
    Args:
        keyword: Search term
        patient: Optional patient object for personalized recommendations
        condition_names: Optional condition names for personalized recommendations
        
    Returns:
        Dictionary with screening information and optionally personalized recommendation
    """
    screening_match = get_screening_by_keyword(keyword)
    
    if not screening_match:
        return {"error": "No screening found for keyword", "keyword": keyword}
    
    result = {
        "screening_id": screening_match["id"],
        "config": screening_match["config"],
        "keyword_matched": keyword
    }
    
    # If patient provided, create personalized recommendation
    if patient and condition_names is not None:
        recommendation = create_fhir_screening_recommendation(
            screening_match["config"],
            str(patient.id),
            datetime.now().date()
        )
        result["personalized_recommendation"] = recommendation
    
    return result
