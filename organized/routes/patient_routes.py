"""
Patient-related routes extracted from demo_routes.py
Handles patient management, viewing, editing, and medical data
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import (
    Patient,
    MedicalDocument,
    Condition,
    Vital,
    Immunization,
    PatientAlert,
)
from app import db
import logging

# Create patient blueprint
patient_bp = Blueprint("patient", __name__, url_prefix="/patients")


@patient_bp.route("/")
def patient_list():
    """Display all patients with search functionality"""
    search_term = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = Patient.query
    if search_term:
        query = query.filter(
            (Patient.first_name.ilike(f"%{search_term}%"))
            | (Patient.last_name.ilike(f"%{search_term}%"))
            | (Patient.mrn.ilike(f"%{search_term}%"))
        )

    patients = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "patient_list.html", patients=patients, search_term=search_term
    )


@patient_bp.route("/add", methods=["GET", "POST"])
def add_patient():
    """Add a new patient"""
    if request.method == "POST":
        # Extract form data
        patient = Patient(
            first_name=request.form.get("first_name"),
            last_name=request.form.get("last_name"),
            date_of_birth=request.form.get("date_of_birth"),
            gender=request.form.get("gender"),
            phone=request.form.get("phone"),
            email=request.form.get("email"),
            address=request.form.get("address"),
            emergency_contact=request.form.get("emergency_contact"),
            emergency_phone=request.form.get("emergency_phone"),
            insurance_provider=request.form.get("insurance_provider"),
            insurance_number=request.form.get("insurance_number"),
            primary_physician=request.form.get("primary_physician"),
        )

        try:
            db.session.add(patient)
            db.session.commit()
            flash(f"Patient {patient.full_name} added successfully!", "success")
            return redirect(url_for("patient.patient_detail", patient_id=patient.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding patient: {str(e)}", "danger")

    return render_template("patient_form.html")


@patient_bp.route("/<int:patient_id>")
def patient_detail(patient_id):
    """Display patient details"""
    patient = Patient.query.get_or_404(patient_id)

    # Get related medical data
    conditions = Condition.query.filter_by(patient_id=patient_id).all()
    vitals = (
        Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).all()
    )
    documents = MedicalDocument.query.filter_by(patient_id=patient_id).all()
    immunizations = Immunization.query.filter_by(patient_id=patient_id).all()
    alerts = PatientAlert.query.filter_by(patient_id=patient_id).all()

    return render_template(
        "patient_detail.html",
        patient=patient,
        conditions=conditions,
        vitals=vitals,
        documents=documents,
        immunizations=immunizations,
        alerts=alerts,
    )


@patient_bp.route("/<int:patient_id>/edit", methods=["GET", "POST"])
def edit_patient(patient_id):
    """Edit patient information"""
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        # Update patient data
        patient.first_name = request.form.get("first_name")
        patient.last_name = request.form.get("last_name")
        patient.date_of_birth = request.form.get("date_of_birth")
        patient.gender = request.form.get("gender")
        patient.phone = request.form.get("phone")
        patient.email = request.form.get("email")
        patient.address = request.form.get("address")
        patient.emergency_contact = request.form.get("emergency_contact")
        patient.emergency_phone = request.form.get("emergency_phone")
        patient.insurance_provider = request.form.get("insurance_provider")
        patient.insurance_number = request.form.get("insurance_number")
        patient.primary_physician = request.form.get("primary_physician")

        try:
            db.session.commit()
            flash(f"Patient {patient.full_name} updated successfully!", "success")
            return redirect(url_for("patient.patient_detail", patient_id=patient.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating patient: {str(e)}", "danger")

    return render_template("patient_form.html", patient=patient)
