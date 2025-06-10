from datetime import datetime, date, time, timedelta
from app import db
from models import Appointment, Patient
from sqlalchemy import and_


class AppointmentService:
    @staticmethod
    def get_daily_schedule(target_date=None):
        """Get all appointments for a specific date"""
        if target_date is None:
            target_date = date.today()

        appointments = (
            Appointment.query.filter_by(appointment_date=target_date)
            .order_by(Appointment.appointment_time)
            .all()
        )

        return appointments

    @staticmethod
    def check_time_conflicts(appointment_date, appointment_time, exclude_id=None):
        """Check if appointment time conflicts with existing appointments"""
        query = Appointment.query.filter(
            and_(
                Appointment.appointment_date == appointment_date,
                Appointment.appointment_time == appointment_time,
            )
        )

        if exclude_id:
            query = query.filter(Appointment.id != exclude_id)

        existing = query.first()
        return existing is not None

    @staticmethod
    def create_appointment(appointment_data):
        """Create appointment with conflict checking"""
        # Check for time conflicts
        if AppointmentService.check_time_conflicts(
            appointment_data["appointment_date"], appointment_data["appointment_time"]
        ):
            raise ValueError("Appointment time conflict detected")

        appointment = Appointment(**appointment_data)
        db.session.add(appointment)
        db.session.commit()

        return appointment

    @staticmethod
    def update_appointment_status(appointment_id, new_status):
        """Update appointment status with validation"""
        valid_statuses = ["OOO", "waiting", "provider", "seen"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        appointment = Appointment.query.get_or_404(appointment_id)
        appointment.status = new_status
        appointment.updated_at = datetime.utcnow()
        db.session.commit()

        return appointment

    @staticmethod
    def get_patient_appointment_history(patient_id, limit=10):
        """Get recent appointment history for a patient"""
        appointments = (
            Appointment.query.filter_by(patient_id=patient_id)
            .order_by(
                Appointment.appointment_date.desc(), Appointment.appointment_time.desc()
            )
            .limit(limit)
            .all()
        )

        return appointments
