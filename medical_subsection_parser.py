"""
Medical Subsection Document Parser
Parses documents from specific medical data subsections (labs, imaging, consults, hospital visits)
with configurable date cutoff windows for prep sheet quality checklist
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from app import db
from models import (
    Patient, MedicalDocument, LabResult, ImagingStudy, 
    ConsultReport, HospitalSummary, Appointment
)


@dataclass
class SubsectionParsingResult:
    """Results from parsing medical subsection documents"""
    section_name: str
    documents_found: List[MedicalDocument]
    structured_data_found: List[Any]  # Labs, Imaging, etc.
    parsing_summary: str
    date_range_applied: bool
    cutoff_date: Optional[datetime] = None


class MedicalSubsectionParser:
    """Parse documents and data from specific medical subsections"""
    
    # Document type mapping for each subsection
    SUBSECTION_MAPPINGS = {
        'laboratories': {
            'document_keywords': ['lab', 'laboratory', 'blood', 'urine', 'pathology', 'chemistry', 'hematology'],
            'document_types': ['LAB_REPORT'],
            'structured_model': LabResult,
            'date_field': 'test_date',
            'display_name': 'Laboratory Results'
        },
        'imaging': {
            'document_keywords': ['xray', 'x-ray', 'ct', 'mri', 'ultrasound', 'mammogram', 'nuclear', 'pet', 'scan'],
            'document_types': ['RADIOLOGY_REPORT'],
            'structured_model': ImagingStudy,
            'date_field': 'study_date',
            'display_name': 'Imaging Studies'
        },
        'consults': {
            'document_keywords': ['consult', 'consultation', 'referral', 'specialist', 'cardiology', 'neurology'],
            'document_types': ['CONSULTATION', 'REFERRAL'],
            'structured_model': ConsultReport,
            'date_field': 'report_date',
            'display_name': 'Specialist Consults'
        },
        'hospital_visits': {
            'document_keywords': ['hospital', 'admission', 'discharge', 'inpatient', 'emergency', 'er'],
            'document_types': ['DISCHARGE_SUMMARY'],
            'structured_model': HospitalSummary,
            'date_field': 'admission_date',
            'display_name': 'Hospital Visits'
        }
    }
    
    def __init__(self):
        self.patient_id = None
        self.cutoff_date = None
        
    def parse_subsection_documents(
        self, 
        patient_id: int, 
        subsection: str, 
        cutoff_date: Optional[datetime] = None,
        limit: int = 10
    ) -> SubsectionParsingResult:
        """
        Parse documents and structured data from a specific medical subsection
        
        Args:
            patient_id: Patient ID
            subsection: Medical subsection ('laboratories', 'imaging', 'consults', 'hospital_visits')
            cutoff_date: Only include data after this date
            limit: Maximum number of items to return
            
        Returns:
            SubsectionParsingResult with documents and structured data
        """
        if subsection not in self.SUBSECTION_MAPPINGS:
            raise ValueError(f"Unknown subsection: {subsection}")
            
        mapping = self.SUBSECTION_MAPPINGS[subsection]
        self.patient_id = patient_id
        self.cutoff_date = cutoff_date
        
        # Find relevant documents
        documents = self._find_subsection_documents(
            patient_id, mapping, cutoff_date, limit
        )
        
        # Find structured data
        structured_data = self._find_structured_data(
            patient_id, mapping, cutoff_date, limit
        )
        
        # Generate summary
        summary = self._generate_parsing_summary(
            subsection, documents, structured_data, cutoff_date
        )
        
        return SubsectionParsingResult(
            section_name=mapping['display_name'],
            documents_found=documents,
            structured_data_found=structured_data,
            parsing_summary=summary,
            date_range_applied=cutoff_date is not None,
            cutoff_date=cutoff_date
        )
    
    def _find_subsection_documents(
        self, 
        patient_id: int, 
        mapping: Dict, 
        cutoff_date: Optional[datetime],
        limit: int
    ) -> List[MedicalDocument]:
        """Find documents matching subsection criteria"""
        
        query = MedicalDocument.query.filter(
            MedicalDocument.patient_id == patient_id
        )
        
        # Apply date filter if provided
        if cutoff_date:
            query = query.filter(MedicalDocument.upload_date >= cutoff_date)
        
        documents = query.order_by(MedicalDocument.upload_date.desc()).all()
        
        # Filter by keywords and document types
        matching_documents = []
        keywords = [kw.lower() for kw in mapping['document_keywords']]
        doc_types = mapping['document_types']
        
        for doc in documents:
            if len(matching_documents) >= limit:
                break
                
            # Check document type
            if doc.document_type and doc.document_type.upper() in doc_types:
                matching_documents.append(doc)
                continue
            
            # Check filename and content for keywords
            filename_lower = (doc.filename or '').lower()
            content_lower = (doc.content or '').lower()
            
            # Check metadata for section information
            section_match = False
            if doc.doc_metadata:
                try:
                    metadata = json.loads(doc.doc_metadata)
                    section = (metadata.get('section', '') or '').lower()
                    category = (metadata.get('category', '') or '').lower()
                    
                    if any(kw in section or kw in category for kw in keywords):
                        section_match = True
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            # Match by keywords in filename or content
            keyword_match = any(
                kw in filename_lower or kw in content_lower 
                for kw in keywords
            )
            
            if section_match or keyword_match:
                matching_documents.append(doc)
        
        return matching_documents
    
    def _find_structured_data(
        self, 
        patient_id: int, 
        mapping: Dict, 
        cutoff_date: Optional[datetime],
        limit: int
    ) -> List[Any]:
        """Find structured data from database tables"""
        
        model = mapping['structured_model']
        date_field = mapping['date_field']
        
        query = model.query.filter(
            getattr(model, 'patient_id') == patient_id
        )
        
        # Apply date filter if provided
        if cutoff_date:
            query = query.filter(getattr(model, date_field) >= cutoff_date)
        
        return query.order_by(
            getattr(model, date_field).desc()
        ).limit(limit).all()
    
    def _generate_parsing_summary(
        self, 
        subsection: str, 
        documents: List[MedicalDocument], 
        structured_data: List[Any],
        cutoff_date: Optional[datetime]
    ) -> str:
        """Generate human-readable summary of parsing results"""
        
        doc_count = len(documents)
        data_count = len(structured_data)
        
        date_qualifier = ""
        if cutoff_date:
            days_back = (datetime.now() - cutoff_date).days
            date_qualifier = f" since {cutoff_date.strftime('%Y-%m-%d')} ({days_back} days ago)"
        
        if doc_count == 0 and data_count == 0:
            return f"No {subsection} data found{date_qualifier}."
        
        summary_parts = []
        if doc_count > 0:
            summary_parts.append(f"{doc_count} document{'s' if doc_count != 1 else ''}")
        if data_count > 0:
            summary_parts.append(f"{data_count} structured record{'s' if data_count != 1 else ''}")
        
        return f"Found {' and '.join(summary_parts)} for {subsection}{date_qualifier}."
    
    def get_past_appointments_for_cutoff(self, patient_id: int, limit: int = 5) -> List[Tuple[datetime, str]]:
        """
        Get past appointments that can be used as cutoff date options
        
        Args:
            patient_id: Patient ID
            limit: Maximum number of appointments to return
            
        Returns:
            List of (appointment_date, display_text) tuples
        """
        appointments = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date < datetime.now()
        ).order_by(
            Appointment.appointment_date.desc()
        ).limit(limit).all()
        
        cutoff_options = []
        for apt in appointments:
            days_ago = (datetime.now() - apt.appointment_date).days
            display_text = f"{apt.appointment_date.strftime('%Y-%m-%d')} ({days_ago} days ago)"
            if apt.notes:
                display_text += f" - {apt.notes[:50]}..."
            cutoff_options.append((apt.appointment_date, display_text))
        
        return cutoff_options
    
    def parse_all_subsections(
        self, 
        patient_id: int, 
        cutoff_date: Optional[datetime] = None,
        limit_per_section: int = 5
    ) -> Dict[str, SubsectionParsingResult]:
        """
        Parse documents from all medical subsections
        
        Args:
            patient_id: Patient ID
            cutoff_date: Only include data after this date
            limit_per_section: Maximum items per subsection
            
        Returns:
            Dictionary mapping subsection names to parsing results
        """
        results = {}
        
        for subsection in self.SUBSECTION_MAPPINGS.keys():
            try:
                results[subsection] = self.parse_subsection_documents(
                    patient_id, subsection, cutoff_date, limit_per_section
                )
            except Exception as e:
                # Create error result for failed subsections
                results[subsection] = SubsectionParsingResult(
                    section_name=self.SUBSECTION_MAPPINGS[subsection]['display_name'],
                    documents_found=[],
                    structured_data_found=[],
                    parsing_summary=f"Error parsing {subsection}: {str(e)}",
                    date_range_applied=cutoff_date is not None,
                    cutoff_date=cutoff_date
                )
        
        return results


def get_default_cutoff_date() -> datetime:
    """Get default cutoff date (6 months ago)"""
    return datetime.now() - timedelta(days=180)


def format_cutoff_date_options(patient_id: int) -> List[Dict[str, Any]]:
    """
    Format cutoff date options for frontend display
    
    Args:
        patient_id: Patient ID
        
    Returns:
        List of cutoff date options with value, text, and days_back
    """
    parser = MedicalSubsectionParser()
    appointments = parser.get_past_appointments_for_cutoff(patient_id)
    
    options = []
    
    # Add preset options
    preset_options = [
        (datetime.now() - timedelta(days=30), "Last 30 days"),
        (datetime.now() - timedelta(days=90), "Last 3 months"),
        (datetime.now() - timedelta(days=180), "Last 6 months"),
        (datetime.now() - timedelta(days=365), "Last year"),
    ]
    
    for date_val, text in preset_options:
        options.append({
            'value': date_val.strftime('%Y-%m-%d'),
            'text': text,
            'days_back': (datetime.now() - date_val).days,
            'type': 'preset'
        })
    
    # Add appointment-based options
    for apt_date, display_text in appointments:
        options.append({
            'value': apt_date.strftime('%Y-%m-%d'),
            'text': f"Since appointment: {display_text}",
            'days_back': (datetime.now() - apt_date).days,
            'type': 'appointment'
        })
    
    return options