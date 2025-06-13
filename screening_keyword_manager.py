"""
Screening Keyword Manager
Allows users to define screening-specific keyword rules with document section associations
"""

import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

from app import db
from models import ScreeningType


@dataclass
class KeywordRule:
    """Represents a user-defined keyword rule for screening matching"""
    keyword: str
    section: str  # 'labs', 'imaging', 'consults', 'vitals', 'general'
    weight: float
    case_sensitive: bool
    exact_match: bool
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScreeningKeywordConfig:
    """Complete keyword configuration for a screening type"""
    screening_type_id: int
    screening_name: str
    keyword_rules: List[KeywordRule]
    section_weights: Dict[str, float]
    fallback_enabled: bool
    confidence_threshold: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "screening_type_id": self.screening_type_id,
            "screening_name": self.screening_name,
            "keyword_rules": [rule.to_dict() for rule in self.keyword_rules],
            "section_weights": self.section_weights,
            "fallback_enabled": self.fallback_enabled,
            "confidence_threshold": self.confidence_threshold
        }


class ScreeningKeywordManager:
    """
    Manages user-defined keyword rules for screening types
    """
    
    def __init__(self):
        # Default section weights
        self.default_section_weights = {
            'labs': 1.0,
            'imaging': 0.9,
            'consults': 0.8,
            'vitals': 0.7,
            'procedures': 0.9,
            'medications': 0.6,
            'general': 0.5
        }
        
        # Common medical paraphrases for sections
        self.section_paraphrases = {
            'labs': [
                'laboratory', 'lab results', 'blood work', 'urine test',
                'pathology', 'biopsy', 'culture', 'chemistry',
                'hematology', 'serology', 'microbiology'
            ],
            'imaging': [
                'radiology', 'x-ray', 'xray', 'ct scan', 'mri',
                'ultrasound', 'mammogram', 'echo', 'nuclear medicine',
                'pet scan', 'fluoroscopy', 'angiogram'
            ],
            'consults': [
                'consultation', 'specialist', 'referral', 'opinion',
                'cardiology', 'neurology', 'orthopedic', 'dermatology',
                'psychiatry', 'oncology', 'endocrinology'
            ],
            'vitals': [
                'vital signs', 'blood pressure', 'heart rate', 'pulse',
                'temperature', 'weight', 'height', 'bmi'
            ],
            'procedures': [
                'procedure', 'surgery', 'operation', 'endoscopy',
                'biopsy', 'catheterization', 'injection'
            ],
            'medications': [
                'medication', 'prescription', 'drug', 'pharmacy',
                'dosage', 'rx', 'medication list'
            ]
        }
    
    def add_keyword_rule(self, screening_type_id: int, keyword: str, section: str,
                        weight: float = 1.0, case_sensitive: bool = False,
                        exact_match: bool = False, description: str = "") -> bool:
        """
        Add a keyword rule to a screening type
        
        Args:
            screening_type_id: ID of the screening type
            keyword: Keyword to match
            section: Document section ('labs', 'imaging', etc.)
            weight: Weight for this keyword (0.0-1.0)
            case_sensitive: Whether matching is case sensitive
            exact_match: Whether to require exact word match
            description: User description of the rule
            
        Returns:
            True if successfully added
        """
        screening_type = ScreeningType.query.get(screening_type_id)
        if not screening_type:
            return False
        
        # Get existing keyword configuration
        config = self.get_keyword_config(screening_type_id)
        if not config:
            config = ScreeningKeywordConfig(
                screening_type_id=screening_type_id,
                screening_name=screening_type.name,
                keyword_rules=[],
                section_weights=self.default_section_weights.copy(),
                fallback_enabled=True,
                confidence_threshold=0.3
            )
        
        # Add new keyword rule
        new_rule = KeywordRule(
            keyword=keyword.strip(),
            section=section,
            weight=max(0.0, min(1.0, weight)),
            case_sensitive=case_sensitive,
            exact_match=exact_match,
            description=description
        )
        
        # Check for duplicates
        for existing_rule in config.keyword_rules:
            if (existing_rule.keyword.lower() == new_rule.keyword.lower() and 
                existing_rule.section == new_rule.section):
                # Update existing rule
                existing_rule.weight = new_rule.weight
                existing_rule.case_sensitive = new_rule.case_sensitive
                existing_rule.exact_match = new_rule.exact_match
                existing_rule.description = new_rule.description
                break
        else:
            config.keyword_rules.append(new_rule)
        
        # Save configuration
        return self._save_keyword_config(config)
    
    def remove_keyword_rule(self, screening_type_id: int, keyword: str, section: str) -> bool:
        """Remove a keyword rule from a screening type"""
        config = self.get_keyword_config(screening_type_id)
        if not config:
            return False
        
        config.keyword_rules = [
            rule for rule in config.keyword_rules
            if not (rule.keyword.lower() == keyword.lower() and rule.section == section)
        ]
        
        return self._save_keyword_config(config)
    
    def get_keyword_config(self, screening_type_id: int) -> Optional[ScreeningKeywordConfig]:
        """Get keyword configuration for a screening type"""
        screening_type = ScreeningType.query.get(screening_type_id)
        if not screening_type:
            return None
        
        # Get configuration from document_section_mappings field
        if hasattr(screening_type, 'document_section_mappings') and screening_type.document_section_mappings:
            try:
                config_data = json.loads(screening_type.document_section_mappings)
                
                # Convert to ScreeningKeywordConfig
                keyword_rules = []
                for rule_data in config_data.get('keyword_rules', []):
                    keyword_rules.append(KeywordRule(
                        keyword=rule_data['keyword'],
                        section=rule_data['section'],
                        weight=rule_data['weight'],
                        case_sensitive=rule_data.get('case_sensitive', False),
                        exact_match=rule_data.get('exact_match', False),
                        description=rule_data.get('description', '')
                    ))
                
                return ScreeningKeywordConfig(
                    screening_type_id=screening_type_id,
                    screening_name=screening_type.name,
                    keyword_rules=keyword_rules,
                    section_weights=config_data.get('section_weights', self.default_section_weights),
                    fallback_enabled=config_data.get('fallback_enabled', True),
                    confidence_threshold=config_data.get('confidence_threshold', 0.3)
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        
        return None
    
    def update_section_weights(self, screening_type_id: int, section_weights: Dict[str, float]) -> bool:
        """Update section weights for a screening type"""
        config = self.get_keyword_config(screening_type_id)
        if not config:
            screening_type = ScreeningType.query.get(screening_type_id)
            if not screening_type:
                return False
            
            config = ScreeningKeywordConfig(
                screening_type_id=screening_type_id,
                screening_name=screening_type.name,
                keyword_rules=[],
                section_weights=self.default_section_weights.copy(),
                fallback_enabled=True,
                confidence_threshold=0.3
            )
        
        # Update section weights
        for section, weight in section_weights.items():
            if section in self.default_section_weights:
                config.section_weights[section] = max(0.0, min(1.0, weight))
        
        return self._save_keyword_config(config)
    
    def match_document_with_keywords(self, filename: str, content: str, 
                                   detected_section: str = 'general') -> List[Dict[str, Any]]:
        """
        Match document against all screening keyword rules as fallback
        
        Args:
            filename: Document filename
            content: Document content
            detected_section: Detected document section
            
        Returns:
            List of matching screening configurations with scores
        """
        matches = []
        
        # Get all screening types with keyword configurations
        screening_types = ScreeningType.query.all()
        
        for screening_type in screening_types:
            config = self.get_keyword_config(screening_type.id)
            if not config or not config.fallback_enabled:
                continue
            
            match_score = self._calculate_keyword_match_score(
                filename, content, detected_section, config
            )
            
            if match_score >= config.confidence_threshold:
                matches.append({
                    'screening_type_id': screening_type.id,
                    'screening_name': screening_type.name,
                    'match_score': match_score,
                    'matched_keywords': self._get_matched_keywords(filename, content, config),
                    'section_match': detected_section in config.section_weights,
                    'fallback_source': 'user_keywords'
                })
        
        # Sort by match score
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches
    
    def get_all_keyword_configs(self) -> List[ScreeningKeywordConfig]:
        """Get keyword configurations for all screening types"""
        configs = []
        screening_types = ScreeningType.query.all()
        
        for screening_type in screening_types:
            config = self.get_keyword_config(screening_type.id)
            if config:
                configs.append(config)
        
        return configs
    
    def import_keyword_rules_bulk(self, screening_type_id: int, 
                                 keyword_data: List[Dict[str, Any]]) -> int:
        """
        Import multiple keyword rules at once
        
        Args:
            screening_type_id: ID of the screening type
            keyword_data: List of keyword rule dictionaries
            
        Returns:
            Number of rules successfully imported
        """
        imported_count = 0
        
        for rule_data in keyword_data:
            try:
                success = self.add_keyword_rule(
                    screening_type_id=screening_type_id,
                    keyword=rule_data['keyword'],
                    section=rule_data['section'],
                    weight=rule_data.get('weight', 1.0),
                    case_sensitive=rule_data.get('case_sensitive', False),
                    exact_match=rule_data.get('exact_match', False),
                    description=rule_data.get('description', '')
                )
                if success:
                    imported_count += 1
            except (KeyError, TypeError):
                continue
        
        return imported_count
    
    def export_keyword_rules(self, screening_type_id: int) -> Optional[Dict[str, Any]]:
        """Export keyword configuration for backup or sharing"""
        config = self.get_keyword_config(screening_type_id)
        if not config:
            return None
        
        return config.to_dict()
    
    def suggest_keywords_for_section(self, section: str) -> List[str]:
        """Suggest common keywords for a document section"""
        return self.section_paraphrases.get(section, [])
    
    def _calculate_keyword_match_score(self, filename: str, content: str,
                                     detected_section: str,
                                     config: ScreeningKeywordConfig) -> float:
        """Calculate match score based on keyword rules"""
        if not config.keyword_rules:
            return 0.0
        
        total_score = 0.0
        max_possible_score = 0.0
        
        # Combine filename and content for matching
        full_text = f"{filename} {content}".lower()
        
        for rule in config.keyword_rules:
            max_possible_score += rule.weight
            
            # Prepare keyword for matching
            keyword = rule.keyword if rule.case_sensitive else rule.keyword.lower()
            search_text = f"{filename} {content}" if rule.case_sensitive else full_text
            
            # Check for match
            if rule.exact_match:
                # Word boundary match
                import re
                pattern = r'\b' + re.escape(keyword) + r'\b'
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                match_found = bool(re.search(pattern, search_text, flags))
            else:
                # Substring match
                match_found = keyword in search_text
            
            if match_found:
                # Apply section weight if applicable
                section_weight = config.section_weights.get(rule.section, 0.5)
                if detected_section == rule.section:
                    section_weight *= 1.2  # Boost for section match
                
                total_score += rule.weight * section_weight
        
        # Normalize score
        return min(1.0, total_score / max(max_possible_score, 1.0))
    
    def _get_matched_keywords(self, filename: str, content: str,
                            config: ScreeningKeywordConfig) -> List[str]:
        """Get list of keywords that matched in the document"""
        matched = []
        full_text = f"{filename} {content}".lower()
        
        for rule in config.keyword_rules:
            keyword = rule.keyword if rule.case_sensitive else rule.keyword.lower()
            search_text = f"{filename} {content}" if rule.case_sensitive else full_text
            
            if rule.exact_match:
                import re
                pattern = r'\b' + re.escape(keyword) + r'\b'
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                match_found = bool(re.search(pattern, search_text, flags))
            else:
                match_found = keyword in search_text
            
            if match_found:
                matched.append(f"{rule.section}:{rule.keyword}")
        
        return matched
    
    def _save_keyword_config(self, config: ScreeningKeywordConfig) -> bool:
        """Save keyword configuration to database"""
        try:
            screening_type = ScreeningType.query.get(config.screening_type_id)
            if not screening_type:
                return False
            
            # Save as JSON in document_section_mappings field
            config_json = json.dumps(config.to_dict())
            screening_type.document_section_mappings = config_json
            
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False


def add_screening_keywords(screening_type_id: int, keyword_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convenience function to add multiple keyword rules
    
    Args:
        screening_type_id: ID of the screening type
        keyword_rules: List of keyword rule dictionaries
        
    Returns:
        Results dictionary with success count and errors
    """
    manager = ScreeningKeywordManager()
    
    results = {
        'total_rules': len(keyword_rules),
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for rule in keyword_rules:
        try:
            success = manager.add_keyword_rule(
                screening_type_id=screening_type_id,
                keyword=rule['keyword'],
                section=rule['section'],
                weight=rule.get('weight', 1.0),
                case_sensitive=rule.get('case_sensitive', False),
                exact_match=rule.get('exact_match', False),
                description=rule.get('description', '')
            )
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Failed to add rule: {rule['keyword']}")
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"Error adding {rule.get('keyword', 'unknown')}: {str(e)}")
    
    return results


def demo_keyword_management():
    """Demonstrate keyword management functionality"""
    from app import app
    
    with app.app_context():
        print("SCREENING KEYWORD MANAGEMENT DEMONSTRATION")
        print("=" * 50)
        
        manager = ScreeningKeywordManager()
        
        # Get a screening type for demonstration
        screening_type = ScreeningType.query.first()
        if not screening_type:
            print("No screening types available for demo")
            return
        
        print(f"Working with: {screening_type.name} (ID: {screening_type.id})")
        
        # Add sample keyword rules
        sample_rules = [
            {
                'keyword': 'hemoglobin a1c',
                'section': 'labs',
                'weight': 1.0,
                'case_sensitive': False,
                'exact_match': False,
                'description': 'HbA1c diabetes monitoring test'
            },
            {
                'keyword': 'glucose',
                'section': 'labs',
                'weight': 0.8,
                'case_sensitive': False,
                'exact_match': True,
                'description': 'Blood glucose measurement'
            },
            {
                'keyword': 'diabetes',
                'section': 'general',
                'weight': 0.6,
                'case_sensitive': False,
                'exact_match': False,
                'description': 'General diabetes mention'
            }
        ]
        
        print(f"\nAdding {len(sample_rules)} keyword rules:")
        for rule in sample_rules:
            success = manager.add_keyword_rule(
                screening_type_id=screening_type.id,
                **rule
            )
            status = "✓" if success else "✗"
            print(f"  {status} {rule['keyword']} ({rule['section']})")
        
        # Get configuration
        config = manager.get_keyword_config(screening_type.id)
        if config:
            print(f"\nKeyword Configuration:")
            print(f"  Screening: {config.screening_name}")
            print(f"  Rules: {len(config.keyword_rules)}")
            print(f"  Fallback Enabled: {config.fallback_enabled}")
            print(f"  Confidence Threshold: {config.confidence_threshold}")
            
            print(f"\nKeyword Rules:")
            for rule in config.keyword_rules:
                print(f"  '{rule.keyword}' in {rule.section} (weight: {rule.weight})")
        
        # Test document matching
        test_document = {
            'filename': 'HbA1c_Lab_Results_2024.pdf',
            'content': 'Laboratory report showing hemoglobin a1c level of 7.2% and glucose 145 mg/dL for diabetes monitoring.'
        }
        
        print(f"\nTesting document matching:")
        print(f"  Document: {test_document['filename']}")
        
        matches = manager.match_document_with_keywords(
            filename=test_document['filename'],
            content=test_document['content'],
            detected_section='labs'
        )
        
        if matches:
            for match in matches:
                print(f"  ✓ {match['screening_name']}: {match['match_score']:.2f}")
                print(f"    Matched keywords: {match['matched_keywords']}")
        else:
            print("  No keyword matches found")
        
        # Show section suggestions
        print(f"\nSection keyword suggestions:")
        for section in ['labs', 'imaging', 'consults']:
            suggestions = manager.suggest_keywords_for_section(section)
            print(f"  {section}: {suggestions[:5]}")


if __name__ == "__main__":
    demo_keyword_management()