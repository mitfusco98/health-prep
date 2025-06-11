"""
Enhanced Document Upload with FHIR Metadata Integration

This shows how to integrate FHIR-style metadata into your existing document upload workflow.
Your database fields remain unchanged - the FHIR structure is stored in doc_metadata as JSON.
"""

import os
import json
from datetime import datetime
from flask import request, flash, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from models import MedicalDocument, Patient, db
from document_fhir_helpers import enhance_document_on_upload, add_document_extension
from fhir_document_metadata import DocumentFHIRMetadataBuilder


def upload_document_with_fhir_metadata(patient_id, file, form_data):
    """
    Enhanced document upload that automatically adds FHIR metadata.
    
    Args:
        patient_id: Patient ID
        file: Uploaded file object
        form_data: Form data containing document details and FHIR metadata
        
    Returns:
        MedicalDocument instance with FHIR metadata
    """
    # Secure filename
    filename = secure_filename(file.filename)
    
    # Determine if file is binary
    is_binary = file.content_type and not file.content_type.startswith('text/')
    
    # Create document record (existing workflow)
    document = MedicalDocument(
        patient_id=patient_id,
        filename=filename,
        document_name=form_data.get('document_name', filename),
        document_type=form_data.get('document_type', 'Other'),
        source_system=form_data.get('source_system', 'Manual Upload'),
        provider=form_data.get('provider'),
        document_date=form_data.get('document_date', datetime.utcnow()),
        is_binary=is_binary,
        mime_type=file.content_type,
        is_processed=True
    )
    
    # Handle file content
    if is_binary:
        document.binary_content = file.read()
    else:
        document.content = file.read().decode('utf-8', errors='ignore')
    
    # Add to database first to get ID
    db.session.add(document)
    db.session.flush()  # Get ID without committing
    
    # Enhance with FHIR metadata based on document type and form data
    fhir_form_data = extract_fhir_metadata_from_form(form_data)
    enhance_document_on_upload(document, fhir_form_data)
    
    # Add custom extensions if provided
    if form_data.get('custom_metadata'):
        try:
            custom_data = json.loads(form_data['custom_metadata'])
            for key, value in custom_data.items():
                add_document_extension(document, key, value)
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Commit the changes
    db.session.commit()
    
    return document


def extract_fhir_metadata_from_form(form_data):
    """
    Extract FHIR-relevant metadata from form submission.
    
    Args:
        form_data: Form data dictionary
        
    Returns:
        Dictionary with FHIR metadata fields
    """
    fhir_data = {}
    
    # Lab Results specific fields
    if form_data.get('document_type') == 'Lab Results':
        fhir_data.update({
            'test_type': form_data.get('lab_test_type', 'General'),
            'lab_id': form_data.get('lab_id'),
            'lab_status': form_data.get('lab_status', 'final'),
            'lab_equipment': form_data.get('lab_equipment'),
            'reference_range': form_data.get('reference_range')
        })
    
    # Imaging specific fields
    elif form_data.get('document_type') in ['Imaging', 'Radiology']:
        fhir_data.update({
            'modality': form_data.get('imaging_modality', 'XRAY'),
            'body_part': form_data.get('body_part', 'Chest'),
            'study_type': form_data.get('study_type', 'Diagnostic'),
            'contrast_used': form_data.get('contrast_used'),
            'radiation_dose': form_data.get('radiation_dose')
        })
    
    # Clinical Notes specific fields
    elif form_data.get('document_type') in ['Progress Notes', 'Consultation', 'Discharge Summary']:
        fhir_data.update({
            'specialty': form_data.get('specialty'),
            'encounter_type': form_data.get('encounter_type'),
            'chief_complaint': form_data.get('chief_complaint')
        })
    
    # Common fields for all document types
    fhir_data.update({
        'priority': form_data.get('priority', 'routine'),
        'confidentiality': form_data.get('confidentiality', 'normal'),
        'workflow_status': form_data.get('workflow_status', 'completed')
    })
    
    # Remove None values
    return {k: v for k, v in fhir_data.items() if v is not None}


