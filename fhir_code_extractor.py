"""
FHIR Code Extractor
Extracts standard codes (LOINC, CPT, SNOMED) from FHIR resources and matches to screening types
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

from app import db
from models import ScreeningType


@dataclass
class ExtractedCode:
    """Represents an extracted FHIR code with metadata"""
    system: str
    code: str
    display: str
    category: str
    resource_type: str
    resource_id: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScreeningMatch:
    """Represents a match between extracted codes and screening types"""
    screening_type_id: int
    screening_name: str
    matched_codes: List[ExtractedCode]
    match_strength: float
    match_sources: List[str]
    total_code_matches: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "screening_type_id": self.screening_type_id,
            "screening_name": self.screening_name,
            "matched_codes": [code.to_dict() for code in self.matched_codes],
            "match_strength": self.match_strength,
            "match_sources": self.match_sources,
            "total_code_matches": self.total_code_matches
        }


class FHIRCodeExtractor:
    """
    Extracts standard medical codes from FHIR resources and matches to screening types
    """
    
    def __init__(self):
        # Standard coding systems with weights
        self.coding_systems = {
            'http://loinc.org': {'name': 'LOINC', 'weight': 1.0},
            'http://www.ama-assn.org/go/cpt': {'name': 'CPT', 'weight': 1.0},
            'http://snomed.info/sct': {'name': 'SNOMED CT', 'weight': 1.0},
            'http://hl7.org/fhir/sid/icd-10-cm': {'name': 'ICD-10-CM', 'weight': 0.9},
            'http://terminology.hl7.org/CodeSystem/observation-category': {'name': 'HL7 Observation Category', 'weight': 0.8},
            'http://terminology.hl7.org/CodeSystem/v3-ActCode': {'name': 'HL7 ActCode', 'weight': 0.7},
            'USER_CODING_SYSTEM': {'name': 'User Defined', 'weight': 0.6}
        }
        
        # FHIR resource processors
        self.resource_processors = {
            'Observation': self._extract_observation_codes,
            'Procedure': self._extract_procedure_codes,
            'DocumentReference': self._extract_document_reference_codes
        }
        
        # Category mappings for different resource types
        self.category_mappings = {
            'Observation': {
                'laboratory': 'diagnostic',
                'vital-signs': 'monitoring',
                'imaging': 'diagnostic',
                'procedure': 'procedural',
                'survey': 'assessment',
                'exam': 'clinical',
                'therapy': 'therapeutic'
            },
            'Procedure': {
                'surgical': 'procedural',
                'diagnostic': 'diagnostic',
                'therapeutic': 'therapeutic',
                'administrative': 'administrative'
            },
            'DocumentReference': {
                'clinical-note': 'clinical',
                'summary': 'clinical',
                'report': 'diagnostic',
                'discharge-summary': 'clinical'
            }
        }
    
    def extract_codes_from_fhir_resource(self, fhir_resource: Dict[str, Any]) -> List[ExtractedCode]:
        """
        Extract all standard codes from a FHIR resource
        
        Args:
            fhir_resource: FHIR resource dictionary
            
        Returns:
            List of ExtractedCode objects
        """
        resource_type = fhir_resource.get('resourceType')
        resource_id = fhir_resource.get('id', 'unknown')
        
        if resource_type not in self.resource_processors:
            return []
        
        processor = self.resource_processors[resource_type]
        return processor(fhir_resource, resource_id)
    
    def extract_codes_from_fhir_bundle(self, fhir_bundle: Dict[str, Any]) -> List[ExtractedCode]:
        """
        Extract codes from all resources in a FHIR Bundle
        
        Args:
            fhir_bundle: FHIR Bundle resource
            
        Returns:
            List of all extracted codes
        """
        all_codes = []
        
        if fhir_bundle.get('resourceType') != 'Bundle':
            return all_codes
        
        entries = fhir_bundle.get('entry', [])
        
        for entry in entries:
            resource = entry.get('resource', {})
            codes = self.extract_codes_from_fhir_resource(resource)
            all_codes.extend(codes)
        
        return all_codes
    
    def match_codes_to_screening_types(self, extracted_codes: List[ExtractedCode]) -> List[ScreeningMatch]:
        """
        Match extracted codes to known screening types
        
        Args:
            extracted_codes: List of extracted FHIR codes
            
        Returns:
            List of ScreeningMatch objects
        """
        # Get all screening types with trigger conditions
        screening_types = ScreeningType.query.all()
        matches = []
        
        for screening_type in screening_types:
            match = self._match_codes_to_screening_type(extracted_codes, screening_type)
            if match and match.total_code_matches > 0:
                matches.append(match)
        
        # Sort by match strength
        matches.sort(key=lambda x: x.match_strength, reverse=True)
        return matches
    
    def _extract_observation_codes(self, resource: Dict[str, Any], resource_id: str) -> List[ExtractedCode]:
        """Extract codes from FHIR Observation resource"""
        codes = []
        
        # Extract primary code
        code_element = resource.get('code', {})
        codes.extend(self._extract_codes_from_codeableconcept(
            code_element, 'observation', 'Observation', resource_id
        ))
        
        # Extract category codes
        categories = resource.get('category', [])
        for category in categories:
            codes.extend(self._extract_codes_from_codeableconcept(
                category, 'category', 'Observation', resource_id
            ))
        
        # Extract value codes if present
        value_codeable_concept = resource.get('valueCodeableConcept', {})
        if value_codeable_concept:
            codes.extend(self._extract_codes_from_codeableconcept(
                value_codeable_concept, 'value', 'Observation', resource_id
            ))
        
        # Extract component codes
        components = resource.get('component', [])
        for component in components:
            component_code = component.get('code', {})
            codes.extend(self._extract_codes_from_codeableconcept(
                component_code, 'component', 'Observation', resource_id
            ))
        
        return codes
    
    def _extract_procedure_codes(self, resource: Dict[str, Any], resource_id: str) -> List[ExtractedCode]:
        """Extract codes from FHIR Procedure resource"""
        codes = []
        
        # Extract primary procedure code
        code_element = resource.get('code', {})
        codes.extend(self._extract_codes_from_codeableconcept(
            code_element, 'procedure', 'Procedure', resource_id
        ))
        
        # Extract category codes
        category = resource.get('category', {})
        if category:
            codes.extend(self._extract_codes_from_codeableconcept(
                category, 'category', 'Procedure', resource_id
            ))
        
        # Extract reason codes
        reason_codes = resource.get('reasonCode', [])
        for reason_code in reason_codes:
            codes.extend(self._extract_codes_from_codeableconcept(
                reason_code, 'reason', 'Procedure', resource_id
            ))
        
        return codes
    
    def _extract_document_reference_codes(self, resource: Dict[str, Any], resource_id: str) -> List[ExtractedCode]:
        """Extract codes from FHIR DocumentReference resource"""
        codes = []
        
        # Extract type codes
        type_element = resource.get('type', {})
        codes.extend(self._extract_codes_from_codeableconcept(
            type_element, 'document-type', 'DocumentReference', resource_id
        ))
        
        # Extract category codes
        categories = resource.get('category', [])
        for category in categories:
            codes.extend(self._extract_codes_from_codeableconcept(
                category, 'category', 'DocumentReference', resource_id
            ))
        
        # Extract context codes
        context = resource.get('context', {})
        practice_setting = context.get('practiceSetting', {})
        if practice_setting:
            codes.extend(self._extract_codes_from_codeableconcept(
                practice_setting, 'practice-setting', 'DocumentReference', resource_id
            ))
        
        facility_type = context.get('facilityType', {})
        if facility_type:
            codes.extend(self._extract_codes_from_codeableconcept(
                facility_type, 'facility-type', 'DocumentReference', resource_id
            ))
        
        return codes
    
    def _extract_codes_from_codeableconcept(self, codeable_concept: Dict[str, Any], 
                                          category: str, resource_type: str, 
                                          resource_id: str) -> List[ExtractedCode]:
        """Extract codes from a FHIR CodeableConcept"""
        codes = []
        
        if not codeable_concept:
            return codes
        
        # Extract from coding array
        codings = codeable_concept.get('coding', [])
        for coding in codings:
            system = coding.get('system', '')
            code = coding.get('code', '')
            display = coding.get('display', '')
            
            if system and code:
                # Calculate confidence based on coding system
                confidence = self.coding_systems.get(system, {'weight': 0.5})['weight']
                
                extracted_code = ExtractedCode(
                    system=system,
                    code=code,
                    display=display,
                    category=category,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    confidence=confidence
                )
                codes.append(extracted_code)
        
        # Extract from text if no codings
        if not codings and codeable_concept.get('text'):
            text_code = ExtractedCode(
                system='text',
                code=codeable_concept['text'],
                display=codeable_concept['text'],
                category=category,
                resource_type=resource_type,
                resource_id=resource_id,
                confidence=0.3
            )
            codes.append(text_code)
        
        return codes
    
    def _match_codes_to_screening_type(self, extracted_codes: List[ExtractedCode], 
                                     screening_type: ScreeningType) -> Optional[ScreeningMatch]:
        """Match extracted codes to a specific screening type"""
        matched_codes = []
        match_sources = []
        
        # Get trigger conditions for this screening type
        trigger_conditions = []
        if hasattr(screening_type, 'trigger_conditions') and screening_type.trigger_conditions:
            try:
                trigger_conditions = json.loads(screening_type.trigger_conditions)
            except (json.JSONDecodeError, TypeError):
                trigger_conditions = []
        
        # Match against trigger conditions
        for extracted_code in extracted_codes:
            for trigger in trigger_conditions:
                if self._codes_match(extracted_code, trigger):
                    matched_codes.append(extracted_code)
                    source = f"{extracted_code.system}:{extracted_code.code}"
                    if source not in match_sources:
                        match_sources.append(source)
        
        # Calculate match strength
        if matched_codes:
            # Base strength on number of matches and confidence
            match_strength = sum(code.confidence for code in matched_codes) / len(matched_codes)
            match_strength *= min(1.0, len(matched_codes) / 3.0)  # Boost for multiple matches
            
            return ScreeningMatch(
                screening_type_id=screening_type.id,
                screening_name=screening_type.name,
                matched_codes=matched_codes,
                match_strength=match_strength,
                match_sources=match_sources,
                total_code_matches=len(matched_codes)
            )
        
        return None
    
    def _codes_match(self, extracted_code: ExtractedCode, trigger: Dict[str, Any]) -> bool:
        """Check if an extracted code matches a trigger condition"""
        trigger_system = trigger.get('system', '')
        trigger_code = trigger.get('code', '')
        
        # Exact match
        if extracted_code.system == trigger_system and extracted_code.code == trigger_code:
            return True
        
        # System-agnostic match for same code
        if extracted_code.code == trigger_code:
            return True
        
        # Display text match
        trigger_display = trigger.get('display', '').lower()
        extracted_display = extracted_code.display.lower()
        if trigger_display and extracted_display and trigger_display in extracted_display:
            return True
        
        return False
    
    def generate_code_summary(self, extracted_codes: List[ExtractedCode]) -> Dict[str, Any]:
        """Generate summary statistics for extracted codes"""
        summary = {
            'total_codes': len(extracted_codes),
            'by_system': defaultdict(int),
            'by_resource_type': defaultdict(int),
            'by_category': defaultdict(int),
            'high_confidence_codes': 0,
            'unique_systems': set(),
            'unique_codes': set()
        }
        
        for code in extracted_codes:
            system_name = self.coding_systems.get(code.system, {'name': 'Unknown'})['name']
            summary['by_system'][system_name] += 1
            summary['by_resource_type'][code.resource_type] += 1
            summary['by_category'][code.category] += 1
            summary['unique_systems'].add(system_name)
            summary['unique_codes'].add(f"{code.system}:{code.code}")
            
            if code.confidence >= 0.8:
                summary['high_confidence_codes'] += 1
        
        # Convert sets to lists for JSON serialization
        summary['unique_systems'] = list(summary['unique_systems'])
        summary['unique_codes'] = list(summary['unique_codes'])
        summary['by_system'] = dict(summary['by_system'])
        summary['by_resource_type'] = dict(summary['by_resource_type'])
        summary['by_category'] = dict(summary['by_category'])
        
        return summary


def extract_codes_from_fhir_resource(fhir_resource: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convenience function to extract codes from a single FHIR resource
    
    Args:
        fhir_resource: FHIR resource dictionary
        
    Returns:
        List of extracted code dictionaries
    """
    extractor = FHIRCodeExtractor()
    codes = extractor.extract_codes_from_fhir_resource(fhir_resource)
    return [code.to_dict() for code in codes]


