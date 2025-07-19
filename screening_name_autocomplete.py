"""
Screening Name Autocomplete System
Provides autocomplete functionality for common medical screening names
"""

import json
from typing import List, Dict, Any
from flask import jsonify

class ScreeningNameAutocomplete:
    """Handles autocomplete for common medical screening names"""
    
    def __init__(self):
        """Initialize with common medical screenings"""
        self.screening_database = [
            # Cancer Screenings
            "Mammography",
            "Breast Cancer Screening",
            "Cervical Cancer Screening", 
            "Pap Smear",
            "Pap Test",
            "Colonoscopy",
            "Colorectal Cancer Screening",
            "Prostate Cancer Screening",
            "PSA Test",
            "Lung Cancer Screening",
            "Low-Dose CT Chest",
            "Skin Cancer Screening",
            "Dermatologic Examination",
            
            # Cardiovascular Screenings
            "Blood Pressure Screening",
            "Hypertension Screening",
            "Cholesterol Screening",
            "Lipid Panel",
            "Cardiovascular Risk Assessment",
            "Electrocardiogram (ECG)",
            "Echocardiogram",
            "Stress Test",
            "Cardiac Stress Test",
            
            # Diabetes/Metabolic Screenings
            "Diabetes Screening",
            "Blood Glucose Test",
            "Hemoglobin A1c",
            "HbA1c Test",
            "Glucose Tolerance Test",
            "Fasting Blood Sugar",
            "Metabolic Panel",
            "Comprehensive Metabolic Panel",
            
            # Bone Health
            "Bone Density Screening",
            "DEXA Scan",
            "DXA Scan",
            "Osteoporosis Screening",
            
            # Vision/Hearing
            "Vision Screening",
            "Eye Examination",
            "Glaucoma Screening",
            "Diabetic Eye Exam",
            "Hearing Test",
            "Audiometry",
            
            # Infectious Disease Screenings
            "Hepatitis B Screening",
            "Hepatitis C Screening",
            "HIV Screening",
            "Tuberculosis Screening",
            "TB Test",
            "STD Screening",
            "Sexually Transmitted Infection Screening",
            
            # Preventive Health
            "Annual Physical Exam",
            "Wellness Visit",
            "Health Maintenance Exam",
            "Preventive Care Visit",
            "Depression Screening",
            "Mental Health Screening",
            "Substance Abuse Screening",
            "Fall Risk Assessment",
            "Cognitive Assessment",
            
            # Women's Health
            "Gynecologic Exam",
            "Pelvic Exam",
            "Breast Exam",
            "Prenatal Screening",
            "Pregnancy Screening",
            "Osteoporosis Screening",
            
            # Men's Health
            "Prostate Exam",
            "Testicular Exam",
            "Abdominal Aortic Aneurysm Screening",
            "AAA Screening",
            
            # Age-Specific Screenings
            "Pediatric Screening",
            "Adolescent Screening",
            "Geriatric Assessment",
            "Senior Wellness Check",
            
            # Specialty Screenings
            "Thyroid Function Test",
            "Kidney Function Test",
            "Liver Function Test",
            "Anemia Screening",
            "Complete Blood Count",
            "CBC",
            "Urinalysis",
            "Vitamin D Screening",
            "B12 Screening",
            "Iron Studies",
            
            # Immunizations (often tracked as screenings)
            "Vaccination Status Review",
            "Immunization Assessment",
            "Flu Shot",
            "COVID-19 Vaccination",
            
            # Other Common Screenings
            "Sleep Apnea Screening",
            "Nutrition Assessment",
            "Weight Management Screening",
            "BMI Assessment",
            "Smoking Cessation Screening",
            "Alcohol Screening",
        ]
        
        # Create search index for faster lookups
        self.search_index = self._build_search_index()
    
    def _build_search_index(self) -> Dict[str, List[str]]:
        """Build a search index for faster screening name lookups"""
        index = {}
        
        for screening_name in self.screening_database:
            # Add the exact screening name
            words = screening_name.lower().split()
            for word in words:
                # Clean word of punctuation
                clean_word = ''.join(c for c in word if c.isalnum())
                if len(clean_word) > 1:  # Skip very short words
                    if clean_word not in index:
                        index[clean_word] = []
                    if screening_name not in index[clean_word]:
                        index[clean_word].append(screening_name)
        
        return index
    
    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get screening name suggestions based on query"""
        if not query or len(query.strip()) < 2:
            return []
        
        query = query.lower().strip()
        suggestions = set()
        
        # Exact name matches
        for screening_name in self.screening_database:
            if query in screening_name.lower():
                suggestions.add(screening_name)
        
        # Word-based matches using search index
        query_words = query.split()
        for word in query_words:
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word in self.search_index:
                suggestions.update(self.search_index[clean_word])
        
        # Sort by relevance (exact matches first, then contains matches)
        sorted_suggestions = []
        
        # Exact matches first
        for screening in suggestions:
            if screening.lower().startswith(query):
                sorted_suggestions.append(screening)
        
        # Then other matches
        for screening in suggestions:
            if not screening.lower().startswith(query) and screening not in sorted_suggestions:
                sorted_suggestions.append(screening)
        
        return sorted_suggestions[:limit]
    
    def search_screenings(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for screening names based on query string
        
        Args:
            query: Search query (screening name or partial name)
            limit: Maximum number of results to return
            
        Returns:
            List of matching screening names
        """
        if not query or len(query) < 2:
            return []
        
        query = query.lower().strip()
        matching_screenings = set()
        
        # Direct substring matches (prioritized)
        for screening_name in self.screening_database:
            if query in screening_name.lower():
                matching_screenings.add(screening_name)
        
        # Word-based search using index
        query_words = query.split()
        for word in query_words:
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word in self.search_index:
                matching_screenings.update(self.search_index[clean_word])
        
        # Convert to list and sort by relevance (exact matches first)
        results = list(matching_screenings)
        
        # Sort by relevance: exact matches first, then by length
        def relevance_score(screening):
            screening_lower = screening.lower()
            if screening_lower == query:
                return 0  # Exact match
            elif screening_lower.startswith(query):
                return 1  # Starts with query
            elif query in screening_lower:
                return 2  # Contains query
            else:
                return 3  # Word match
        
        results.sort(key=relevance_score)
        
        return results[:limit]

# Global instance
screening_autocomplete_service = ScreeningNameAutocomplete()