def create_fhir_enhanced_upload_form():
    """
    Create an enhanced upload form that includes FHIR metadata fields.
    Returns HTML form template with FHIR-specific fields.
    """
    return """
    <form method="POST" enctype="multipart/form-data" id="fhir-document-upload">
        <!-- Existing fields -->
        <div class="form-group">
            <label for="file">Document File</label>
            <input type="file" class="form-control" name="file" required>
        </div>
        
        <div class="form-group">
            <label for="document_name">Document Name</label>
            <input type="text" class="form-control" name="document_name">
        </div>
        
        <div class="form-group">
            <label for="document_type">Document Type</label>
            <select class="form-control" name="document_type" id="document_type" onchange="showFHIRFields()">
                <option value="Other">Other</option>
                <option value="Lab Results">Lab Results</option>
                <option value="Imaging">Imaging</option>
                <option value="Radiology">Radiology</option>
                <option value="Progress Notes">Progress Notes</option>
                <option value="Consultation">Consultation</option>
                <option value="Discharge Summary">Discharge Summary</option>
                <option value="Operative Note">Operative Note</option>
                <option value="Pathology">Pathology</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="provider">Provider</label>
            <input type="text" class="form-control" name="provider">
        </div>
        
        <div class="form-group">
            <label for="document_date">Document Date</label>
            <input type="datetime-local" class="form-control" name="document_date">
        </div>
        
        <!-- FHIR-Enhanced Fields -->
        <div id="fhir-metadata-section" style="border-top: 2px solid #007bff; padding-top: 20px; margin-top: 20px;">
            <h5>FHIR Metadata (Optional)</h5>
            <p class="text-muted">These fields structure your document metadata using healthcare standards.</p>
            
            <!-- Lab Results Fields -->
            <div id="lab-fields" style="display: none;">
                <div class="form-group">
                    <label for="lab_test_type">Test Type</label>
                    <select class="form-control" name="lab_test_type">
                        <option value="CBC">Complete Blood Count (CBC)</option>
                        <option value="BMP">Basic Metabolic Panel (BMP)</option>
                        <option value="CMP">Comprehensive Metabolic Panel (CMP)</option>
                        <option value="Lipid Panel">Lipid Panel</option>
                        <option value="HbA1c">Hemoglobin A1c</option>
                        <option value="TSH">Thyroid Stimulating Hormone</option>
                        <option value="Urinalysis">Urinalysis</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="lab_id">Lab ID</label>
                    <input type="text" class="form-control" name="lab_id" placeholder="LAB-2024-001">
                </div>
                
                <div class="form-group">
                    <label for="lab_status">Lab Status</label>
                    <select class="form-control" name="lab_status">
                        <option value="final">Final</option>
                        <option value="preliminary">Preliminary</option>
                        <option value="corrected">Corrected</option>
                        <option value="amended">Amended</option>
                    </select>
                </div>
            </div>
            
            <!-- Imaging Fields -->
            <div id="imaging-fields" style="display: none;">
                <div class="form-group">
                    <label for="imaging_modality">Imaging Modality</label>
                    <select class="form-control" name="imaging_modality">
                        <option value="XRAY">X-Ray</option>
                        <option value="CT">CT Scan</option>
                        <option value="MRI">MRI</option>
                        <option value="ULTRASOUND">Ultrasound</option>
                        <option value="MAMMOGRAPHY">Mammography</option>
                        <option value="NUCLEAR">Nuclear Medicine</option>
                        <option value="PET">PET Scan</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="body_part">Body Part</label>
                    <input type="text" class="form-control" name="body_part" placeholder="Chest, Head, Abdomen, etc.">
                </div>
                
                <div class="form-group">
                    <label for="study_type">Study Type</label>
                    <select class="form-control" name="study_type">
                        <option value="Diagnostic">Diagnostic</option>
                        <option value="Screening">Screening</option>
                        <option value="Follow-up">Follow-up</option>
                        <option value="Emergency">Emergency</option>
                    </select>
                </div>
            </div>
            
            <!-- Clinical Notes Fields -->
            <div id="clinical-fields" style="display: none;">
                <div class="form-group">
                    <label for="specialty">Medical Specialty</label>
                    <select class="form-control" name="specialty">
                        <option value="">Select Specialty</option>
                        <option value="Cardiology">Cardiology</option>
                        <option value="Dermatology">Dermatology</option>
                        <option value="Emergency Medicine">Emergency Medicine</option>
                        <option value="Endocrinology">Endocrinology</option>
                        <option value="Family Medicine">Family Medicine</option>
                        <option value="Gastroenterology">Gastroenterology</option>
                        <option value="Internal Medicine">Internal Medicine</option>
                        <option value="Neurology">Neurology</option>
                        <option value="Oncology">Oncology</option>
                        <option value="Orthopedics">Orthopedics</option>
                        <option value="Pediatrics">Pediatrics</option>
                        <option value="Psychiatry">Psychiatry</option>
                        <option value="Radiology">Radiology</option>
                        <option value="Surgery">Surgery</option>
                        <option value="Urology">Urology</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="encounter_type">Encounter Type</label>
                    <select class="form-control" name="encounter_type">
                        <option value="outpatient">Outpatient</option>
                        <option value="inpatient">Inpatient</option>
                        <option value="emergency">Emergency</option>
                        <option value="virtual">Telemedicine</option>
                    </select>
                </div>
            </div>
            
            <!-- Common FHIR Fields -->
            <div class="form-group">
                <label for="priority">Priority</label>
                <select class="form-control" name="priority">
                    <option value="routine">Routine</option>
                    <option value="urgent">Urgent</option>
                    <option value="stat">STAT</option>
                    <option value="asap">ASAP</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="confidentiality">Confidentiality</label>
                <select class="form-control" name="confidentiality">
                    <option value="normal">Normal</option>
                    <option value="restricted">Restricted</option>
                    <option value="very-restricted">Very Restricted</option>
                </select>
            </div>
        </div>
        
        <button type="submit" class="btn btn-primary">Upload Document with FHIR Metadata</button>
    </form>
    
    <script>
    function showFHIRFields() {
        const documentType = document.getElementById('document_type').value;
        
        // Hide all specific fields
        document.getElementById('lab-fields').style.display = 'none';
        document.getElementById('imaging-fields').style.display = 'none';
        document.getElementById('clinical-fields').style.display = 'none';
        
        // Show relevant fields
        if (documentType === 'Lab Results') {
            document.getElementById('lab-fields').style.display = 'block';
        } else if (documentType === 'Imaging' || documentType === 'Radiology') {
            document.getElementById('imaging-fields').style.display = 'block';
        } else if (['Progress Notes', 'Consultation', 'Discharge Summary', 'Operative Note'].includes(documentType)) {
            document.getElementById('clinical-fields').style.display = 'block';
        }
    }
    </script>
    """


