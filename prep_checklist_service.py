"""
PrepChecklist Service - Intelligent checklist evaluation with keyword matching
Dynamically evaluates medical data against screening types and keywords
"""

from datetime import datetime, timedelta
import json
import re
from typing import List, Dict, Tuple, Optional, Any
from sqlalchemy import and_, or_
from app import db
from models import Patient, LabResult, ImagingStudy, ConsultReport, HospitalSummary, ScreeningType, Condition
from screening_keyword_manager import ScreeningKeywordManager
from models import (
    PrepChecklistTemplate, PrepChecklistItem, PrepChecklistResult, 
    PrepChecklistConfiguration, PrepChecklistSection, PrepChecklistItemType,
    PrepChecklistMatchStatus
)


class PrepChecklistEvaluator:
    """Evaluates prep checklist items against patient medical data"""
    
    def __init__(self):
        self.keyword_manager = ScreeningKeywordManager()
        self.config = PrepChecklistConfiguration.get_config()
    
    def evaluate_patient_checklist(self, patient_id: int, template_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Evaluate complete checklist for a patient
        
        Args:
            patient_id: Patient ID
            template_id: Optional specific template, uses default if None
            
        Returns:
            Dict with evaluation results
        """
        patient = Patient.query.get_or_404(patient_id)
        
        # Get template
        if template_id:
            template = PrepChecklistTemplate.query.get_or_404(template_id)
        else:
            template = self.config.default_template
            if not template:
                template = self._get_or_create_default_template()
        
        # Get applicable checklist items
        applicable_items = self._get_applicable_items(patient, template)
        
        # Evaluate each item
        results = []
        for item in applicable_items:
            result = self._evaluate_checklist_item(patient, item)
            results.append(result)
        
        # Group results by section
        grouped_results = self._group_results_by_section(results)
        
        # Calculate summary statistics
        summary = self._calculate_summary_stats(results)
        
        return {
            'patient_id': patient_id,
            'template': template,
            'results': results,
            'grouped_results': grouped_results,
            'summary': summary,
            'evaluation_date': datetime.now()
        }
    
    def _get_applicable_items(self, patient: Patient, template: PrepChecklistTemplate) -> List[PrepChecklistItem]:
        """Get checklist items that apply to this patient"""
        applicable_items = []
        
        for item in template.checklist_items:
            if not item.is_active:
                continue
                
            if item.applies_to_patient(patient):
                # Check condition triggers
                if item.item_type == PrepChecklistItemType.CONDITION_TRIGGERED:
                    if self._check_condition_triggers(patient, item):
                        applicable_items.append(item)
                else:
                    applicable_items.append(item)
        
        return sorted(applicable_items, key=lambda x: (x.section.value, x.order_index))
    
    def _check_condition_triggers(self, patient: Patient, item: PrepChecklistItem) -> bool:
        """Check if patient has conditions that trigger this checklist item"""
        if not item.trigger_conditions_list:
            return True
        
        patient_conditions = Condition.query.filter_by(
            patient_id=patient.id, 
            is_active=True
        ).all()
        
        patient_condition_names = [c.name.lower() for c in patient_conditions]
        
        for trigger_condition in item.trigger_conditions_list:
            trigger_lower = trigger_condition.lower()
            if any(trigger_lower in condition_name for condition_name in patient_condition_names):
                return True
        
        return False
    
    def _evaluate_checklist_item(self, patient: Patient, item: PrepChecklistItem) -> PrepChecklistResult:
        """Evaluate a single checklist item against patient data"""
        # Check if we already have a recent result
        existing_result = PrepChecklistResult.query.filter_by(
            patient_id=patient.id,
            checklist_item_id=item.id
        ).order_by(PrepChecklistResult.evaluated_at.desc()).first()
        
        if existing_result and self._is_result_recent(existing_result):
            return existing_result
        
        # Create new result
        result = PrepChecklistResult(
            patient_id=patient.id,
            template_id=item.template_id,
            checklist_item_id=item.id
        )
        
        # Evaluate based on item type
        if item.item_type == PrepChecklistItemType.SCREENING_TYPE:
            self._evaluate_screening_type_item(patient, item, result)
        elif item.item_type == PrepChecklistItemType.KEYWORD_MATCH:
            self._evaluate_keyword_match_item(patient, item, result)
        elif item.item_type == PrepChecklistItemType.AGE_GENDER_RULE:
            self._evaluate_age_gender_rule_item(patient, item, result)
        else:
            # Default to not checked for custom items
            result.match_status = PrepChecklistMatchStatus.NOT_CHECKED
        
        # Save result
        db.session.add(result)
        db.session.commit()
        
        return result
    
    def _evaluate_screening_type_item(self, patient: Patient, item: PrepChecklistItem, result: PrepChecklistResult):
        """Evaluate checklist item linked to a screening type"""
        if not item.screening_type:
            result.match_status = PrepChecklistMatchStatus.NOT_FOUND
            return
        
        # Use screening type keywords for evaluation
        screening_config = self.keyword_manager.get_keyword_config(item.screening_type_id)
        if not screening_config or not screening_config.keyword_rules:
            result.match_status = PrepChecklistMatchStatus.NOT_FOUND
            return
        
        # Get keywords from screening type
        keywords = [rule.keyword for rule in screening_config.keyword_rules]
        
        # Search in medical data
        matches = self._search_medical_data(patient, keywords, item)
        
        if matches:
            best_match = max(matches, key=lambda x: x['confidence'])
            result.match_status = PrepChecklistMatchStatus.FOUND
            result.confidence_score = best_match['confidence']
            result.matched_data_type = best_match['data_type']
            result.matched_data_id = best_match['data_id']
            result.matched_keywords_list = best_match['matched_keywords']
            result.matched_text_snippet = best_match['text_snippet']
            result.data_date = best_match['data_date']
        else:
            result.match_status = PrepChecklistMatchStatus.NOT_FOUND
            result.confidence_score = 0
    
    def _evaluate_keyword_match_item(self, patient: Patient, item: PrepChecklistItem, result: PrepChecklistResult):
        """Evaluate checklist item using keyword matching"""
        all_keywords = item.primary_keywords_list + item.secondary_keywords_list
        if not all_keywords:
            result.match_status = PrepChecklistMatchStatus.NOT_FOUND
            return
        
        # Search in medical data
        matches = self._search_medical_data(patient, all_keywords, item)
        
        if matches:
            # Filter out matches with excluded keywords
            filtered_matches = []
            for match in matches:
                if not self._contains_excluded_keywords(match['text_snippet'], item.excluded_keywords_list):
                    filtered_matches.append(match)
            
            if filtered_matches:
                best_match = max(filtered_matches, key=lambda x: x['confidence'])
                result.match_status = PrepChecklistMatchStatus.FOUND
                result.confidence_score = best_match['confidence']
                result.matched_data_type = best_match['data_type']
                result.matched_data_id = best_match['data_id']
                result.matched_keywords_list = best_match['matched_keywords']
                result.matched_text_snippet = best_match['text_snippet']
                result.data_date = best_match['data_date']
            else:
                result.match_status = PrepChecklistMatchStatus.NOT_FOUND
        else:
            result.match_status = PrepChecklistMatchStatus.NOT_FOUND
            result.confidence_score = 0
    
    def _evaluate_age_gender_rule_item(self, patient: Patient, item: PrepChecklistItem, result: PrepChecklistResult):
        """Evaluate checklist item based on age/gender rules"""
        applies = item.applies_to_patient(patient)
        
        if applies:
            result.match_status = PrepChecklistMatchStatus.FOUND
            result.confidence_score = 100
            result.matched_text_snippet = f"Patient meets criteria: age {patient.age}, gender {patient.sex}"
        else:
            result.match_status = PrepChecklistMatchStatus.NOT_FOUND
            result.confidence_score = 0
    
    def _search_medical_data(self, patient: Patient, keywords: List[str], item: PrepChecklistItem) -> List[Dict[str, Any]]:
        """Search for keywords in patient's medical data"""
        matches = []
        cutoff_date = datetime.now() - timedelta(days=item.recent_data_days) if item.require_recent_data else None
        
        # Search lab results
        if item.section in [PrepChecklistSection.LABORATORY_RESULTS, PrepChecklistSection.SCREENING_CHECKLIST]:
            lab_matches = self._search_lab_results(patient.id, keywords, cutoff_date)
            matches.extend(lab_matches)
        
        # Search imaging studies
        if item.section in [PrepChecklistSection.IMAGING_STUDIES, PrepChecklistSection.SCREENING_CHECKLIST]:
            imaging_matches = self._search_imaging_studies(patient.id, keywords, cutoff_date)
            matches.extend(imaging_matches)
        
        # Search consult reports
        if item.section in [PrepChecklistSection.CONSULTS_REFERRALS, PrepChecklistSection.SCREENING_CHECKLIST]:
            consult_matches = self._search_consult_reports(patient.id, keywords, cutoff_date)
            matches.extend(consult_matches)
        
        # Search hospital visits
        if item.section in [PrepChecklistSection.HOSPITAL_VISITS, PrepChecklistSection.SCREENING_CHECKLIST]:
            hospital_matches = self._search_hospital_visits(patient.id, keywords, cutoff_date)
            matches.extend(hospital_matches)
        
        return [match for match in matches if match['confidence'] >= item.match_confidence_threshold]
    
    def _search_lab_results(self, patient_id: int, keywords: List[str], cutoff_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Search lab results for keywords"""
        query = LabResult.query.filter_by(patient_id=patient_id)
        if cutoff_date:
            query = query.filter(LabResult.test_date >= cutoff_date)
        
        lab_results = query.all()
        matches = []
        
        for lab in lab_results:
            search_text = f"{lab.test_name} {lab.result} {lab.units or ''} {lab.reference_range or ''}"
            confidence, matched_keywords = self._calculate_keyword_match(search_text, keywords)
            
            if confidence > 0:
                matches.append({
                    'data_type': 'lab',
                    'data_id': lab.id,
                    'confidence': confidence,
                    'matched_keywords': matched_keywords,
                    'text_snippet': search_text[:200],
                    'data_date': lab.test_date
                })
        
        return matches
    
    def _search_imaging_studies(self, patient_id: int, keywords: List[str], cutoff_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Search imaging studies for keywords"""
        query = ImagingStudy.query.filter_by(patient_id=patient_id)
        if cutoff_date:
            query = query.filter(ImagingStudy.study_date >= cutoff_date)
        
        imaging_studies = query.all()
        matches = []
        
        for study in imaging_studies:
            search_text = f"{study.study_type} {study.description or ''} {study.findings or ''} {study.impression or ''}"
            confidence, matched_keywords = self._calculate_keyword_match(search_text, keywords)
            
            if confidence > 0:
                matches.append({
                    'data_type': 'imaging',
                    'data_id': study.id,
                    'confidence': confidence,
                    'matched_keywords': matched_keywords,
                    'text_snippet': search_text[:200],
                    'data_date': study.study_date
                })
        
        return matches
    
    def _search_consult_reports(self, patient_id: int, keywords: List[str], cutoff_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Search consult reports for keywords"""
        query = ConsultReport.query.filter_by(patient_id=patient_id)
        if cutoff_date:
            query = query.filter(ConsultReport.report_date >= cutoff_date)
        
        consult_reports = query.all()
        matches = []
        
        for consult in consult_reports:
            search_text = f"{consult.provider} {consult.specialty} {consult.reason or ''} {consult.recommendations or ''}"
            confidence, matched_keywords = self._calculate_keyword_match(search_text, keywords)
            
            if confidence > 0:
                matches.append({
                    'data_type': 'consult',
                    'data_id': consult.id,
                    'confidence': confidence,
                    'matched_keywords': matched_keywords,
                    'text_snippet': search_text[:200],
                    'data_date': consult.report_date
                })
        
        return matches
    
    def _search_hospital_visits(self, patient_id: int, keywords: List[str], cutoff_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Search hospital visits for keywords"""
        query = HospitalSummary.query.filter_by(patient_id=patient_id)
        if cutoff_date:
            query = query.filter(HospitalSummary.admission_date >= cutoff_date)
        
        hospital_visits = query.all()
        matches = []
        
        for visit in hospital_visits:
            search_text = f"{visit.facility} {visit.visit_type} {visit.diagnosis or ''} {visit.discharge_summary or ''}"
            confidence, matched_keywords = self._calculate_keyword_match(search_text, keywords)
            
            if confidence > 0:
                matches.append({
                    'data_type': 'hospital',
                    'data_id': visit.id,
                    'confidence': confidence,
                    'matched_keywords': matched_keywords,
                    'text_snippet': search_text[:200],
                    'data_date': visit.admission_date
                })
        
        return matches
    
    def _calculate_keyword_match(self, text: str, keywords: List[str]) -> Tuple[int, List[str]]:
        """Calculate confidence score and matched keywords for text"""
        text_lower = text.lower()
        matched_keywords = []
        total_score = 0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                matched_keywords.append(keyword)
                # Higher score for exact matches, partial score for partial matches
                if re.search(r'\b' + re.escape(keyword_lower) + r'\b', text_lower):
                    total_score += 20  # Exact word match
                else:
                    total_score += 10  # Partial match
        
        # Normalize score to 0-100 range
        max_possible_score = len(keywords) * 20
        confidence = min(100, (total_score / max_possible_score * 100)) if max_possible_score > 0 else 0
        
        return int(confidence), matched_keywords
    
    def _contains_excluded_keywords(self, text: str, excluded_keywords: List[str]) -> bool:
        """Check if text contains any excluded keywords"""
        if not excluded_keywords:
            return False
        
        text_lower = text.lower()
        for excluded in excluded_keywords:
            if excluded.lower() in text_lower:
                return True
        return False
    
    def _is_result_recent(self, result: PrepChecklistResult) -> bool:
        """Check if evaluation result is recent enough to reuse"""
        age_hours = (datetime.now() - result.evaluated_at).total_seconds() / 3600
        return age_hours < 24  # Results valid for 24 hours
    
    def _group_results_by_section(self, results: List[PrepChecklistResult]) -> Dict[str, List[PrepChecklistResult]]:
        """Group results by prep sheet section"""
        grouped = {}
        for result in results:
            section = result.checklist_item.section.value
            if section not in grouped:
                grouped[section] = []
            grouped[section].append(result)
        return grouped
    
    def _calculate_summary_stats(self, results: List[PrepChecklistResult]) -> Dict[str, Any]:
        """Calculate summary statistics for checklist evaluation"""
        total_items = len(results)
        found_items = len([r for r in results if r.match_status == PrepChecklistMatchStatus.FOUND])
        not_found_items = len([r for r in results if r.match_status == PrepChecklistMatchStatus.NOT_FOUND])
        needs_review_items = len([r for r in results if r.match_status == PrepChecklistMatchStatus.NEEDS_REVIEW])
        
        avg_confidence = sum(r.confidence_score for r in results if r.confidence_score) / max(1, len([r for r in results if r.confidence_score]))
        
        return {
            'total_items': total_items,
            'found_items': found_items,
            'not_found_items': not_found_items,
            'needs_review_items': needs_review_items,
            'completion_percentage': (found_items / total_items * 100) if total_items > 0 else 0,
            'average_confidence': int(avg_confidence)
        }
    
    def _get_or_create_default_template(self) -> PrepChecklistTemplate:
        """Get or create the default prep checklist template"""
        template = PrepChecklistTemplate.query.filter_by(is_default=True).first()
        
        if not template:
            template = self._create_default_template()
        
        return template
    
    def _create_default_template(self) -> PrepChecklistTemplate:
        """Create a default prep checklist template based on existing screening types"""
        template = PrepChecklistTemplate(
            name="Default Prep Checklist",
            description="Auto-generated template based on screening types and common prep sheet sections",
            is_default=True,
            is_active=True
        )
        db.session.add(template)
        db.session.flush()  # Get the ID
        
        # Create items for each screening type
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        for i, screening_type in enumerate(screening_types):
            item = PrepChecklistItem(
                template_id=template.id,
                section=PrepChecklistSection.SCREENING_CHECKLIST,
                item_type=PrepChecklistItemType.SCREENING_TYPE,
                title=screening_type.name,
                description=f"Check for {screening_type.name} in medical records",
                order_index=i,
                screening_type_id=screening_type.id,
                min_age=screening_type.min_age,
                max_age=screening_type.max_age,
                gender_specific=screening_type.gender_specific,
                is_required=True,
                show_in_summary=True,
                priority_level=1
            )
            db.session.add(item)
        
        # Add some common demographic-based items
        common_items = [
            {
                'title': 'Annual Physical Exam',
                'section': PrepChecklistSection.SCREENING_CHECKLIST,
                'item_type': PrepChecklistItemType.KEYWORD_MATCH,
                'primary_keywords': ['annual exam', 'physical exam', 'wellness visit', 'preventive care'],
                'min_age': 18
            },
            {
                'title': 'Vaccination History',
                'section': PrepChecklistSection.IMMUNIZATIONS,
                'item_type': PrepChecklistItemType.KEYWORD_MATCH,
                'primary_keywords': ['vaccination', 'vaccine', 'immunization', 'flu shot', 'covid vaccine']
            },
            {
                'title': 'Blood Pressure Check',
                'section': PrepChecklistSection.VITAL_SIGNS,
                'item_type': PrepChecklistItemType.KEYWORD_MATCH,
                'primary_keywords': ['blood pressure', 'BP', 'hypertension', 'systolic', 'diastolic'],
                'min_age': 18
            }
        ]
        
        for i, item_data in enumerate(common_items):
            item = PrepChecklistItem(
                template_id=template.id,
                section=item_data['section'],
                item_type=item_data['item_type'],
                title=item_data['title'],
                description=f"Check for {item_data['title']} documentation",
                order_index=len(screening_types) + i,
                primary_keywords=json.dumps(item_data.get('primary_keywords', [])),
                min_age=item_data.get('min_age'),
                max_age=item_data.get('max_age'),
                gender_specific=item_data.get('gender_specific'),
                is_required=False,
                show_in_summary=True,
                priority_level=2
            )
            db.session.add(item)
        
        db.session.commit()
        
        # Set as default template in configuration
        config = PrepChecklistConfiguration.get_config()
        config.default_template_id = template.id
        db.session.commit()
        
        return template


class PrepChecklistManager:
    """Manager for prep checklist templates and configuration"""
    
    def __init__(self):
        self.evaluator = PrepChecklistEvaluator()
    
    def sync_with_screening_types(self):
        """Sync checklist templates with current screening types"""
        config = PrepChecklistConfiguration.get_config()
        if not config.sync_with_screening_types:
            return
        
        default_template = config.default_template
        if not default_template:
            return
        
        # Get existing screening type items
        existing_items = PrepChecklistItem.query.filter_by(
            template_id=default_template.id,
            item_type=PrepChecklistItemType.SCREENING_TYPE
        ).all()
        
        existing_screening_ids = {item.screening_type_id for item in existing_items}
        
        # Get all active screening types
        active_screening_types = ScreeningType.query.filter_by(is_active=True).all()
        active_screening_ids = {st.id for st in active_screening_types}
        
        # Add new screening types
        new_screening_ids = active_screening_ids - existing_screening_ids
        for screening_type in active_screening_types:
            if screening_type.id in new_screening_ids:
                self._create_screening_type_item(default_template, screening_type)
        
        # Deactivate items for removed screening types
        removed_screening_ids = existing_screening_ids - active_screening_ids
        for item in existing_items:
            if item.screening_type_id in removed_screening_ids:
                item.is_active = False
        
        db.session.commit()
    
    def _create_screening_type_item(self, template: PrepChecklistTemplate, screening_type: ScreeningType):
        """Create a checklist item for a screening type"""
        max_order = db.session.query(db.func.max(PrepChecklistItem.order_index)).filter_by(
            template_id=template.id
        ).scalar() or 0
        
        item = PrepChecklistItem(
            template_id=template.id,
            section=PrepChecklistSection.SCREENING_CHECKLIST,
            item_type=PrepChecklistItemType.SCREENING_TYPE,
            title=screening_type.name,
            description=f"Check for {screening_type.name} in medical records",
            order_index=max_order + 1,
            screening_type_id=screening_type.id,
            min_age=screening_type.min_age,
            max_age=screening_type.max_age,
            gender_specific=screening_type.gender_specific,
            is_required=True,
            show_in_summary=True,
            priority_level=1
        )
        db.session.add(item)
        return item