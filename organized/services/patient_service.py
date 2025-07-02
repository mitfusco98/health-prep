"""
Patient service layer consolidated from patient_service.py and related utilities
Handles patient business logic, data processing, and prep sheet generation
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from models import (
    Patient,
    MedicalDocument,
    Condition,
    Vital,
    Immunization,
    PatientAlert,
    Screening,
    ScreeningType,
)
from app import db
import logging


class PatientService:
    """Service class for patient-related business logic"""

    @staticmethod
    def create_patient(patient_data: Dict) -> Tuple[Patient, List[str]]:
        """Create a new patient with validation"""
        errors = []

        try:
            patient = Patient(
                first_name=patient_data.get("first_name"),
                last_name=patient_data.get("last_name"),
                date_of_birth=patient_data.get("date_of_birth"),
                gender=patient_data.get("gender"),
                phone=patient_data.get("phone"),
                email=patient_data.get("email"),
                address=patient_data.get("address"),
                emergency_contact=patient_data.get("emergency_contact"),
                emergency_phone=patient_data.get("emergency_phone"),
                insurance_provider=patient_data.get("insurance_provider"),
                insurance_number=patient_data.get("insurance_number"),
                primary_physician=patient_data.get("primary_physician"),
            )

            db.session.add(patient)
            db.session.commit()

            return patient, errors

        except Exception as e:
            db.session.rollback()
            errors.append(f"Error creating patient: {str(e)}")
            return None, errors

    @staticmethod
    def update_patient(
        patient_id: int, patient_data: Dict
    ) -> Tuple[Optional[Patient], List[str]]:
        """Update patient information"""
        errors = []

        try:
            patient = Patient.query.get(patient_id)
            if not patient:
                errors.append("Patient not found")
                return None, errors

            # Update fields
            patient.first_name = patient_data.get("first_name", patient.first_name)
            patient.last_name = patient_data.get("last_name", patient.last_name)
            patient.date_of_birth = patient_data.get(
                "date_of_birth", patient.date_of_birth
            )
            patient.gender = patient_data.get("gender", patient.gender)
            patient.phone = patient_data.get("phone", patient.phone)
            patient.email = patient_data.get("email", patient.email)
            patient.address = patient_data.get("address", patient.address)
            patient.emergency_contact = patient_data.get(
                "emergency_contact", patient.emergency_contact
            )
            patient.emergency_phone = patient_data.get(
                "emergency_phone", patient.emergency_phone
            )
            patient.insurance_provider = patient_data.get(
                "insurance_provider", patient.insurance_provider
            )
            patient.insurance_number = patient_data.get(
                "insurance_number", patient.insurance_number
            )
            patient.primary_physician = patient_data.get(
                "primary_physician", patient.primary_physician
            )

            db.session.commit()
            return patient, errors

        except Exception as e:
            db.session.rollback()
            errors.append(f"Error updating patient: {str(e)}")
            return None, errors

    @staticmethod
    def get_patient_with_medical_data(patient_id: int) -> Optional[Dict]:
        """Get patient with all related medical data"""
        patient = Patient.query.get(patient_id)
        if not patient:
            return None

        return {
            "patient": patient,
            "conditions": Condition.query.filter_by(patient_id=patient_id).all(),
            "vitals": Vital.query.filter_by(patient_id=patient_id)
            .order_by(Vital.date.desc())
            .all(),
            "documents": MedicalDocument.query.filter_by(patient_id=patient_id)
            .order_by(MedicalDocument.created_at.desc())
            .all(),
            "immunizations": Immunization.query.filter_by(patient_id=patient_id).all(),
            "alerts": PatientAlert.query.filter_by(patient_id=patient_id).all(),
            "screenings": Screening.query.filter_by(patient_id=patient_id).all(),
        }

    @staticmethod
    def search_patients(search_term: str, page: int = 1, per_page: int = 20):
        """Search patients by name or MRN"""
        query = Patient.query

        if search_term:
            query = query.filter(
                (Patient.first_name.ilike(f"%{search_term}%"))
                | (Patient.last_name.ilike(f"%{search_term}%"))
                | (Patient.mrn.ilike(f"%{search_term}%"))
            )

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def delete_patient_with_records(patient_id: int) -> Tuple[bool, List[str]]:
        """Delete a patient and all associated records"""
        errors = []

        try:
            patient = Patient.query.get(patient_id)
            if not patient:
                errors.append("Patient not found")
                return False, errors

            # Delete associated records first (due to foreign key constraints)
            Condition.query.filter_by(patient_id=patient_id).delete()
            Vital.query.filter_by(patient_id=patient_id).delete()
            MedicalDocument.query.filter_by(patient_id=patient_id).delete()
            Immunization.query.filter_by(patient_id=patient_id).delete()
            PatientAlert.query.filter_by(patient_id=patient_id).delete()
            Screening.query.filter_by(patient_id=patient_id).delete()

            # Delete the patient
            db.session.delete(patient)
            db.session.commit()

            return True, errors

        except Exception as e:
            db.session.rollback()
            errors.append(f"Error deleting patient: {str(e)}")
            return False, errors

    @staticmethod
    def generate_prep_sheet_data(patient_id: int) -> Optional[Dict]:
        """Generate preparation sheet data for a patient"""
        patient_data = PatientService.get_patient_with_medical_data(patient_id)
        if not patient_data:
            return None

        patient = patient_data["patient"]

        # Calculate age
        if patient.date_of_birth:
            today = date.today()
            age = today.year - patient.date_of_birth.year
            if today.month < patient.date_of_birth.month or (
                today.month == patient.date_of_birth.month
                and today.day < patient.date_of_birth.day
            ):
                age -= 1
        else:
            age = None

        # Get due screenings
        due_screenings = []
        for screening in patient_data["screenings"]:
            if screening.due_date and screening.due_date <= date.today():
                due_screenings.append(screening)

        # Get recent vitals (last 3 entries)
        recent_vitals = patient_data["vitals"][:3]

        # Get active conditions
        active_conditions = [c for c in patient_data["conditions"] if c.is_active]

        # Get recent alerts
        recent_alerts = [a for a in patient_data["alerts"] if a.is_active]

        return {
            "patient": patient,
            "age": age,
            "due_screenings": due_screenings,
            "recent_vitals": recent_vitals,
            "active_conditions": active_conditions,
            "recent_alerts": recent_alerts,
            "immunizations": patient_data["immunizations"],
            "generated_date": datetime.now(),
        }

    @staticmethod
    def get_patient_statistics() -> Dict:
        """Get patient statistics for dashboard"""
        try:
            total_patients = Patient.query.count()

            # Calculate age distribution
            patients_with_dob = Patient.query.filter(
                Patient.date_of_birth.isnot(None)
            ).all()
            age_groups = {"0-18": 0, "19-35": 0, "36-65": 0, "65+": 0}

            today = date.today()
            for patient in patients_with_dob:
                age = today.year - patient.date_of_birth.year
                if today.month < patient.date_of_birth.month or (
                    today.month == patient.date_of_birth.month
                    and today.day < patient.date_of_birth.day
                ):
                    age -= 1

                if age <= 18:
                    age_groups["0-18"] += 1
                elif age <= 35:
                    age_groups["19-35"] += 1
                elif age <= 65:
                    age_groups["36-65"] += 1
                else:
                    age_groups["65+"] += 1

            # Gender distribution
            gender_stats = (
                db.session.query(Patient.gender, db.func.count(Patient.id))
                .group_by(Patient.gender)
                .all()
            )
            gender_distribution = {gender: count for gender, count in gender_stats}

            return {
                "total_patients": total_patients,
                "age_distribution": age_groups,
                "gender_distribution": gender_distribution,
                "patients_with_alerts": PatientAlert.query.filter_by(
                    is_active=True
                ).count(),
                "patients_with_due_screenings": len(
                    set(
                        [
                            s.patient_id
                            for s in Screening.query.filter(
                                Screening.due_date <= today
                            ).all()
                        ]
                    )
                ),
            }

        except Exception as e:
            logging.error(f"Error getting patient statistics: {str(e)}")
            return {
                "total_patients": 0,
                "age_distribution": {"0-18": 0, "19-35": 0, "36-65": 0, "65+": 0},
                "gender_distribution": {},
                "patients_with_alerts": 0,
                "patients_with_due_screenings": 0,
            }

    @staticmethod
    def bulk_delete_patients(patient_ids: List[int]) -> Tuple[int, List[str]]:
        """Delete multiple patients and their records"""
        deleted_count = 0
        errors = []

        for patient_id in patient_ids:
            try:
                success, patient_errors = PatientService.delete_patient_with_records(
                    patient_id
                )
                if success:
                    deleted_count += 1
                else:
                    errors.extend(patient_errors)
            except Exception as e:
                errors.append(f"Error deleting patient {patient_id}: {str(e)}")

        return deleted_count, errors
