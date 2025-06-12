"""
Enhanced Document Upload Routes with Dual Storage

Routes that save documents with both internal keys and FHIR-style keys,
maintaining backward compatibility while supporting Epic and FHIR exports.
All actions are logged to admin logs with timestamps and file details.
"""

from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import os

from models import Patient, MedicalDocument, db
from dual_storage_system import (
    save_document_dual_keys,
    save_prep_sheet_dual_keys,
    get_document_metadata,
    migrate_document_metadata
)
from fhir_prep_sheet_integration import generate_fhir_prep_sheet
from admin_middleware import log_admin_access
from utils import allowed_file

# Create blueprint for enhanced document routes
enhanced_docs = Blueprint('enhanced_docs', __name__)

@enhanced_docs.route('/upload_document_enhanced/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def upload_document_enhanced(patient_id):
    """
    Enhanced document upload with dual storage (internal + FHIR keys)
    """
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        # Validate file upload
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Secure filename
                filename = secure_filename(file.filename)
                
                # Get form data
                document_name = request.form.get('document_name', filename)
                document_type = request.form.get('document_type', 'Unknown')
                provider = request.form.get('provider', '')
                document_date_str = request.form.get('document_date', '')
                
                # Parse document date
                document_date = None
                if document_date_str:
                    try:
                        document_date = datetime.strptime(document_date_str, '%Y-%m-%d')
                    except ValueError:
                        document_date = datetime.utcnow()
                else:
                    document_date = datetime.utcnow()
                
                # Read file content
                file_content = file.read()
                
                # Determine if binary content
                is_binary = not filename.lower().endswith(('.txt', '.md', '.csv'))
                mime_type = file.content_type or 'application/octet-stream'
                
                # Extract text content for analysis
                text_content = None
                if not is_binary:
                    try:
                        text_content = file_content.decode('utf-8')
                    except UnicodeDecodeError:
                        is_binary = True
                        text_content = None
                
                # Create MedicalDocument object
                document = MedicalDocument(
                    patient_id=patient_id,
                    filename=filename,
                    document_name=document_name,
                    document_type=document_type,
                    content=text_content,
                    binary_content=file_content if is_binary else None,
                    is_binary=is_binary,
                    mime_type=mime_type,
                    provider=provider,
                    document_date=document_date,
                    source_system='Manual Upload',
                    created_at=datetime.utcnow()
                )
                
                # Save to database first
                db.session.add(document)
                db.session.commit()
                
                # Save with dual storage system
                storage_result = save_document_dual_keys(
                    document=document,
                    content=text_content,
                    user_id=current_user.id
                )
                
                if storage_result['success']:
                    # Update database with dual metadata
                    db.session.commit()
                    
                    # Additional admin logging for file upload
                    log_admin_access(
                        action="Document Upload Completed",
                        details={
                            'upload_timestamp': datetime.utcnow().isoformat(),
                            'filename': filename,
                            'original_filename': file.filename,
                            'document_name': document_name,
                            'document_type': document_type,
                            'patient_id': patient_id,
                            'patient_name': f"{patient.first_name} {patient.last_name}",
                            'document_id': document.id,
                            'file_size': len(file_content),
                            'mime_type': mime_type,
                            'is_binary': is_binary,
                            'provider': provider,
                            'document_date': document_date.isoformat(),
                            'storage_type': 'dual',
                            'internal_keys_count': storage_result['internal_keys_count'],
                            'fhir_keys_count': storage_result['fhir_keys_count'],
                            'user_id': current_user.id,
                            'user_name': current_user.username
                        },
                        user_id=current_user.id
                    )
                    
                    flash(f'Document "{document_name}" uploaded successfully with dual storage', 'success')
                    return redirect(url_for('patient_detail', patient_id=patient_id))
                else:
                    # Storage failed, but document was saved
                    flash(f'Document uploaded but storage system failed: {storage_result.get("error", "Unknown error")}', 'warning')
                    return redirect(url_for('patient_detail', patient_id=patient_id))
                
            except Exception as e:
                db.session.rollback()
                
                # Log upload error
                log_admin_access(
                    action="Document Upload Error",
                    details={
                        'error_timestamp': datetime.utcnow().isoformat(),
                        'filename': getattr(file, 'filename', 'unknown'),
                        'patient_id': patient_id,
                        'error_message': str(e),
                        'user_id': current_user.id,
                        'user_name': current_user.username
                    },
                    user_id=current_user.id
                )
                
                flash(f'Error uploading document: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type', 'error')
            return redirect(request.url)
    
    return render_template('upload_document_enhanced.html', patient=patient)

@enhanced_docs.route('/generate_prep_sheet_enhanced/<int:patient_id>')
@login_required
def generate_prep_sheet_enhanced(patient_id):
    """
    Enhanced prep sheet generation with dual storage and FHIR compliance
    """
    try:
        patient = Patient.query.get_or_404(patient_id)
        appointment_date = datetime.now().date()
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"prep_sheet_{patient.mrn}_{timestamp}.pdf"
        
        # Generate FHIR-compliant prep sheet data
        fhir_prep_data = generate_fhir_prep_sheet(patient, appointment_date)
        
        # Extract data for traditional prep sheet format
        prep_data = {
            'patient': patient,
            'screenings': _extract_screenings_from_fhir(fhir_prep_data),
            'conditions': _extract_conditions_from_fhir(fhir_prep_data),
            'vitals': _extract_vitals_from_fhir(fhir_prep_data),
            'documents': _extract_documents_from_fhir(fhir_prep_data),
            'immunizations': _extract_immunizations_from_fhir(fhir_prep_data),
            'generated_at': datetime.utcnow()
        }
        
        # Save prep sheet with dual storage
        storage_result = save_prep_sheet_dual_keys(
            patient_id=patient_id,
            prep_data=prep_data,
            filename=filename,
            user_id=current_user.id
        )
        
        if storage_result['success']:
            # Additional detailed logging
            log_admin_access(
                action="Prep Sheet Generated Successfully",
                details={
                    'generation_timestamp': datetime.utcnow().isoformat(),
                    'filename': filename,
                    'patient_id': patient_id,
                    'patient_name': f"{patient.first_name} {patient.last_name}",
                    'patient_mrn': patient.mrn,
                    'appointment_date': appointment_date.isoformat(),
                    'sections_generated': storage_result['metadata']['internal']['sections'],
                    'screening_count': storage_result['metadata']['internal']['screening_count'],
                    'document_count': storage_result['metadata']['internal']['document_count'],
                    'fhir_compliant': True,
                    'storage_type': 'dual',
                    'user_id': current_user.id,
                    'user_name': current_user.username
                },
                user_id=current_user.id
            )
            
            # Render prep sheet with enhanced data
            return render_template('prep_sheet_enhanced.html', 
                                 prep_data=prep_data,
                                 fhir_data=fhir_prep_data,
                                 filename=filename,
                                 storage_metadata=storage_result['metadata'])
        else:
            flash(f'Error generating prep sheet: {storage_result.get("error", "Unknown error")}', 'error')
            return redirect(url_for('patient_detail', patient_id=patient_id))
            
    except Exception as e:
        # Log generation error
        log_admin_access(
            action="Prep Sheet Generation Error",
            details={
                'error_timestamp': datetime.utcnow().isoformat(),
                'patient_id': patient_id,
                'error_message': str(e),
                'user_id': current_user.id,
                'user_name': current_user.username
            },
            user_id=current_user.id
        )
        
        flash(f'Error generating prep sheet: {str(e)}', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))

