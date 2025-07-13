#!/usr/bin/env python3
"""
Automated Screening Routes
Handles the new automated screening system with intelligent status determination
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, date
from app import db
from models import Patient, ScreeningType, Screening
from admin_middleware import admin_required

# Create blueprint for automated screening routes
automated_screening_bp = Blueprint('automated_screening', __name__)

@automated_screening_bp.route('/api/patient/<int:patient_id>/screenings/generate', methods=['POST'])
def generate_patient_screenings_api(patient_id):
    """
    API endpoint to generate automated screenings for a specific patient
    """
    try:
        from automated_screening_engine import ScreeningStatusEngine
        engine = ScreeningStatusEngine()
        screenings = engine.generate_patient_screenings(patient_id)
        
        # Update database with generated screenings
        _update_patient_screenings(patient_id, screenings)
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'screenings_generated': len(screenings),
            'screenings': screenings
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@automated_screening_bp.route('/api/screenings/generate-all', methods=['POST'])
@admin_required
def generate_all_screenings_api():
    """
    API endpoint to regenerate all automated screenings for all patients
    """
    try:
        from automated_screening_engine import ScreeningStatusEngine
        engine = ScreeningStatusEngine()
        all_screenings = engine.generate_all_patient_screenings()
        
        total_generated = 0
        for patient_id, screenings in all_screenings.items():
            _update_patient_screenings(patient_id, screenings)
            total_generated += len(screenings)
        
        return jsonify({
            'success': True,
            'patients_processed': len(all_screenings),
            'total_screenings_generated': total_generated,
            'summary': {pid: len(screenings) for pid, screenings in all_screenings.items()}
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@automated_screening_bp.route('/screenings/automated-view')
def automated_screenings_view():
    """
    View all automated screenings with status filtering
    """
    # Get filter parameters
    status_filter = request.args.get('status', '')
    patient_search = request.args.get('search', '')
    
    # Build query
    query = db.session.query(Screening).join(Patient)
    
    if status_filter:
        query = query.filter(Screening.status == status_filter)
    
    if patient_search:
        query = query.filter(
            (Patient.first_name.ilike(f'%{patient_search}%')) |
            (Patient.last_name.ilike(f'%{patient_search}%')) |
            (Patient.mrn.ilike(f'%{patient_search}%'))
        )
    
    screenings = query.order_by(
        Screening.status.desc(),  # Due first, then Due Soon, etc.
        Patient.last_name,
        Patient.first_name
    ).all()
    
    # Get summary statistics
    status_counts = _get_status_summary()
    
    return render_template('automated_screenings.html',
                         screenings=screenings,
                         status_filter=status_filter,
                         patient_search=patient_search,
                         status_counts=status_counts)

@automated_screening_bp.route('/screenings/refresh-patient/<int:patient_id>', methods=['POST'])
def refresh_patient_screenings(patient_id):
    """
    Refresh automated screenings for a specific patient
    """
    try:
        from automated_screening_engine import ScreeningStatusEngine
        engine = ScreeningStatusEngine()
        screenings = engine.generate_patient_screenings(patient_id)
        _update_patient_screenings(patient_id, screenings)
        
        flash(f'Refreshed {len(screenings)} screenings for patient', 'success')
        
    except Exception as e:
        flash(f'Error refreshing screenings: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('patient_detail', patient_id=patient_id))

@automated_screening_bp.route('/admin/screenings/regenerate-all', methods=['POST'])
@admin_required
def regenerate_all_screenings():
    """
    Admin function to regenerate all automated screenings
    """
    try:
        from automated_screening_engine import ScreeningStatusEngine
        engine = ScreeningStatusEngine()
        all_screenings = engine.generate_all_patient_screenings()
        
        total_generated = 0
        for patient_id, screenings in all_screenings.items():
            _update_patient_screenings(patient_id, screenings)
            total_generated += len(screenings)
        
        flash(f'Successfully regenerated {total_generated} screenings for {len(all_screenings)} patients', 'success')
        
    except Exception as e:
        flash(f'Error regenerating screenings: {str(e)}', 'error')
    
    return redirect(url_for('screening_list'))

def _update_patient_screenings(patient_id: int, screenings_data: list):
    """
    Update database with generated screening data using proper many-to-many relationships
    
    Args:
        patient_id: Patient ID
        screenings_data: List of screening dictionaries from engine
    """
    try:
        for screening_data in screenings_data:
            # Find existing screening or create new one
            existing = Screening.query.filter_by(
                patient_id=patient_id,
                screening_type=screening_data['screening_type']
            ).first()
            
            if existing:
                # CRITICAL VALIDATION: Complete status requires matched documents
                proposed_status = screening_data['status']
                has_valid_documents = 'matched_documents' in screening_data and screening_data['matched_documents']
                
                if proposed_status == 'Complete' and not has_valid_documents:
                    print(f"  ⚠️  Correcting invalid Complete status to Incomplete for {screening_data['screening_type']} - no matched documents")
                    existing.status = 'Incomplete'
                else:
                    existing.status = proposed_status
                    
                existing.last_completed = screening_data['last_completed']
                existing.frequency = screening_data['frequency']
                existing.notes = screening_data['notes']
                existing.updated_at = datetime.now()
                
                # Clear existing document relationships using direct SQL for efficiency
                try:
                    from sqlalchemy import text
                    result = db.session.execute(
                        text("DELETE FROM screening_documents WHERE screening_id = :screening_id"),
                        {'screening_id': existing.id}
                    )
                    if result.rowcount > 0:
                        print(f"  → Cleared {result.rowcount} existing document relationships for screening {existing.id}")
                except Exception as clear_error:
                    print(f"  ⚠️  Error clearing existing documents: {clear_error}")
                    # Try ORM method as fallback
                    try:
                        with db.session.no_autoflush:
                            existing_docs = list(existing.documents.all())
                        for doc in existing_docs:
                            existing.remove_document(doc)
                    except Exception as orm_error:
                        print(f"  ⚠️  ORM clear also failed: {orm_error}")
                
                current_screening = existing
            else:
                # CRITICAL VALIDATION: Complete status requires matched documents for new screenings too
                proposed_status = screening_data['status']
                has_valid_documents = 'matched_documents' in screening_data and screening_data['matched_documents']
                
                if proposed_status == 'Complete' and not has_valid_documents:
                    print(f"  ⚠️  Correcting invalid Complete status to Incomplete for new {screening_data['screening_type']} - no matched documents")
                    validated_status = 'Incomplete'
                else:
                    validated_status = proposed_status
                
                # Create new screening
                new_screening = Screening(
                    patient_id=patient_id,
                    screening_type=screening_data['screening_type'],
                    status=validated_status,
                    last_completed=screening_data['last_completed'],
                    frequency=screening_data['frequency'],
                    notes=screening_data['notes'],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(new_screening)
                db.session.flush()  # Flush to get the ID
                
                current_screening = new_screening
            
            # Add document relationships using the new many-to-many table with validation
            linked_document_count = 0
            if 'matched_documents' in screening_data and screening_data['matched_documents']:
                for document in screening_data['matched_documents']:
                    try:
                        # Get a fresh document instance from the database to avoid session conflicts
                        from models import MedicalDocument
                        fresh_document = db.session.get(MedicalDocument, document.id)
                        
                        if fresh_document and _validate_document_exists(fresh_document):
                            current_screening.add_document(fresh_document, confidence_score=1.0, match_source='automated')
                            linked_document_count += 1
                            print(f"  → Linked document {fresh_document.filename} to screening {current_screening.screening_type}")
                        else:
                            print(f"  → Skipping deleted/invalid document {document.id}")
                    except Exception as doc_error:
                        print(f"  → Error linking document {document.id}: {doc_error}")
                        # Continue with other documents even if one fails
            
            # FINAL VALIDATION: If marked Complete but no documents were actually linked, correct the status
            if current_screening.status == 'Complete' and linked_document_count == 0:
                print(f"  ⚠️  FINAL CORRECTION: Complete status to Incomplete for {current_screening.screening_type} - no documents successfully linked")
                current_screening.status = 'Incomplete'
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise e

def _get_status_summary():
    """Get summary counts for each status"""
    from sqlalchemy import func
    
    summary = db.session.query(
        Screening.status,
        func.count(Screening.id).label('count')
    ).group_by(Screening.status).all()
    
    return {status: count for status, count in summary}

def _validate_document_exists(document):
    """Validate that a document exists in the database"""
    try:
        if not document or not hasattr(document, 'id'):
            return False
        
        # Simple check - if we have a document instance, it should be valid
        # More thorough validation would require additional database queries
        return document.id is not None and document.id > 0
        
    except Exception as e:
        print(f"Error validating document existence: {e}")
        return False

def cleanup_orphaned_screening_documents():
    """Clean up orphaned document relationships across all screenings"""
    try:
        from models import Screening
        total_cleaned = 0
        
        all_screenings = Screening.query.all()
        for screening in all_screenings:
            cleaned_count = screening.validate_and_cleanup_document_relationships()
            total_cleaned += cleaned_count
            
        if total_cleaned > 0:
            db.session.commit()
            print(f"Cleaned up {total_cleaned} orphaned document relationships across all screenings")
            
        return total_cleaned
        
    except Exception as e:
        print(f"Error during orphaned document cleanup: {e}")
        db.session.rollback()
        return 0

# Utility function to register the blueprint
def register_automated_screening_routes(app):
    """Register automated screening routes with the Flask app"""
    app.register_blueprint(automated_screening_bp)