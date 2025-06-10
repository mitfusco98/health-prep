from sqlalchemy import text, func
from app import db
from models import Patient, Condition


class PatientRepository:
    @staticmethod
    def find_by_mrn(mrn):
        """Find patient by Medical Record Number"""
        return Patient.query.filter_by(mrn=mrn).first()

    @staticmethod
    def search_patients(search_term, limit=50):
        """Search patients by name, MRN, or email"""
        search_pattern = f"%{search_term}%"

        return (
            Patient.query.filter(
                db.or_(
                    Patient.first_name.ilike(search_pattern),
                    Patient.last_name.ilike(search_pattern),
                    Patient.mrn.ilike(search_pattern),
                    Patient.email.ilike(search_pattern),
                )
            )
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_patients_with_conditions(condition_names):
        """Get patients with specific conditions"""
        return (
            Patient.query.join(Condition)
            .filter(Condition.name.in_(condition_names), Condition.is_active == True)
            .distinct()
            .all()
        )

    @staticmethod
    def get_patients_by_age_range(min_age, max_age):
        """Get patients within age range"""
        # Calculate birth date range
        from datetime import date, timedelta

        today = date.today()
        max_birth_date = today - timedelta(days=min_age * 365)
        min_birth_date = today - timedelta(days=(max_age + 1) * 365)

        return Patient.query.filter(
            Patient.date_of_birth.between(min_birth_date, max_birth_date)
        ).all()

    @staticmethod
    def get_patients_by_gender(gender):
        """Get patients by gender"""
        return Patient.query.filter_by(sex=gender).all()

    @staticmethod
    def get_recent_patients(limit=10):
        """Get recently created or updated patients"""
        return Patient.query.order_by(Patient.updated_at.desc()).limit(limit).all()

    @staticmethod
    def count_total_patients():
        """Get total patient count"""
        return Patient.query.count()

    @staticmethod
    def get_next_available_mrn():
        """Generate next available MRN"""
        try:
            result = db.session.execute(
                text(
                    "SELECT MAX(CAST(SUBSTRING(mrn FROM '[0-9]+') AS INTEGER)) FROM patient WHERE mrn ~ '^[0-9]+$'"
                )
            )
            max_mrn = result.scalar()

            if max_mrn is None:
                return "1000"
            else:
                return str(max_mrn + 1)
        except Exception:
            import random

            return str(random.randint(10000, 99999))
