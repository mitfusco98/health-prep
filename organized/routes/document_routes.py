"""
Document management routes - handles medical documents, uploads, and downloads
Extracted from demo_routes.py for better organization
"""

from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
)
from werkzeug.utils import secure_filename
from models import Patient, MedicalDocument, db
from organized.middleware.admin_logging import AdminLogger
from datetime import datetime
import os
import io

document_bp = Blueprint("document", __name__)

ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx"}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@document_bp.route("/patient/<int:patient_id>/documents")
def patient_documents(patient_id):
    """View patient documents"""
    patient = Patient.query.get_or_404(patient_id)
    documents = (
        MedicalDocument.query.filter_by(patient_id=patient_id)
        .order_by(MedicalDocument.upload_date.desc())
        .all()
    )

    return render_template(
        "documents/patient_documents.html", patient=patient, documents=documents
    )


@document_bp.route(
    "/patient/<int:patient_id>/documents/upload", methods=["GET", "POST"]
)
def upload_document(patient_id):
    """Upload a new document for patient"""
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        document_data = {
            "document_type": request.form.get("document_type"),
            "description": request.form.get("description"),
            "date_created": request.form.get("date_created"),
        }

        # Check if file was uploaded
        if "file" not in request.files:
            flash("No file selected", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                
                # Reset file pointer to beginning before reading
                file.seek(0)
                file_data = file.read()
                
                # Validate file data was actually read
                if not file_data:
                    flash("Error: File appears to be empty or could not be read", "error")
                    return redirect(request.url)

                document = MedicalDocument(
                    patient_id=patient_id,
                    document_type=document_data["document_type"],
                    filename=filename,
                    file_data=file_data,
                    description=document_data["description"],
                    date_created=(
                        datetime.strptime(
                            document_data["date_created"], "%Y-%m-%d"
                        ).date()
                        if document_data["date_created"]
                        else datetime.now().date()
                    ),
                    upload_date=datetime.now(),
                )

                db.session.add(document)
                db.session.commit()

                # Log the action
                AdminLogger.log_data_modification(
                    action="upload",
                    data_type="document",
                    record_id=document.id,
                    patient_id=patient_id,
                    patient_name=patient.full_name,
                    form_changes={
                        "filename": filename,
                        "document_type": document_data["document_type"],
                        "description": document_data["description"],
                        "file_size": len(file_data),
                    },
                )

                flash("Document uploaded successfully", "success")
                return redirect(
                    url_for("document.patient_documents", patient_id=patient_id)
                )

            except Exception as e:
                db.session.rollback()
                flash(f"Error uploading document: {str(e)}", "error")
                return redirect(request.url)

            except Exception as e:
                db.session.rollback()
                flash(f"Error uploading document: {str(e)}", "error")
        else:
            flash(
                "Invalid file type. Allowed types: txt, pdf, png, jpg, jpeg, gif, doc, docx",
                "error",
            )

    return render_template("documents/upload_document.html", patient=patient)


@document_bp.route("/document/<int:document_id>/view")
def view_document(document_id):
    """View document details"""
    document = MedicalDocument.query.get_or_404(document_id)

    # Log document access
    AdminLogger.log_data_modification(
        action="view",
        data_type="document",
        record_id=document_id,
        patient_id=document.patient_id,
        patient_name=document.patient.full_name,
        additional_data={"filename": document.filename},
    )

    return render_template("documents/view_document.html", document=document)


@document_bp.route("/document/<int:document_id>/download")
def download_document(document_id):
    """Download a document"""
    document = MedicalDocument.query.get_or_404(document_id)

    # Log document download
    AdminLogger.log_data_modification(
        action="download",
        data_type="document",
        record_id=document_id,
        patient_id=document.patient_id,
        patient_name=document.patient.full_name,
        additional_data={"filename": document.filename},
    )

    return send_file(
        io.BytesIO(document.file_data),
        as_attachment=True,
        download_name=document.filename,
        mimetype="application/octet-stream",
    )


@document_bp.route("/document/<int:document_id>/image")
def document_image(document_id):
    """Serve document image for preview"""
    document = MedicalDocument.query.get_or_404(document_id)
    
    if not document.binary_content:
        return jsonify({"error": "No image content available"}), 404
    
    # Log document preview access
    AdminLogger.log_data_modification(
        action="preview",
        data_type="document",
        record_id=document_id,
        patient_id=document.patient_id,
        patient_name=document.patient.full_name,
        additional_data={"filename": document.filename},
    )
    
    # Determine MIME type
    mime_type = document.mime_type or "application/octet-stream"
    if not mime_type.startswith(('image/', 'application/pdf')):
        return jsonify({"error": "Document is not previewable"}), 400
    
    return send_file(
        io.BytesIO(document.binary_content),
        mimetype=mime_type,
        as_attachment=False,
        download_name=document.filename
    )


@document_bp.route("/document/<int:document_id>/delete", methods=["POST"])
def delete_document(document_id):
    """Delete a document"""
    document = MedicalDocument.query.get_or_404(document_id)
    patient_id = document.patient_id
    patient_name = document.patient.full_name
    filename = document.filename

    try:
        # Log the deletion
        AdminLogger.log_data_modification(
            action="delete",
            data_type="document",
            record_id=document_id,
            patient_id=patient_id,
            patient_name=patient_name,
            additional_data={"deleted_filename": filename},
        )

        db.session.delete(document)
        db.session.commit()

        flash("Document deleted successfully", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting document: {str(e)}", "error")

    return redirect(url_for("document.patient_documents", patient_id=patient_id))


@document_bp.route("/document/<int:document_id>/edit", methods=["GET", "POST"])
def edit_document(document_id):
    """Edit document metadata"""
    document = MedicalDocument.query.get_or_404(document_id)

    if request.method == "POST":
        old_data = {
            "document_type": document.document_type,
            "description": document.description,
            "date_created": document.date_created,
        }

        new_data = {
            "document_type": request.form.get("document_type"),
            "description": request.form.get("description"),
            "date_created": request.form.get("date_created"),
        }

        try:
            document.document_type = new_data["document_type"]
            document.description = new_data["description"]
            if new_data["date_created"]:
                document.date_created = datetime.strptime(
                    new_data["date_created"], "%Y-%m-%d"
                ).date()

            db.session.commit()

            # Log the changes
            changes = {}
            for key in new_data:
                if str(old_data[key]) != str(new_data[key]):
                    changes[key] = {
                        "old": str(old_data[key]),
                        "new": str(new_data[key]),
                    }

            if changes:
                AdminLogger.log_data_modification(
                    action="edit",
                    data_type="document",
                    record_id=document_id,
                    patient_id=document.patient_id,
                    patient_name=document.patient.full_name,
                    form_changes=changes,
                    additional_data={"filename": document.filename},
                )

            flash("Document updated successfully", "success")
            return redirect(url_for("document.view_document", document_id=document_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating document: {str(e)}", "error")

    return render_template("documents/edit_document.html", document=document)


@document_bp.route("/api/patient/<int:patient_id>/documents")
def api_patient_documents(patient_id):
    """API endpoint for patient documents"""
    documents = (
        MedicalDocument.query.filter_by(patient_id=patient_id)
        .order_by(MedicalDocument.upload_date.desc())
        .all()
    )

    documents_data = []
    for doc in documents:
        documents_data.append(
            {
                "id": doc.id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "description": doc.description,
                "upload_date": doc.upload_date.isoformat(),
                "date_created": (
                    doc.date_created.isoformat() if doc.date_created else None
                ),
                "file_size": len(doc.file_data) if doc.file_data else 0,
            }
        )

    return jsonify(documents_data)


@document_bp.route("/documents/types")
def document_types():
    """Get available document types"""
    types = [
        "Lab Results",
        "Imaging Study",
        "Consultation Report",
        "Hospital Summary",
        "Insurance Document",
        "Prescription",
        "Medical History",
        "Other",
    ]
    return jsonify(types)
