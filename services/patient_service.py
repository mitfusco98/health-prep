
from datetime import datetime, timedelta
from app import db
from models import Patient, Condition, Vital, Screening, LabResult, Visit
from utils import evaluate_screening_needs

class PatientService:
    @staticmethod
    def create_patient(patient_data):
        """Create a new patient with validation and screening evaluation"""
        patient = Patient(**patient_data)
        db.session.add(patient)
        db.session.commit()
        
        # Evaluate screening needs for new patient
        evaluate_screening_needs(patient)
        
        return patient
    
    @staticmethod
    def update_patient(patient_id, patient_data):
        """Update patient and re-evaluate screening needs"""
        patient = Patient.query.get_or_404(patient_id)
        
        for key, value in patient_data.items():
            setattr(patient, key, value)
        
        patient.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Re-evaluate screening needs if demographics changed
        evaluate_screening_needs(patient)
        
        return patient
    
    @staticmethod
    def get_patient_summary(patient_id, include_recent_data=True):
        """Get comprehensive patient summary"""
        patient = Patient.query.get_or_404(patient_id)
        
        summary = {
            'patient': patient,
            'active_conditions': Condition.query.filter_by(
                patient_id=patient_id, 
                is_active=True
            ).all(),
            'screenings': Screening.query.filter_by(
                patient_id=patient_id
            ).all()
        }
        
        if include_recent_data:
            six_months_ago = datetime.now() - timedelta(days=180)
            
            summary.update({
                'recent_vitals': Vital.query.filter(
                    Vital.patient_id == patient_id,
                    Vital.date >= six_months_ago
                ).order_by(Vital.date.desc()).limit(5).all(),
                
                'recent_labs': LabResult.query.filter(
                    LabResult.patient_id == patient_id,
                    LabResult.test_date >= six_months_ago
                ).order_by(LabResult.test_date.desc()).limit(10).all(),
                
                'recent_visits': Visit.query.filter(
                    Visit.patient_id == patient_id,
                    Visit.visit_date >= six_months_ago
                ).order_by(Visit.visit_date.desc()).limit(5).all()
            })
        
        return summary
    
    @staticmethod
    def delete_patient(patient_id):
        """Safely delete patient and related data"""
        patient = Patient.query.get_or_404(patient_id)
        
        # Delete related records (cascade should handle this, but being explicit)
        Condition.query.filter_by(patient_id=patient_id).delete()
        Vital.query.filter_by(patient_id=patient_id).delete()
        Screening.query.filter_by(patient_id=patient_id).delete()
        
        db.session.delete(patient)
        db.session.commit()
        
        return True
