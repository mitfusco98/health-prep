"""
Medical Terminology Standardizer
Provides standardized medical terminology for screening types and conditions
to prevent variant detection issues caused by inconsistent naming.
"""

import json
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re

class MedicalTerminologyStandardizer:
    """
    Standardizes medical terminology for screening types and conditions
    to ensure consistent variant detection and prevent user input errors.
    """
    
    def __init__(self):
        self.screening_standards = self._load_screening_standards()
        self.condition_standards = self._load_condition_standards()
        self.synonym_mappings = self._load_synonym_mappings()
    
    def _load_screening_standards(self) -> Dict[str, Dict]:
        """Load standardized screening type definitions"""
        return {
            "mammography": {
                "canonical_name": "Mammography",
                "aliases": ["mammogram", "breast imaging", "breast screening", "mammographic screening"],
                "category": "cancer_screening",
                "typical_frequency": {"number": 1, "unit": "years"},
                "description": "Breast cancer screening using mammography"
            },
            "colonoscopy": {
                "canonical_name": "Colonoscopy", 
                "aliases": ["colo", "colorectal screening", "colon screening", "lower endoscopy"],
                "category": "cancer_screening",
                "typical_frequency": {"number": 10, "unit": "years"},
                "description": "Colorectal cancer screening using colonoscopy"
            },
            "pap_smear": {
                "canonical_name": "Pap Smear",
                "aliases": ["pap test", "cervical cancer screening", "cervical screening", "cytology"],
                "category": "cancer_screening", 
                "typical_frequency": {"number": 3, "unit": "years"},
                "description": "Cervical cancer screening using Pap test"
            },
            "hba1c": {
                "canonical_name": "HbA1c Test",
                "aliases": ["a1c", "hemoglobin a1c", "glycated hemoglobin", "diabetes monitoring"],
                "category": "diabetes_monitoring",
                "typical_frequency": {"number": 6, "unit": "months"},
                "description": "Diabetes monitoring using HbA1c"
            },
            "lipid_panel": {
                "canonical_name": "Lipid Panel",
                "aliases": ["cholesterol test", "lipid profile", "cholesterol panel", "lipid screening"],
                "category": "cardiovascular_screening",
                "typical_frequency": {"number": 5, "unit": "years"},
                "description": "Cardiovascular risk assessment using lipid panel"
            },
            "bone_density": {
                "canonical_name": "Bone Density Screening",
                "aliases": ["dxa scan", "dexa", "osteoporosis screening", "bone scan"],
                "category": "bone_health",
                "typical_frequency": {"number": 2, "unit": "years"},
                "description": "Osteoporosis screening using bone density measurement"
            },
            "eye_exam": {
                "canonical_name": "Eye Exam",
                "aliases": ["vision screening", "ophthalmology exam", "diabetic eye exam", "retinal screening"],
                "category": "vision_screening",
                "typical_frequency": {"number": 1, "unit": "years"},
                "description": "Comprehensive eye examination"
            },
            "vaccination": {
                "canonical_name": "Vaccination History",
                "aliases": ["immunization history", "immunizations", "vaccines", "vaccination status"],
                "category": "immunization",
                "typical_frequency": {"number": 1, "unit": "years"},
                "description": "Review and update of vaccination status"
            },
            "blood_pressure": {
                "canonical_name": "Blood Pressure Screening",
                "aliases": ["bp screening", "hypertension screening", "blood pressure check"],
                "category": "cardiovascular_screening",
                "typical_frequency": {"number": 1, "unit": "years"},
                "description": "Blood pressure measurement and hypertension screening"
            },
            "psa": {
                "canonical_name": "PSA Test",
                "aliases": ["prostate specific antigen", "prostate screening", "psa screening"],
                "category": "cancer_screening",
                "typical_frequency": {"number": 1, "unit": "years"},
                "description": "Prostate cancer screening using PSA"
            }
        }
    
    def _load_condition_standards(self) -> Dict[str, Dict]:
        """Load standardized medical condition definitions"""
        return {
            "diabetes": {
                "canonical_name": "Diabetes mellitus",
                "aliases": ["diabetes", "diabetes mellitus", "type 2 diabetes", "type 1 diabetes", "dm"],
                "snomed_codes": ["73211009", "44054006", "46635009"],
                "icd10_codes": ["E11.9", "E10.9", "E11"],
                "category": "endocrine"
            },
            "hypertension": {
                "canonical_name": "Hypertensive disorder",
                "aliases": ["hypertension", "high blood pressure", "htn", "hypertensive disease"],
                "snomed_codes": ["38341003", "59621000"],
                "icd10_codes": ["I10", "I15.9"],
                "category": "cardiovascular"
            },
            "osteoporosis": {
                "canonical_name": "Osteoporosis",
                "aliases": ["osteoporosis", "osteopenia", "bone loss", "low bone density"],
                "snomed_codes": ["64859006", "312894000"],
                "icd10_codes": ["M81.0", "M85.8"],
                "category": "musculoskeletal"
            },
            "cancer_history": {
                "canonical_name": "Personal history of malignant neoplasm",
                "aliases": ["cancer history", "personal history of cancer", "previous cancer", "cancer survivor"],
                "snomed_codes": ["395557000", "429740004"],
                "icd10_codes": ["Z85.9", "Z80.9"],
                "category": "oncology"
            },
            "smoking": {
                "canonical_name": "Tobacco use disorder",
                "aliases": ["smoking", "tobacco use", "smoker", "cigarette smoking", "nicotine dependence"],
                "snomed_codes": ["365981007", "56294008"],
                "icd10_codes": ["Z87.891", "F17.210"],
                "category": "behavioral"
            }
        }
    
    def _load_synonym_mappings(self) -> Dict[str, str]:
        """Create bidirectional synonym mappings for quick lookup"""
        mappings = {}
        
        # Add screening type synonyms
        for key, data in self.screening_standards.items():
            canonical = data["canonical_name"]
            mappings[canonical.lower()] = canonical
            for alias in data["aliases"]:
                mappings[alias.lower()] = canonical
        
        # Add condition synonyms  
        for key, data in self.condition_standards.items():
            canonical = data["canonical_name"]
            mappings[canonical.lower()] = canonical
            for alias in data["aliases"]:
                mappings[alias.lower()] = canonical
                
        return mappings
    
    def normalize_screening_name(self, input_name: str) -> Tuple[str, float]:
        """
        Normalize a screening name to its canonical form
        
        Args:
            input_name: User-provided screening name
            
        Returns:
            Tuple of (canonical_name, confidence_score)
        """
        if not input_name:
            return "", 0.0
            
        input_clean = input_name.strip().lower()
        
        # Direct match in synonym mappings
        if input_clean in self.synonym_mappings:
            return self.synonym_mappings[input_clean], 1.0
        
        # Fuzzy matching against all known terms
        best_match = ""
        best_score = 0.0
        
        for term, canonical in self.synonym_mappings.items():
            similarity = SequenceMatcher(None, input_clean, term).ratio()
            if similarity > best_score and similarity >= 0.8:  # 80% similarity threshold
                best_match = canonical
                best_score = similarity
        
        return best_match, best_score
    
    def normalize_condition_name(self, input_name: str) -> Tuple[str, float]:
        """
        Normalize a condition name to its canonical form
        
        Args:
            input_name: User-provided condition name
            
        Returns:
            Tuple of (canonical_name, confidence_score)
        """
        if not input_name:
            return "", 0.0
            
        input_clean = input_name.strip().lower()
        
        # Direct match in synonym mappings
        if input_clean in self.synonym_mappings:
            return self.synonym_mappings[input_clean], 1.0
        
        # Fuzzy matching against condition terms
        best_match = ""
        best_score = 0.0
        
        for key, data in self.condition_standards.items():
            canonical = data["canonical_name"]
            
            # Check canonical name
            similarity = SequenceMatcher(None, input_clean, canonical.lower()).ratio()
            if similarity > best_score and similarity >= 0.7:  # 70% similarity for conditions
                best_match = canonical
                best_score = similarity
            
            # Check aliases
            for alias in data["aliases"]:
                similarity = SequenceMatcher(None, input_clean, alias.lower()).ratio()
                if similarity > best_score and similarity >= 0.7:
                    best_match = canonical
                    best_score = similarity
        
        return best_match, best_score
    
    def get_screening_suggestions(self, partial_input: str, limit: int = 10) -> List[Dict]:
        """
        Get screening name suggestions for autocomplete
        
        Args:
            partial_input: Partial screening name
            limit: Maximum number of suggestions
            
        Returns:
            List of suggestion dictionaries
        """
        if not partial_input or len(partial_input) < 2:
            return []
        
        input_clean = partial_input.strip().lower()
        suggestions = []
        
        for key, data in self.screening_standards.items():
            canonical = data["canonical_name"]
            
            # Check if canonical name or any alias contains the input
            matches = [canonical] + data["aliases"]
            for match in matches:
                if input_clean in match.lower():
                    suggestions.append({
                        "canonical_name": canonical,
                        "display_text": canonical,
                        "category": data["category"],
                        "description": data["description"],
                        "typical_frequency": data["typical_frequency"]
                    })
                    break  # Only add each canonical once
        
        # Sort by relevance (exact matches first, then by length)
        suggestions.sort(key=lambda x: (
            not x["display_text"].lower().startswith(input_clean),
            len(x["display_text"])
        ))
        
        return suggestions[:limit]
    
    def get_condition_suggestions(self, partial_input: str, limit: int = 10) -> List[Dict]:
        """
        Get condition name suggestions for autocomplete
        
        Args:
            partial_input: Partial condition name
            limit: Maximum number of suggestions
            
        Returns:
            List of suggestion dictionaries
        """
        if not partial_input or len(partial_input) < 2:
            return []
        
        input_clean = partial_input.strip().lower()
        suggestions = []
        
        for key, data in self.condition_standards.items():
            canonical = data["canonical_name"]
            
            # Check if canonical name or any alias contains the input
            matches = [canonical] + data["aliases"]
            for match in matches:
                if input_clean in match.lower():
                    suggestions.append({
                        "canonical_name": canonical,
                        "display_text": canonical,
                        "category": data["category"],
                        "snomed_codes": data["snomed_codes"],
                        "icd10_codes": data["icd10_codes"]
                    })
                    break  # Only add each canonical once
        
        # Sort by relevance
        suggestions.sort(key=lambda x: (
            not x["display_text"].lower().startswith(input_clean),
            len(x["display_text"])
        ))
        
        return suggestions[:limit]
    
    def detect_variants(self, screening_name: str) -> List[str]:
        """
        Detect all variants of a given screening name
        
        Args:
            screening_name: Base screening name
            
        Returns:
            List of all canonical names that are variants of the input
        """
        normalized, confidence = self.normalize_screening_name(screening_name)
        if confidence < 0.8:
            return []
        
        # Find the base screening standard
        base_key = None
        for key, data in self.screening_standards.items():
            if data["canonical_name"] == normalized:
                base_key = key
                break
        
        if not base_key:
            return []
        
        # For now, return just the normalized name
        # This can be extended to include actual variant logic
        return [normalized]
    
    def validate_screening_input(self, name: str, trigger_conditions: List[str]) -> Dict:
        """
        Validate screening type input and provide suggestions
        
        Args:
            name: Screening type name
            trigger_conditions: List of trigger condition strings
            
        Returns:
            Validation result dictionary
        """
        result = {
            "name_valid": False,
            "name_suggestion": "",
            "name_confidence": 0.0,
            "condition_suggestions": [],
            "warnings": [],
            "errors": []
        }
        
        # Validate screening name
        if name:
            normalized_name, confidence = self.normalize_screening_name(name)
            result["name_suggestion"] = normalized_name
            result["name_confidence"] = confidence
            
            if confidence >= 0.8:
                result["name_valid"] = True
            elif confidence >= 0.5:
                result["warnings"].append(f"Did you mean '{normalized_name}'? (similarity: {confidence:.1%})")
            else:
                result["errors"].append("Screening name not recognized. Please use standard medical terminology.")
        
        # Validate trigger conditions
        for condition in trigger_conditions:
            if condition.strip():
                normalized_condition, confidence = self.normalize_condition_name(condition)
                if confidence >= 0.7:
                    result["condition_suggestions"].append({
                        "original": condition,
                        "suggested": normalized_condition,
                        "confidence": confidence
                    })
                elif confidence >= 0.4:
                    result["warnings"].append(f"Condition '{condition}' - did you mean '{normalized_condition}'?")
                else:
                    result["warnings"].append(f"Condition '{condition}' not recognized in standard terminology")
        
        return result


# Global instance for use throughout the application
medical_standardizer = MedicalTerminologyStandardizer()