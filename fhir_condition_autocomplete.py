"""
FHIR Condition Code Autocomplete System
Provides autocomplete functionality for medical condition codes using SNOMED CT, ICD-10-CM, and common medical conditions
"""

import json
from typing import List, Dict, Any
from flask import jsonify

class FHIRConditionAutocomplete:
    """Handles autocomplete for FHIR condition codes"""
    
    def __init__(self):
        """Initialize with common medical conditions and their codes"""
        self.condition_database = {
            # Diabetes conditions
            "diabetes": [
                {"system": "http://snomed.info/sct", "code": "73211009", "display": "Diabetes mellitus"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11", "display": "Type 2 diabetes mellitus"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E10", "display": "Type 1 diabetes mellitus"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11.9", "display": "Type 2 diabetes mellitus without complications"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11.65", "display": "Type 2 diabetes mellitus with hyperglycemia"},
            ],
            "type 2 diabetes": [
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11", "display": "Type 2 diabetes mellitus"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11.9", "display": "Type 2 diabetes mellitus without complications"},
                {"system": "http://snomed.info/sct", "code": "44054006", "display": "Type 2 diabetes mellitus"},
            ],
            "type 1 diabetes": [
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E10", "display": "Type 1 diabetes mellitus"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E10.9", "display": "Type 1 diabetes mellitus without complications"},
                {"system": "http://snomed.info/sct", "code": "46635009", "display": "Type 1 diabetes mellitus"},
            ],
            
            # Hypertension
            "hypertension": [
                {"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertensive disorder"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I15", "display": "Secondary hypertension"},
            ],
            "high blood pressure": [
                {"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertensive disorder"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"},
            ],
            
            # Heart conditions
            "coronary artery disease": [
                {"system": "http://snomed.info/sct", "code": "53741008", "display": "Coronary artery disease"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I25.10", "display": "Atherosclerotic heart disease of native coronary artery without angina pectoris"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I25.9", "display": "Chronic ischemic heart disease, unspecified"},
            ],
            "heart failure": [
                {"system": "http://snomed.info/sct", "code": "84114007", "display": "Heart failure"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I50.9", "display": "Heart failure, unspecified"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I50.1", "display": "Left ventricular failure"},
            ],
            "atrial fibrillation": [
                {"system": "http://snomed.info/sct", "code": "49436004", "display": "Atrial fibrillation"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I48.91", "display": "Unspecified atrial fibrillation"},
            ],
            
            # Cancer conditions
            "breast cancer": [
                {"system": "http://snomed.info/sct", "code": "254837009", "display": "Malignant neoplasm of breast"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "C50.9", "display": "Malignant neoplasm of unspecified site of unspecified female breast"},
            ],
            "prostate cancer": [
                {"system": "http://snomed.info/sct", "code": "399068003", "display": "Malignant neoplasm of prostate"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "C61", "display": "Malignant neoplasm of prostate"},
            ],
            "colorectal cancer": [
                {"system": "http://snomed.info/sct", "code": "363406005", "display": "Malignant neoplasm of colon"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "C78.5", "display": "Secondary malignant neoplasm of large intestine and rectum"},
            ],
            
            # Respiratory conditions
            "asthma": [
                {"system": "http://snomed.info/sct", "code": "195967001", "display": "Asthma"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "J45.9", "display": "Asthma, unspecified"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "J45.0", "display": "Predominantly allergic asthma"},
            ],
            "copd": [
                {"system": "http://snomed.info/sct", "code": "13645005", "display": "Chronic obstructive lung disease"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "J44.1", "display": "Chronic obstructive pulmonary disease with acute exacerbation"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "J44.0", "display": "Chronic obstructive pulmonary disease with acute lower respiratory infection"},
            ],
            
            # Mental health
            "depression": [
                {"system": "http://snomed.info/sct", "code": "35489007", "display": "Depressive disorder"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "F32.9", "display": "Major depressive disorder, single episode, unspecified"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "F33.9", "display": "Major depressive disorder, recurrent, unspecified"},
            ],
            "anxiety": [
                {"system": "http://snomed.info/sct", "code": "197480006", "display": "Anxiety disorder"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "F41.9", "display": "Anxiety disorder, unspecified"},
            ],
            
            # Kidney conditions
            "chronic kidney disease": [
                {"system": "http://snomed.info/sct", "code": "431855005", "display": "Chronic kidney disease"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "N18.6", "display": "End stage renal disease"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "N18.3", "display": "Chronic kidney disease, stage 3 (moderate)"},
            ],
            
            # Osteoporosis
            "osteoporosis": [
                {"system": "http://snomed.info/sct", "code": "64859006", "display": "Osteoporosis"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "M81.0", "display": "Age-related osteoporosis without current pathological fracture"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "M80.00XA", "display": "Age-related osteoporosis with current pathological fracture, unspecified site, initial encounter for fracture"},
            ],
            
            # Hyperlipidemia
            "hyperlipidemia": [
                {"system": "http://snomed.info/sct", "code": "55822004", "display": "Hyperlipidemia"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E78.5", "display": "Hyperlipidemia, unspecified"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E78.0", "display": "Pure hypercholesterolemia"},
            ],
            "high cholesterol": [
                {"system": "http://snomed.info/sct", "code": "13644009", "display": "Hypercholesterolemia"},
                {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E78.0", "display": "Pure hypercholesterolemia"},
            ],
        }
        
        # Create search index for faster lookups
        self.search_index = self._build_search_index()
    
    def _build_search_index(self) -> Dict[str, List[str]]:
        """Build a search index for faster condition lookups"""
        index = {}
        
        for condition_name, codes in self.condition_database.items():
            # Add the exact condition name
            words = condition_name.lower().split()
            for word in words:
                if word not in index:
                    index[word] = []
                if condition_name not in index[word]:
                    index[word].append(condition_name)
            
            # Add individual words from display names
            for code_info in codes:
                display_words = code_info["display"].lower().split()
                for word in display_words:
                    if len(word) > 2:  # Skip very short words
                        if word not in index:
                            index[word] = []
                        if condition_name not in index[word]:
                            index[word].append(condition_name)
        
        return index
    
    def search_conditions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for conditions based on query string
        
        Args:
            query: Search query (condition name or partial name)
            limit: Maximum number of results to return
            
        Returns:
            List of matching conditions with their codes
        """
        if not query or len(query) < 2:
            return []
        
        query = query.lower().strip()
        matching_conditions = set()
        
        # Direct match
        if query in self.condition_database:
            matching_conditions.add(query)
        
        # Partial matches
        for condition_name in self.condition_database.keys():
            if query in condition_name.lower():
                matching_conditions.add(condition_name)
        
        # Word-based search using index
        query_words = query.split()
        for word in query_words:
            if word in self.search_index:
                matching_conditions.update(self.search_index[word])
        
        # Build results
        results = []
        for condition_name in list(matching_conditions)[:limit]:
            codes = self.condition_database[condition_name]
            results.append({
                "condition_name": condition_name,
                "codes": codes,
                "primary_code": codes[0] if codes else None
            })
        
        return results
    
    def get_codes_for_condition(self, condition_name: str) -> List[Dict[str, Any]]:
        """
        Get all codes for a specific condition
        
        Args:
            condition_name: Exact condition name
            
        Returns:
            List of code dictionaries
        """
        return self.condition_database.get(condition_name.lower(), [])
    
    def add_condition(self, condition_name: str, codes: List[Dict[str, Any]]):
        """
        Add a new condition with its codes to the database
        
        Args:
            condition_name: Name of the condition
            codes: List of code dictionaries with system, code, display
        """
        self.condition_database[condition_name.lower()] = codes
        # Rebuild search index
        self.search_index = self._build_search_index()

# Global instance
autocomplete_service = FHIRConditionAutocomplete()