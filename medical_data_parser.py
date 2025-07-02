"""
Medical Data Parser with Time-based Filtering
Parses documents from medical data subsections (labs, imaging, consults, hospital visits)
Applies user-configurable cutoff dates to filter older data
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import and_
from models import (
    MedicalDocument, LabResult, ImagingStudy, ConsultReport, 
    HospitalSummary, ChecklistSettings, Patient
)
from app import db
import json


class MedicalDataParser:
    """Parse and filter medical data with time-based cutoffs"""
    
    def __init__(self, patient_id: int, settings: Optional[ChecklistSettings] = None):
        self.patient_id = patient_id
        self.settings = settings or self._get_default_settings()
        
    def _get_default_settings(self) -> ChecklistSettings:
        """Get checklist settings or create default"""
        settings = ChecklistSettings.query.first()
        if not settings:
            settings = ChecklistSettings(
                labs_cutoff_months=6,
                imaging_cutoff_months=12,
                consults_cutoff_months=12,
                hospital_cutoff_months=24
            )
        return settings
    
    def _calculate_cutoff_date(self, months: int) -> datetime:
        """Calculate cutoff date based on months from now"""
        return datetime.now() - timedelta(days=months * 30)
    
    def get_filtered_labs(self) -> Dict[str, Any]:
        """Get lab results within cutoff period and their associated documents"""
        cutoff_date = self._calculate_cutoff_date(self.settings.labs_cutoff_months)
        
        # Get lab results within cutoff
        labs = LabResult.query.filter(
            and_(
                LabResult.patient_id == self.patient_id,
                LabResult.test_date >= cutoff_date
            )
        ).order_by(LabResult.test_date.desc()).all()
        
        # Get associated documents
        lab_documents = MedicalDocument.query.filter(
            and_(
                MedicalDocument.patient_id == self.patient_id,
                MedicalDocument.document_type.in_(['lab_result', 'laboratory']),
                MedicalDocument.upload_date >= cutoff_date
            )
        ).order_by(MedicalDocument.upload_date.desc()).all()
        
        return {
            'data': labs,
            'documents': lab_documents,
            'cutoff_date': cutoff_date,
            'section_name': 'Laboratories',
            'cutoff_months': self.settings.labs_cutoff_months
        }
    
    def get_filtered_imaging(self) -> Dict[str, Any]:
        """Get imaging studies within cutoff period and their associated documents"""
        cutoff_date = self._calculate_cutoff_date(self.settings.imaging_cutoff_months)
        
        # Get imaging studies within cutoff
        imaging = ImagingStudy.query.filter(
            and_(
                ImagingStudy.patient_id == self.patient_id,
                ImagingStudy.study_date >= cutoff_date
            )
        ).order_by(ImagingStudy.study_date.desc()).all()
        
        # Get associated documents
        imaging_documents = MedicalDocument.query.filter(
            and_(
                MedicalDocument.patient_id == self.patient_id,
                MedicalDocument.document_type.in_(['imaging', 'radiology', 'xray', 'mri', 'ct_scan']),
                MedicalDocument.upload_date >= cutoff_date
            )
        ).order_by(MedicalDocument.upload_date.desc()).all()
        
        return {
            'data': imaging,
            'documents': imaging_documents,
            'cutoff_date': cutoff_date,
            'section_name': 'Imaging',
            'cutoff_months': self.settings.imaging_cutoff_months
        }
    
    def get_filtered_consults(self) -> Dict[str, Any]:
        """Get consult reports within cutoff period and their associated documents"""
        cutoff_date = self._calculate_cutoff_date(self.settings.consults_cutoff_months)
        
        # Get consult reports within cutoff
        consults = ConsultReport.query.filter(
            and_(
                ConsultReport.patient_id == self.patient_id,
                ConsultReport.report_date >= cutoff_date
            )
        ).order_by(ConsultReport.report_date.desc()).all()
        
        # Get associated documents
        consult_documents = MedicalDocument.query.filter(
            and_(
                MedicalDocument.patient_id == self.patient_id,
                MedicalDocument.document_type.in_(['consult', 'consultation', 'specialist_report']),
                MedicalDocument.upload_date >= cutoff_date
            )
        ).order_by(MedicalDocument.upload_date.desc()).all()
        
        return {
            'data': consults,
            'documents': consult_documents,
            'cutoff_date': cutoff_date,
            'section_name': 'Consults',
            'cutoff_months': self.settings.consults_cutoff_months
        }
    
    def get_filtered_hospital_visits(self) -> Dict[str, Any]:
        """Get hospital visits within cutoff period and their associated documents"""
        cutoff_date = self._calculate_cutoff_date(self.settings.hospital_cutoff_months)
        
        # Get hospital summaries within cutoff
        hospital_visits = HospitalSummary.query.filter(
            and_(
                HospitalSummary.patient_id == self.patient_id,
                HospitalSummary.admission_date >= cutoff_date
            )
        ).order_by(HospitalSummary.admission_date.desc()).all()
        
        # Get associated documents
        hospital_documents = MedicalDocument.query.filter(
            and_(
                MedicalDocument.patient_id == self.patient_id,
                MedicalDocument.document_type.in_(['hospital_summary', 'discharge_summary', 'admission_note']),
                MedicalDocument.upload_date >= cutoff_date
            )
        ).order_by(MedicalDocument.upload_date.desc()).all()
        
        return {
            'data': hospital_visits,
            'documents': hospital_documents,
            'cutoff_date': cutoff_date,
            'section_name': 'Hospital Visits',
            'cutoff_months': self.settings.hospital_cutoff_months
        }
    
    def get_all_filtered_data(self) -> Dict[str, Any]:
        """Get all filtered medical data and documents"""
        return {
            'labs': self.get_filtered_labs(),
            'imaging': self.get_filtered_imaging(),
            'consults': self.get_filtered_consults(),
            'hospital_visits': self.get_filtered_hospital_visits(),
            'patient_id': self.patient_id,
            'settings': self.settings
        }
    
    def format_document_summary(self, documents: List[MedicalDocument], max_items: int = 3) -> str:
        """Format document summary for display in checklist"""
        if not documents:
            return "No documents found within the selected time period."
        
        summaries = []
        for doc in documents[:max_items]:
            # Try to extract meaningful info from document
            doc_info = doc.filename
            
            # Add date if available
            if doc.upload_date:
                doc_info += f" ({doc.upload_date.strftime('%Y-%m-%d')})"
            
            # Add document type if available and different from filename
            if doc.document_type and doc.document_type.lower() not in doc.filename.lower():
                doc_info += f" [{doc.document_type}]"
                
            summaries.append(doc_info)
        
        result = "; ".join(summaries)
        if len(documents) > max_items:
            result += f" and {len(documents) - max_items} more documents"
            
        return result
    
    def format_data_summary(self, data_items: List[Any], data_type: str, max_items: int = 3) -> str:
        """Format medical data summary for display in checklist"""
        if not data_items:
            return f"No {data_type.lower()} found within the selected time period."
        
        summaries = []
        for item in data_items[:max_items]:
            if data_type == 'labs':
                summary = f"{item.test_name}: {item.result_value} {item.unit or ''} ({item.test_date.strftime('%Y-%m-%d')})"
            elif data_type == 'imaging':
                summary = f"{item.study_type} ({item.study_date.strftime('%Y-%m-%d')})"
            elif data_type == 'consults':
                summary = f"{item.specialty} ({item.report_date.strftime('%Y-%m-%d')})"
            elif data_type == 'hospital_visits':
                summary = f"{item.hospital_name} ({item.admission_date.strftime('%Y-%m-%d')})"
            else:
                summary = str(item)
                
            summaries.append(summary)
        
        result = "; ".join(summaries)
        if len(data_items) > max_items:
            result += f" and {len(data_items) - max_items} more {data_type.lower()}"
            
        return result


def get_patient_appointments_for_cutoff_selection(patient_id: int, months_back: int = 24) -> List[Dict[str, Any]]:
    """Get patient's past appointments for cutoff date selection"""
    from models import Appointment
    
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)
    appointments = Appointment.query.filter(
        and_(
            Appointment.patient_id == patient_id,
            Appointment.date >= cutoff_date,
            Appointment.date <= datetime.now().date()
        )
    ).order_by(Appointment.date.desc()).all()
    
    appointment_options = []
    for appt in appointments:
        appointment_options.append({
            'date': appt.date,
            'date_str': appt.date.strftime('%Y-%m-%d'),
            'display': f"{appt.date.strftime('%B %d, %Y')} - {appt.reason or 'Appointment'}",
            'reason': appt.reason or 'Appointment'
        })
    
    return appointment_options