"""
Appointment-related routes extracted from demo_routes.py
Handles appointment scheduling, editing, and management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Appointment, Patient
from app import db
from datetime import datetime, date, timedelta
import json

# Create appointment blueprint
appointment_bp = Blueprint("appointment", __name__, url_prefix="/appointments")


@appointment_bp.route("/")
def appointment_list():
    """Display appointments for a specific date"""
    date_str = request.args.get("date")
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    appointments = (
        Appointment.query.filter(Appointment.appointment_date == selected_date)
        .order_by(Appointment.appointment_time)
        .all()
    )

    return render_template(
        "index.html", appointments=appointments, selected_date=selected_date
    )


@appointment_bp.route("/add", methods=["GET", "POST"])
def add_appointment():
    """Add a new appointment with conflict prevention"""
    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        appointment_type = request.form.get("appointment_type", "Consultation")
        note = request.form.get("note", "")

        if not all([patient_id, appointment_date, appointment_time]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("appointment.add_appointment"))

        # Check for conflicts
        existing_appointment = Appointment.query.filter_by(
            appointment_date=appointment_date, appointment_time=appointment_time
        ).first()

        if existing_appointment:
            flash(
                "This time slot is already booked. Please choose a different time.",
                "warning",
            )
            return redirect(url_for("appointment.add_appointment"))

        try:
            appointment = Appointment(
                patient_id=int(patient_id),
                appointment_date=datetime.strptime(appointment_date, "%Y-%m-%d").date(),
                appointment_time=datetime.strptime(appointment_time, "%H:%M").time(),
                appointment_type=appointment_type,
                note=note,
            )

            db.session.add(appointment)
            db.session.commit()

            patient = Patient.query.get(patient_id)
            flash(
                f"Appointment scheduled for {patient.full_name} on {appointment_date} at {appointment_time}",
                "success",
            )
            return redirect(
                url_for("appointment.appointment_list", date=appointment_date)
            )

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating appointment: {str(e)}", "danger")

    # Get all patients for the form
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    return render_template("appointment_form.html", patients=patients)


@appointment_bp.route("/<int:appointment_id>/edit", methods=["GET", "POST"])
def edit_appointment(appointment_id):
    """Edit an existing appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        appointment_type = request.form.get("appointment_type")
        note = request.form.get("note", "")
        status = request.form.get("status", "Scheduled")

        # Check for conflicts (excluding current appointment)
        existing_appointment = Appointment.query.filter(
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.id != appointment_id,
        ).first()

        if existing_appointment:
            flash(
                "This time slot is already booked. Please choose a different time.",
                "warning",
            )
            return redirect(
                url_for("appointment.edit_appointment", appointment_id=appointment_id)
            )

        try:
            appointment.patient_id = int(patient_id)
            appointment.appointment_date = datetime.strptime(
                appointment_date, "%Y-%m-%d"
            ).date()
            appointment.appointment_time = datetime.strptime(
                appointment_time, "%H:%M"
            ).time()
            appointment.appointment_type = appointment_type
            appointment.note = note
            appointment.status = status

            db.session.commit()
            flash("Appointment updated successfully!", "success")
            return redirect(
                url_for("appointment.appointment_list", date=appointment_date)
            )

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating appointment: {str(e)}", "danger")

    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    return render_template(
        "appointment_form.html", appointment=appointment, patients=patients
    )


@appointment_bp.route("/<int:appointment_id>/delete", methods=["POST"])
def delete_appointment(appointment_id):
    """Delete an appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment_date = appointment.appointment_date

    try:
        db.session.delete(appointment)
        db.session.commit()
        flash("Appointment deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting appointment: {str(e)}", "danger")

    return redirect(url_for("appointment.appointment_list", date=appointment_date))


@appointment_bp.route("/available-slots")
def get_available_slots():
    """API endpoint to get available appointment time slots for a specific date"""
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Date parameter is required"}), 400

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    # Generate 15-minute time slots from 8:00 AM to 5:00 PM
    all_slots = []
    start_time = datetime.combine(selected_date, datetime.min.time().replace(hour=8))
    end_time = datetime.combine(selected_date, datetime.min.time().replace(hour=17))

    current_time = start_time
    while current_time < end_time:
        all_slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=15)

    # Get booked slots
    booked_appointments = Appointment.query.filter_by(
        appointment_date=selected_date
    ).all()
    booked_slots = [
        apt.appointment_time.strftime("%H:%M") for apt in booked_appointments
    ]

    # Filter available slots
    available_slots = [slot for slot in all_slots if slot not in booked_slots]

    return jsonify({"available_slots": available_slots})


@appointment_bp.route("/all")
def all_visits():
    """Display all appointments (past and future) with ability to delete"""
    page = request.args.get("page", 1, type=int)
    per_page = 50

    appointments = Appointment.query.order_by(
        Appointment.appointment_date.desc(), Appointment.appointment_time.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template("all_visits.html", appointments=appointments)