@enhanced_docs.route('/document_metadata/<int:document_id>')
@login_required
def view_document_metadata(document_id):
    """
    View document metadata in both internal and FHIR formats
    """
    document = MedicalDocument.query.get_or_404(document_id)
    
    # Get metadata in both formats
    all_metadata = get_document_metadata(document, 'both')
    internal_metadata = get_document_metadata(document, 'internal')
    fhir_metadata = get_document_metadata(document, 'fhir')
    
    # Log metadata access
    log_admin_access(
        action="Document Metadata Viewed",
        details={
            'access_timestamp': datetime.utcnow().isoformat(),
            'document_id': document_id,
            'filename': document.filename,
            'patient_id': document.patient_id,
            'has_internal_keys': bool(internal_metadata),
            'has_fhir_keys': bool(fhir_metadata),
            'user_id': current_user.id,
            'user_name': current_user.username
        },
        user_id=current_user.id
    )
    
    return render_template('document_metadata_view.html',
                         document=document,
                         all_metadata=all_metadata,
                         internal_metadata=internal_metadata,
                         fhir_metadata=fhir_metadata)

@enhanced_docs.route('/migrate_document_metadata/<int:document_id>')
@login_required
def migrate_document_metadata_route(document_id):
    """
    Migrate legacy document metadata to dual-key format
    """
    document = MedicalDocument.query.get_or_404(document_id)
    
    try:
        migration_result = migrate_document_metadata(document)
        
        if migration_result['success']:
            db.session.commit()
            
            # Log successful migration
            log_admin_access(
                action="Document Metadata Migrated",
                details={
                    'migration_timestamp': datetime.utcnow().isoformat(),
                    'document_id': document_id,
                    'filename': document.filename,
                    'patient_id': document.patient_id,
                    'migrated_from': migration_result['migrated_from'],
                    'preserved_fields': migration_result.get('preserved_fields', 0),
                    'user_id': current_user.id,
                    'user_name': current_user.username
                },
                user_id=current_user.id
            )
            
            flash('Document metadata migrated to dual-key format successfully', 'success')
        else:
            flash(f'Migration failed: {migration_result.get("reason", "Unknown error")}', 'warning')
            
    except Exception as e:
        db.session.rollback()
        
        # Log migration error
        log_admin_access(
            action="Document Metadata Migration Error",
            details={
                'error_timestamp': datetime.utcnow().isoformat(),
                'document_id': document_id,
                'error_message': str(e),
                'user_id': current_user.id,
                'user_name': current_user.username
            },
            user_id=current_user.id
        )
        
        flash(f'Migration error: {str(e)}', 'error')
    
    return redirect(url_for('enhanced_docs.view_document_metadata', document_id=document_id))

