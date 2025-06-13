"""
FHIR Condition-Based Screening Trigger System
Checks patient conditions against screening type trigger conditions during prep generation
"""

import json
from typing import List, Dict, Any, Set
from datetime import datetime

from app import db
from models import Patient, MedicalCondition, ScreeningType, Screening
from fhir_object_mappers import FHIRObjectMapper


class ConditionScreeningMatcher:
    """
    Matches patient conditions to screening requirements using FHIR condition codes
    """
    
    def __init__(self):
        self.fhir_mapper = FHIRObjectMapper()
    
    def get_patient_condition_codes(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Extract all FHIR condition codes for a patient
        
        Args:
            patient_id: Patient ID
            
        Returns:
            List of condition codes with system and code information
        """
        patient = Patient.query.get(patient_id)
        if not patient:
            return []
        
        condition_codes = []
        
        # Get all medical conditions for the patient
        conditions = MedicalCondition.query.filter_by(patient_id=patient_id).all()
        
        for condition in conditions:
            # Convert condition to FHIR format
            fhir_condition = self.fhir_mapper.map_condition_to_fhir(condition)
            
            # Extract coding information
            if 'code' in fhir_condition and 'coding' in fhir_condition['code']:
                for coding in fhir_condition['code']['coding']:
                    condition_codes.append({
                        'system': coding.get('system'),
                        'code': coding.get('code'),
                        'display': coding.get('display'),
                        'condition_id': condition.id,
                        'condition_name': condition.condition_name,
                        'diagnosis_date': condition.diagnosis_date.isoformat() if condition.diagnosis_date else None
                    })
        
        return condition_codes
    
    def find_triggered_screenings(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Find all screening types that should be triggered based on patient's conditions
        
        Args:
            patient_id: Patient ID
            
        Returns:
            List of triggered screening recommendations with details
        """
        patient = Patient.query.get(patient_id)
        if not patient:
            return []
        
        # Get all patient condition codes
        patient_condition_codes = self.get_patient_condition_codes(patient_id)
        
        if not patient_condition_codes:
            return []
        
        # Get all active screening types with trigger conditions
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        
        triggered_screenings = []
        
        for screening_type in screening_types:
            trigger_conditions = screening_type.get_trigger_conditions()
            
            if not trigger_conditions:
                continue
            
            # Check if any patient condition matches trigger conditions
            matched_conditions = []
            
            for patient_condition in patient_condition_codes:
                for trigger_condition in trigger_conditions:
                    if self._codes_match(patient_condition, trigger_condition):
                        matched_conditions.append({
                            'patient_condition': patient_condition,
                            'trigger_condition': trigger_condition
                        })
            
            if matched_conditions:
                # Check if screening is appropriate for patient demographics
                if self._screening_appropriate_for_patient(screening_type, patient):
                    # Check if screening is already completed or scheduled
                    existing_screening = self._get_existing_screening(patient_id, screening_type.name)
                    
                    triggered_screenings.append({
                        'screening_type': {
                            'id': screening_type.id,
                            'name': screening_type.name,
                            'description': screening_type.description,
                            'frequency': screening_type.default_frequency
                        },
                        'triggered_by': matched_conditions,
                        'existing_screening': existing_screening,
                        'recommendation_status': self._get_recommendation_status(existing_screening, screening_type),
                        'priority': self._calculate_priority(matched_conditions, screening_type)
                    })
        
        # Sort by priority (high priority first)
        triggered_screenings.sort(key=lambda x: x['priority'], reverse=True)
        
        return triggered_screenings
    
    def _codes_match(self, patient_condition: Dict[str, Any], trigger_condition: Dict[str, Any]) -> bool:
        """
        Check if a patient condition code matches a trigger condition
        
        Args:
            patient_condition: Patient condition with system, code, display
            trigger_condition: Trigger condition with system, code, display
            
        Returns:
            bool: True if codes match
        """
        # Direct code match
        if patient_condition.get('code') == trigger_condition.get('code'):
            # If systems are specified, they should match
            patient_system = patient_condition.get('system', '').lower()
            trigger_system = trigger_condition.get('system', '').lower()
            
            if patient_system and trigger_system:
                return patient_system == trigger_system
            else:
                # If no system specified, accept code match
                return True
        
        return False
    
    def _screening_appropriate_for_patient(self, screening_type: ScreeningType, patient: Patient) -> bool:
        """
        Check if screening is appropriate for patient's age and gender
        
        Args:
            screening_type: ScreeningType object
            patient: Patient object
            
        Returns:
            bool: True if screening is appropriate
        """
        # Check age requirements
        if patient.age is not None:
            if screening_type.min_age and patient.age < screening_type.min_age:
                return False
            if screening_type.max_age and patient.age > screening_type.max_age:
                return False
        
        # Check gender requirements
        if screening_type.gender_specific:
            if patient.gender and patient.gender.lower() != screening_type.gender_specific.lower():
                return False
        
        return True
    
    def _get_existing_screening(self, patient_id: int, screening_name: str) -> Dict[str, Any]:
        """
        Get existing screening record for patient
        
        Args:
            patient_id: Patient ID
            screening_name: Name of the screening type
            
        Returns:
            Dict with existing screening information or None
        """
        try:
            # Find most recent screening of this type for the patient
            screening = Screening.query.filter_by(
                patient_id=patient_id,
                screening_type=screening_name
            ).order_by(Screening.due_date.desc()).first()
            
            if screening:
                return {
                    'id': screening.id,
                    'due_date': screening.due_date.isoformat() if screening.due_date else None,
                    'completed_date': screening.completed_date.isoformat() if screening.completed_date else None,
                    'status': screening.status,
                    'notes': screening.notes
                }
        except Exception:
            pass
        
        return None
    
    def _get_recommendation_status(self, existing_screening: Dict[str, Any], screening_type: ScreeningType) -> str:
        """
        Determine recommendation status based on existing screening
        
        Args:
            existing_screening: Existing screening record
            screening_type: ScreeningType object
            
        Returns:
            str: Status like 'due', 'overdue', 'completed', 'scheduled'
        """
        if not existing_screening:
            return 'due'
        
        if existing_screening.get('completed_date'):
            return 'completed'
        
        if existing_screening.get('due_date'):
            try:
                due_date = datetime.fromisoformat(existing_screening['due_date'].replace('Z', '+00:00'))
                if due_date < datetime.now():
                    return 'overdue'
                else:
                    return 'scheduled'
            except (ValueError, TypeError):
                pass
        
        return 'due'
    
    def _calculate_priority(self, matched_conditions: List[Dict[str, Any]], screening_type: ScreeningType) -> int:
        """
        Calculate priority score for screening recommendation
        
        Args:
            matched_conditions: List of matched condition/trigger pairs
            screening_type: ScreeningType object
            
        Returns:
            int: Priority score (higher = more important)
        """
        priority = 0
        
        # Base priority for having matched conditions
        priority += len(matched_conditions) * 10
        
        # Higher priority for chronic disease management screenings
        chronic_keywords = ['diabetes', 'hypertension', 'heart', 'cancer', 'kidney']
        if any(keyword in screening_type.name.lower() for keyword in chronic_keywords):
            priority += 20
        
        # Higher priority for preventive screenings
        preventive_keywords = ['screening', 'colonoscopy', 'mammogram', 'pap']
        if any(keyword in screening_type.name.lower() for keyword in preventive_keywords):
            priority += 15
        
        return priority
    
    def generate_condition_triggered_recommendations(self, patient_id: int) -> Dict[str, Any]:
        """
        Generate comprehensive condition-triggered screening recommendations for prep sheet
        
        Args:
            patient_id: Patient ID
            
        Returns:
            Dict with recommendation details for prep sheet inclusion
        """
        triggered_screenings = self.find_triggered_screenings(patient_id)
        
        if not triggered_screenings:
            return {
                'has_triggered_screenings': False,
                'total_triggered': 0,
                'recommendations': []
            }
        
        # Group recommendations by status
        recommendations_by_status = {
            'due': [],
            'overdue': [],
            'scheduled': [],
            'completed': []
        }
        
        for screening in triggered_screenings:
            status = screening['recommendation_status']
            recommendations_by_status[status].append(screening)
        
        return {
            'has_triggered_screenings': True,
            'total_triggered': len(triggered_screenings),
            'recommendations': triggered_screenings,
            'by_status': recommendations_by_status,
            'summary': {
                'due_count': len(recommendations_by_status['due']),
                'overdue_count': len(recommendations_by_status['overdue']),
                'scheduled_count': len(recommendations_by_status['scheduled']),
                'completed_count': len(recommendations_by_status['completed'])
            },
            'generation_timestamp': datetime.now().isoformat()
        }


def add_condition_triggered_screenings_to_prep_sheet(patient_id: int, prep_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add condition-triggered screening recommendations to prep sheet data
    
    Args:
        patient_id: Patient ID
        prep_data: Existing prep sheet data
        
    Returns:
        Enhanced prep sheet data with condition-triggered screenings
    """
    try:
        matcher = ConditionScreeningMatcher()
        recommendations = matcher.generate_condition_triggered_recommendations(patient_id)
        
        # Add to prep sheet data
        prep_data['condition_triggered_screenings'] = recommendations
        
        # Add summary to main prep sheet sections if there are triggered screenings
        if recommendations['has_triggered_screenings']:
            if 'screening_recommendations' not in prep_data:
                prep_data['screening_recommendations'] = []
            
            # Add high-priority triggered screenings to main recommendations
            high_priority_screenings = [
                s for s in recommendations['recommendations'] 
                if s['priority'] >= 30 and s['recommendation_status'] in ['due', 'overdue']
            ]
            
            for screening in high_priority_screenings:
                prep_data['screening_recommendations'].append({
                    'type': 'condition_triggered',
                    'name': screening['screening_type']['name'],
                    'description': screening['screening_type']['description'],
                    'triggered_by': [match['patient_condition']['condition_name'] for match in screening['triggered_by']],
                    'status': screening['recommendation_status'],
                    'priority': screening['priority']
                })
        
        return prep_data
        
    except Exception as e:
        # Log error but don't break prep sheet generation
        print(f"Error adding condition-triggered screenings: {str(e)}")
        return prep_data


# Example screening type configurations with trigger conditions
EXAMPLE_SCREENING_CONFIGURATIONS = {
    "diabetes_management": {
        "name": "Diabetes Management Screening",
        "description": "Comprehensive diabetes monitoring including HbA1c, eye exam, and foot exam",
        "trigger_conditions": [
            {
                "system": "http://snomed.info/sct",
                "code": "73211009",
                "display": "Diabetes mellitus"
            },
            {
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": "E11.9",
                "display": "Type 2 diabetes mellitus without complications"
            },
            {
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": "E10.9",
                "display": "Type 1 diabetes mellitus without complications"
            }
        ]
    },
    "hypertension_monitoring": {
        "name": "Hypertension Monitoring",
        "description": "Blood pressure monitoring and cardiovascular risk assessment",
        "trigger_conditions": [
            {
                "system": "http://snomed.info/sct",
                "code": "38341003",
                "display": "Hypertensive disorder"
            },
            {
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": "I10",
                "display": "Essential hypertension"
            }
        ]
    },
    "cancer_screening": {
        "name": "Enhanced Cancer Screening",
        "description": "Additional cancer screening for high-risk patients",
        "trigger_conditions": [
            {
                "system": "http://snomed.info/sct",
                "code": "395557000",
                "display": "Family history of malignant neoplasm"
            },
            {
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": "Z80.9",
                "display": "Family history of malignant neoplasm, unspecified"
            }
        ]
    }
}