def extract_and_match_codes(fhir_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract codes from FHIR data and match to screening types
    
    Args:
        fhir_data: FHIR resource or Bundle
        
    Returns:
        Dictionary with extracted codes and screening matches
    """
    extractor = FHIRCodeExtractor()
    
    # Extract codes
    if fhir_data.get('resourceType') == 'Bundle':
        extracted_codes = extractor.extract_codes_from_fhir_bundle(fhir_data)
    else:
        extracted_codes = extractor.extract_codes_from_fhir_resource(fhir_data)
    
    # Match to screening types
    screening_matches = extractor.match_codes_to_screening_types(extracted_codes)
    
    # Generate summary
    code_summary = extractor.generate_code_summary(extracted_codes)
    
    return {
        'extracted_codes': [code.to_dict() for code in extracted_codes],
        'screening_matches': [match.to_dict() for match in screening_matches],
        'summary': code_summary,
        'total_extracted_codes': len(extracted_codes),
        'total_screening_matches': len(screening_matches)
    }


def demo_fhir_code_extraction():
    """Demonstrate FHIR code extraction and screening matching"""
    
    # Sample FHIR Observation for HbA1c test
    sample_observation = {
        "resourceType": "Observation",
        "id": "hba1c-test-123",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "4548-4",
                    "display": "Hemoglobin A1c/Hemoglobin.total in Blood"
                }
            ]
        },
        "valueQuantity": {
            "value": 7.2,
            "unit": "%",
            "system": "http://unitsofmeasure.org",
            "code": "%"
        }
    }
    
    # Sample FHIR Procedure for colonoscopy
    sample_procedure = {
        "resourceType": "Procedure",
        "id": "colonoscopy-456",
        "status": "completed",
        "category": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "387713003",
                    "display": "Surgical procedure"
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://www.ama-assn.org/go/cpt",
                    "code": "45378",
                    "display": "Colonoscopy, flexible, proximal to splenic flexure"
                },
                {
                    "system": "http://snomed.info/sct", 
                    "code": "73761001",
                    "display": "Colonoscopy"
                }
            ]
        }
    }
    
    # Sample FHIR DocumentReference
    sample_document = {
        "resourceType": "DocumentReference",
        "id": "lab-report-789",
        "status": "current",
        "type": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "11502-2",
                    "display": "Laboratory report"
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                        "code": "clinical-note",
                        "display": "Clinical Note"
                    }
                ]
            }
        ]
    }
    
    print("FHIR CODE EXTRACTION AND SCREENING MATCHING DEMO")
    print("=" * 55)
    
    extractor = FHIRCodeExtractor()
    
    # Test individual resources
    test_resources = [
        ("HbA1c Observation", sample_observation),
        ("Colonoscopy Procedure", sample_procedure),
        ("Lab Report Document", sample_document)
    ]
    
    all_codes = []
    
    for name, resource in test_resources:
        print(f"\n{name}:")
        print("-" * 30)
        
        codes = extractor.extract_codes_from_fhir_resource(resource)
        all_codes.extend(codes)
        
        print(f"Extracted {len(codes)} codes:")
        for code in codes:
            system_name = extractor.coding_systems.get(code.system, {'name': 'Unknown'})['name']
            print(f"  {system_name}: {code.code} - {code.display}")
    
    # Test screening matching
    print(f"\nScreening Type Matching:")
    print("-" * 30)
    
    matches = extractor.match_codes_to_screening_types(all_codes)
    
    if matches:
        for match in matches:
            print(f"  {match.screening_name}:")
            print(f"    Match Strength: {match.match_strength:.2f}")
            print(f"    Matched Codes: {match.total_code_matches}")
            print(f"    Sources: {match.match_sources}")
    else:
        print("  No screening matches found")
    
    # Generate summary
    summary = extractor.generate_code_summary(all_codes)
    print(f"\nExtraction Summary:")
    print("-" * 20)
    print(f"Total Codes: {summary['total_codes']}")
    print(f"High Confidence: {summary['high_confidence_codes']}")
    print(f"Systems: {summary['unique_systems']}")
    print(f"By Resource Type: {summary['by_resource_type']}")


if __name__ == "__main__":
    from app import app
    
    with app.app_context():
        demo_fhir_code_extraction()