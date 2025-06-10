"""
Medical data routes - handles vitals, conditions, immunizations, and alerts
Extracted from demo_routes.py for better organization
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from models import Patient, Vital, Condition, Immunization, PatientAlert, db
from organized.utils.validation_utils import (
    validate_vital_data,
    validate_condition_data,
)
from organized.middleware.admin_logging import AdminLogger
from datetime import datetime

medical_bp = Blueprint("medical", __name__)


@medical_bp.route("/patient/<int:patient_id>/vitals", methods=["GET", "POST"])
def patient_vitals(patient_id):
    """Add or view patient vitals"""
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        vital_data = {
            "blood_pressure_systolic": request.form.get("blood_pressure_systolic"),
            "blood_pressure_diastolic": request.form.get("blood_pressure_diastolic"),
            "heart_rate": request.form.get("heart_rate"),
            "temperature": request.form.get("temperature"),
            "weight": request.form.get("weight"),
            "height": request.form.get("height"),
            "date": request.form.get("date"),
        }

        errors = validate_vital_data(vital_data)
        if not errors:
            try:
                vital = Vital(
                    patient_id=patient_id,
                    blood_pressure_systolic=vital_data["blood_pressure_systolic"],
                    blood_pressure_diastolic=vital_data["blood_pressure_diastolic"],
                    heart_rate=vital_data["heart_rate"],
                    temperature=vital_data["temperature"],
                    weight=vital_data["weight"],
                    height=vital_data["height"],
                    date=datetime.strptime(vital_data["date"], "%Y-%m-%d").date(),
                )

                db.session.add(vital)
                db.session.commit()

                # Log the action
                AdminLogger.log_data_modification(
                    action="add",
                    data_type="vital",
                    record_id=vital.id,
                    patient_id=patient_id,
                    patient_name=patient.full_name,
                    form_changes=vital_data,
                )

                flash("Vital signs added successfully", "success")
                return redirect(url_for("patient_detail", patient_id=patient_id))

            except Exception as e:
                db.session.rollback()
                flash(f"Error adding vital signs: {str(e)}", "error")
        else:
            for error in errors:
                flash(error, "error")

    vitals = (
        Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).all()
    )
    return render_template("medical/vitals.html", patient=patient, vitals=vitals)


@medical_bp.route("/patient/<int:patient_id>/conditions", methods=["GET", "POST"])
def patient_conditions(patient_id):
    """Add or view patient conditions"""
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        condition_data = {
            "condition_name": request.form.get("condition_name"),
            "diagnosis_date": request.form.get("diagnosis_date"),
            "severity": request.form.get("severity"),
            "status": request.form.get("status"),
            "notes": request.form.get("notes"),
        }

        errors = validate_condition_data(condition_data)
        if not errors:
            try:
                condition = Condition(
                    patient_id=patient_id,
                    condition_name=condition_data["condition_name"],
                    diagnosis_date=(
                        datetime.strptime(
                            condition_data["diagnosis_date"], "%Y-%m-%d"
                        ).date()
                        if condition_data["diagnosis_date"]
                        else None
                    ),
                    severity=condition_data["severity"],
                    status=condition_data["status"],
                    notes=condition_data["notes"],
                )

                db.session.add(condition)
                db.session.commit()

                # Log the action
                AdminLogger.log_data_modification(
                    action="add",
                    data_type="condition",
                    record_id=condition.id,
                    patient_id=patient_id,
                    patient_name=patient.full_name,
                    form_changes=condition_data,
                )

                flash("Condition added successfully", "success")
                return redirect(url_for("patient_detail", patient_id=patient_id))

            except Exception as e:
                db.session.rollback()
                flash(f"Error adding condition: {str(e)}", "error")
        else:
            for error in errors:
                flash(error, "error")

    conditions = Condition.query.filter_by(patient_id=patient_id).all()
    return render_template(
        "medical/conditions.html", patient=patient, conditions=conditions
    )


@medical_bp.route("/patient/<int:patient_id>/immunizations", methods=["GET", "POST"])
def patient_immunizations(patient_id):
    """Add or view patient immunizations"""
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        immunization_data = {
            "vaccine_name": request.form.get("vaccine_name"),
            "date_administered": request.form.get("date_administered"),
            "administered_by": request.form.get("administered_by"),
            "lot_number": request.form.get("lot_number"),
            "site": request.form.get("site"),
            "notes": request.form.get("notes"),
        }

        try:
            immunization = Immunization(
                patient_id=patient_id,
                vaccine_name=immunization_data["vaccine_name"],
                date_administered=datetime.strptime(
                    immunization_data["date_administered"], "%Y-%m-%d"
                ).date(),
                administered_by=immunization_data["administered_by"],
                lot_number=immunization_data["lot_number"],
                site=immunization_data["site"],
                notes=immunization_data["notes"],
            )

            db.session.add(immunization)
            db.session.commit()

            # Log the action
            AdminLogger.log_data_modification(
                action="add",
                data_type="immunization",
                record_id=immunization.id,
                patient_id=patient_id,
                patient_name=patient.full_name,
                form_changes=immunization_data,
            )

            flash("Immunization added successfully", "success")
            return redirect(url_for("patient_detail", patient_id=patient_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error adding immunization: {str(e)}", "error")

    immunizations = Immunization.query.filter_by(patient_id=patient_id).all()
    return render_template(
        "medical/immunizations.html", patient=patient, immunizations=immunizations
    )


@medical_bp.route("/patient/<int:patient_id>/alerts", methods=["GET", "POST"])
def patient_alerts(patient_id):
    """Add or view patient alerts"""
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        alert_data = {
            "alert_type": request.form.get("alert_type"),
            "message": request.form.get("message"),
            "severity": request.form.get("severity"),
            "is_active": request.form.get("is_active") == "on",
        }

        try:
            alert = PatientAlert(
                patient_id=patient_id,
                alert_type=alert_data["alert_type"],
                message=alert_data["message"],
                severity=alert_data["severity"],
                is_active=alert_data["is_active"],
            )

            db.session.add(alert)
            db.session.commit()

            # Log the action
            AdminLogger.log_data_modification(
                action="add",
                data_type="alert",
                record_id=alert.id,
                patient_id=patient_id,
                patient_name=patient.full_name,
                form_changes=alert_data,
            )

            flash("Alert added successfully", "success")
            return redirect(url_for("patient_detail", patient_id=patient_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error adding alert: {str(e)}", "error")

    alerts = PatientAlert.query.filter_by(patient_id=patient_id).all()
    return render_template("medical/alerts.html", patient=patient, alerts=alerts)


@medical_bp.route("/vital/<int:vital_id>/delete", methods=["POST"])
def delete_vital(vital_id):
    """Delete a vital record"""
    vital = Vital.query.get_or_404(vital_id)
    patient_id = vital.patient_id
    patient_name = vital.patient.full_name

    try:
        # Log the deletion
        AdminLogger.log_data_modification(
            action="delete",
            data_type="vital",
            record_id=vital_id,
            patient_id=patient_id,
            patient_name=patient_name,
            additional_data={"deleted_vital_date": str(vital.date)},
        )

        db.session.delete(vital)
        db.session.commit()

        flash("Vital signs deleted successfully", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting vital signs: {str(e)}", "error")

    return redirect(url_for("patient_detail", patient_id=patient_id))


@medical_bp.route("/condition/<int:condition_id>/delete", methods=["POST"])
def delete_condition(condition_id):
    """Delete a condition record"""
    condition = Condition.query.get_or_404(condition_id)
    patient_id = condition.patient_id
    patient_name = condition.patient.full_name

    try:
        # Log the deletion
        AdminLogger.log_data_modification(
            action="delete",
            data_type="condition",
            record_id=condition_id,
            patient_id=patient_id,
            patient_name=patient_name,
            additional_data={"deleted_condition": condition.condition_name},
        )

        db.session.delete(condition)
        db.session.commit()

        flash("Condition deleted successfully", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting condition: {str(e)}", "error")

    return redirect(url_for("patient_detail", patient_id=patient_id))


@medical_bp.route("/api/patient/<int:patient_id>/vitals")
def api_patient_vitals(patient_id):
    """API endpoint for patient vitals"""
    vitals = (
        Vital.query.filter_by(patient_id=patient_id).order_by(Vital.date.desc()).all()
    )

    vitals_data = []
    for vital in vitals:
        vitals_data.append(
            {
                "id": vital.id,
                "date": vital.date.isoformat(),
                "blood_pressure": f"{vital.blood_pressure_systolic}/{vital.blood_pressure_diastolic}",
                "heart_rate": vital.heart_rate,
                "temperature": vital.temperature,
                "weight": vital.weight,
                "height": vital.height,
            }
        )

    return jsonify(vitals_data)