@enhanced_docs.route('/bulk_migrate_metadata')
@login_required
def bulk_migrate_metadata():
    """
    Bulk migrate all legacy document metadata to dual-key format
    """
    if not current_user.is_admin:
        flash('Admin access required', 'error')
        return redirect(url_for('index'))
    
    try:
        documents = MedicalDocument.query.all()
        migrated_count = 0
        error_count = 0
        
        for document in documents:
            try:
                migration_result = migrate_document_metadata(document)
                if migration_result['success']:
                    migrated_count += 1
                elif migration_result.get('reason') != 'Already in dual format':
                    error_count += 1
            except Exception:
                error_count += 1
        
        db.session.commit()
        
        # Log bulk migration
        log_admin_access(
            action="Bulk Metadata Migration Completed",
            details={
                'migration_timestamp': datetime.utcnow().isoformat(),
                'total_documents': len(documents),
                'migrated_count': migrated_count,
                'error_count': error_count,
                'user_id': current_user.id,
                'user_name': current_user.username
            },
            user_id=current_user.id
        )
        
        flash(f'Bulk migration completed: {migrated_count} migrated, {error_count} errors', 'info')
        
    except Exception as e:
        db.session.rollback()
        
        # Log bulk migration error
        log_admin_access(
            action="Bulk Metadata Migration Error",
            details={
                'error_timestamp': datetime.utcnow().isoformat(),
                'error_message': str(e),
                'user_id': current_user.id,
                'user_name': current_user.username
            },
            user_id=current_user.id
        )
        
        flash(f'Bulk migration error: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

# Helper functions for extracting data from FHIR bundles

def _extract_screenings_from_fhir(fhir_bundle):
    """Extract screening recommendations from FHIR bundle"""
    screenings = []
    
    for entry in fhir_bundle.get('entry', []):
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'ServiceRequest':
            screenings.append({
                'name': resource.get('code', {}).get('coding', [{}])[0].get('display', 'Unknown'),
                'priority': resource.get('priority', 'medium'),
                'due_date': resource.get('occurrenceDateTime', ''),
                'notes': resource.get('note', [{}])[0].get('text', '') if resource.get('note') else '',
                'fhir_code': resource.get('code', {}).get('coding', [{}])[0].get('code', '')
            })
    
    return screenings

def _extract_conditions_from_fhir(fhir_bundle):
    """Extract conditions from FHIR bundle"""
    conditions = []
    
    for entry in fhir_bundle.get('entry', []):
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'Condition':
            conditions.append({
                'name': resource.get('code', {}).get('text', 'Unknown'),
                'status': resource.get('clinicalStatus', {}).get('coding', [{}])[0].get('display', 'Unknown'),
                'onset_date': resource.get('onsetDateTime', ''),
                'notes': resource.get('note', [{}])[0].get('text', '') if resource.get('note') else ''
            })
    
    return conditions

def _extract_vitals_from_fhir(fhir_bundle):
    """Extract vital signs from FHIR bundle"""
    vitals = []
    
    for entry in fhir_bundle.get('entry', []):
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'Observation':
            category = resource.get('category', [{}])[0].get('coding', [{}])[0].get('code', '')
            if category == 'vital-signs':
                vitals.append({
                    'name': resource.get('code', {}).get('coding', [{}])[0].get('display', 'Unknown'),
                    'value': resource.get('valueQuantity', {}).get('value', ''),
                    'unit': resource.get('valueQuantity', {}).get('unit', ''),
                    'date': resource.get('effectiveDateTime', ''),
                    'components': resource.get('component', [])
                })
    
    return vitals

def _extract_documents_from_fhir(fhir_bundle):
    """Extract documents from FHIR bundle"""
    documents = []
    
    for entry in fhir_bundle.get('entry', []):
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'DocumentReference':
            documents.append({
                'name': resource.get('description', 'Unknown'),
                'type': resource.get('type', {}).get('coding', [{}])[0].get('display', 'Unknown'),
                'date': resource.get('date', ''),
                'author': resource.get('author', [{}])[0].get('display', '') if resource.get('author') else ''
            })
    
    return documents

def _extract_immunizations_from_fhir(fhir_bundle):
    """Extract immunizations from FHIR bundle"""
    immunizations = []
    
    for entry in fhir_bundle.get('entry', []):
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'Immunization':
            immunizations.append({
                'vaccine': resource.get('vaccineCode', {}).get('text', 'Unknown'),
                'date': resource.get('occurrenceDateTime', ''),
                'status': resource.get('status', 'unknown')
            })
    
    return immunizations

# Register blueprint function
def register_enhanced_document_routes(app):
    """Register enhanced document routes with Flask app"""
    app.register_blueprint(enhanced_docs)