def get_document_fhir_summary(document):
    """
    Get a summary of FHIR metadata for display in document lists.
    
    Args:
        document: MedicalDocument instance
        
    Returns:
        Dictionary with FHIR summary information
    """
    if not document.doc_metadata:
        return {"has_fhir": False}
    
    try:
        metadata_dict = json.loads(document.doc_metadata)
        fhir_data = metadata_dict.get("fhir", {})
        
        summary = {"has_fhir": bool(fhir_data)}
        
        # Extract key FHIR information
        if fhir_data.get("code", {}).get("coding"):
            primary_code = fhir_data["code"]["coding"][0]
            summary["code_display"] = primary_code.get("display", "Unknown")
            summary["code_system"] = primary_code.get("system", "").split("/")[-1]
        
        if fhir_data.get("type", {}).get("coding"):
            primary_type = fhir_data["type"]["coding"][0]
            summary["type_display"] = primary_type.get("display", "Unknown")
        
        if fhir_data.get("category", {}).get("coding"):
            primary_category = fhir_data["category"]["coding"][0]
            summary["category_display"] = primary_category.get("display", "Unknown")
        
        if fhir_data.get("effectiveDateTime"):
            summary["effective_date"] = fhir_data["effectiveDateTime"]
        
        # Extract useful extensions
        extensions = fhir_data.get("extensions", {})
        if extensions.get("test_type"):
            summary["test_type"] = extensions["test_type"]
        if extensions.get("modality"):
            summary["modality"] = extensions["modality"]
        if extensions.get("specialty"):
            summary["specialty"] = extensions["specialty"]
        
        return summary
        
    except (json.JSONDecodeError, KeyError, TypeError):
        return {"has_fhir": False}


def search_documents_by_fhir_metadata(patient_id=None, filters=None):
    """
    Search documents using FHIR metadata filters.
    
    Args:
        patient_id: Optional patient ID to filter by
        filters: Dictionary of FHIR metadata filters
        
    Returns:
        List of matching documents
    """
    query = MedicalDocument.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    documents = query.all()
    
    if not filters:
        return documents
    
    filtered_documents = []
    
    for document in documents:
        if not document.doc_metadata:
            continue
        
        try:
            metadata_dict = json.loads(document.doc_metadata)
            fhir_data = metadata_dict.get("fhir", {})
            
            # Check filters
            match = True
            
            # Filter by FHIR type code
            if filters.get("type_code"):
                type_codings = fhir_data.get("type", {}).get("coding", [])
                type_codes = [coding.get("code") for coding in type_codings]
                if filters["type_code"] not in type_codes:
                    match = False
            
            # Filter by FHIR category
            if filters.get("category_code"):
                category_codings = fhir_data.get("category", {}).get("coding", [])
                category_codes = [coding.get("code") for coding in category_codings]
                if filters["category_code"] not in category_codes:
                    match = False
            
            # Filter by test type (lab results)
            if filters.get("test_type"):
                extensions = fhir_data.get("extensions", {})
                if extensions.get("test_type") != filters["test_type"]:
                    match = False
            
            # Filter by modality (imaging)
            if filters.get("modality"):
                extensions = fhir_data.get("extensions", {})
                if extensions.get("modality") != filters["modality"]:
                    match = False
            
            # Filter by specialty (clinical notes)
            if filters.get("specialty"):
                extensions = fhir_data.get("extensions", {})
                if extensions.get("specialty") != filters["specialty"]:
                    match = False
            
            if match:
                filtered_documents.append(document)
                
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    
    return filtered_documents


# Example usage functions
def example_upload_lab_result():
    """Example of uploading a lab result with FHIR metadata"""
    form_data = {
        'document_name': 'CBC Lab Results',
        'document_type': 'Lab Results',
        'provider': 'Dr. Smith',
        'source_system': 'LabCorp',
        'lab_test_type': 'CBC',
        'lab_id': 'LAB-2024-001',
        'lab_status': 'final',
        'priority': 'routine'
    }
    
    # In your route handler:
    # document = upload_document_with_fhir_metadata(patient_id, file, form_data)
    # return redirect(url_for('patient_detail', id=patient_id))


def example_search_lab_results():
    """Example of searching for lab results using FHIR metadata"""
    filters = {
        'type_code': '11502-2',  # LOINC code for laboratory report
        'test_type': 'CBC'       # Specific test type
    }
    
    # documents = search_documents_by_fhir_metadata(patient_id=123, filters=filters)
    # return render_template('documents_list.html', documents=documents)