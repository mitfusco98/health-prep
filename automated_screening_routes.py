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
        from unified_screening_engine import unified_engine
        engine = unified_engine
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
        from unified_screening_engine import unified_engine
        engine = unified_engine
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
        from unified_screening_engine import unified_engine
        engine = unified_engine
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
        from unified_screening_engine import unified_engine
        engine = unified_engine
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
        # Add comprehensive timeout protection starting with database connection
        import signal
        def db_timeout_handler(signum, frame):
            raise TimeoutError("Database operation timed out")
        
        # Test database connection first with timeout protection
        signal.signal(signal.SIGALRM, db_timeout_handler)
        signal.alarm(2)  # 2 second timeout for connection test
        
        try:
            # Test connection with simple query
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            signal.alarm(0)  # Cancel timeout
        except TimeoutError:
            signal.alarm(0)
            print(f"⏱️  Database connection timeout for patient {patient_id}, skipping")
            return
        except Exception as conn_error:
            signal.alarm(0)
            print(f"⚠️  Database connection error for patient {patient_id}: {conn_error}")
            return
        
        # Now load existing screenings with timeout protection
        signal.signal(signal.SIGALRM, db_timeout_handler)
        signal.alarm(3)  # 3 second timeout for query
        
        try:
            # Optimize: Load all existing screenings for patient at once
            existing_screenings = {
                screening.screening_type: screening 
                for screening in Screening.query.filter_by(patient_id=patient_id).all()
            }
            signal.alarm(0)  # Cancel timeout
        except TimeoutError:
            signal.alarm(0)
            print(f"⏱️  Database query timeout loading screenings for patient {patient_id}, skipping")
            return
        except Exception as query_error:
            signal.alarm(0)
            print(f"⚠️  Database query error loading screenings for patient {patient_id}: {query_error}")
            return
        
        for screening_data in screenings_data:
            # Use pre-loaded screening instead of individual query
            existing = existing_screenings.get(screening_data['screening_type'])
            
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
                
                # Clear existing document relationships with timeout protection
                try:
                    from sqlalchemy import text
                    
                    def clear_timeout_handler(signum, frame):
                        raise TimeoutError("Document clearing timed out")
                    
                    # Set 2-second timeout for this operation
                    signal.signal(signal.SIGALRM, clear_timeout_handler)
                    signal.alarm(2)
                    
                    try:
                        result = db.session.execute(
                            text("DELETE FROM screening_documents WHERE screening_id = :screening_id"),
                            {'screening_id': existing.id}
                        )
                        signal.alarm(0)  # Cancel timeout
                        if result.rowcount > 0:
                            print(f"  → Cleared {result.rowcount} existing document relationships for screening {existing.id}")
                    except TimeoutError:
                        signal.alarm(0)
                        print(f"  ⚠️  Timeout clearing documents for screening {existing.id}, skipping relationship update")
                        # Skip document relationship updates if clearing times out
                        continue
                        
                except Exception as clear_error:
                    print(f"  ⚠️  Error clearing existing documents: {clear_error}")
                    # Skip this screening update if we can't clear relationships safely
                    continue
                
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
            
            # Add document relationships using batch processing to avoid individual flushes
            linked_document_count = 0
            if 'matched_documents' in screening_data and screening_data['matched_documents']:
                # Process documents in batch mode to avoid individual database flushes
                valid_documents = []
                
                # First pass: validate documents in bulk with timeout protection
                signal.signal(signal.SIGALRM, db_timeout_handler)
                signal.alarm(3)  # 3 second timeout for bulk document validation
                
                try:
                    # Get all document IDs at once
                    document_ids = [doc.id for doc in screening_data['matched_documents']]
                    
                    # Bulk fetch all documents at once to avoid N+1 queries
                    from models import MedicalDocument
                    from sqlalchemy import text
                    
                    if document_ids:
                        # Use raw SQL for faster bulk fetch
                        id_placeholders = ','.join([str(id) for id in document_ids])
                        result = db.session.execute(
                            text(f"SELECT id, filename FROM medical_document WHERE id IN ({id_placeholders})")
                        )
                        existing_doc_data = {row.id: row.filename for row in result}
                        
                        # Only include documents that exist in database
                        for document in screening_data['matched_documents']:
                            if document.id in existing_doc_data:
                                valid_documents.append(document)
                            else:
                                print(f"  → Skipping deleted document {document.id}")
                    
                    signal.alarm(0)  # Cancel timeout
                except TimeoutError:
                    signal.alarm(0)
                    print(f"  ⏱️  Document validation timeout for screening {current_screening.screening_type}, skipping document linking")
                    valid_documents = []  # Skip all documents for this screening
                except Exception as bulk_error:
                    signal.alarm(0)
                    print(f"  ⚠️  Bulk document validation error: {bulk_error}")
                    # Fallback to the documents we have (assume they're valid)
                    valid_documents = screening_data['matched_documents'][:10]  # Limit to 10 as safety
                
                # Second pass: link documents in batch mode with limits to prevent timeouts
                max_documents_per_screening = 50  # Limit to prevent timeouts
                documents_to_process = valid_documents[:max_documents_per_screening]
                
                if len(valid_documents) > max_documents_per_screening:
                    print(f"  ⚠️  Limiting to {max_documents_per_screening} documents out of {len(valid_documents)} for screening {current_screening.screening_type}")
                
                # Bulk insert relationships using raw SQL for speed
                if documents_to_process:
                    try:
                        signal.signal(signal.SIGALRM, db_timeout_handler)
                        signal.alarm(2)  # 2 second timeout for bulk insert
                        
                        # Use raw SQL for bulk insert of screening-document relationships
                        from sqlalchemy import text
                        insert_values = []
                        for document in documents_to_process:
                            insert_values.append(f"({current_screening.id}, {document.id}, 1.0, 'automated')")
                        
                        if insert_values:
                            # First clear existing relationships for this screening
                            db.session.execute(
                                text("DELETE FROM screening_documents WHERE screening_id = :screening_id"),
                                {'screening_id': current_screening.id}
                            )
                            
                            # Bulk insert new relationships
                            values_str = ','.join(insert_values)
                            db.session.execute(
                                text(f"INSERT INTO screening_documents (screening_id, document_id, confidence_score, match_source) VALUES {values_str}")
                            )
                            
                            linked_document_count = len(documents_to_process)
                            print(f"  → Bulk linked {linked_document_count} documents to screening {current_screening.screening_type}")
                        
                        signal.alarm(0)  # Cancel timeout
                    except TimeoutError:
                        signal.alarm(0)
                        print(f"  ⏱️  Bulk document linking timeout for screening {current_screening.screening_type}")
                        linked_document_count = 0
                    except Exception as bulk_link_error:
                        signal.alarm(0)
                        print(f"  ⚠️  Bulk document linking error: {bulk_link_error}")
                        linked_document_count = 0
            
            # Skip metadata processing since we're using bulk SQL operations
            
            # FINAL VALIDATION: If marked Complete but no documents were actually linked, correct the status
            if current_screening.status == 'Complete' and linked_document_count == 0:
                print(f"  ⚠️  FINAL CORRECTION: Complete status to Incomplete for {current_screening.screening_type} - no documents successfully linked")
                current_screening.status = 'Incomplete'
        
        # Commit with error handling and timeout protection to prevent SystemExit issues
        try:
            signal.signal(signal.SIGALRM, db_timeout_handler)
            signal.alarm(8)  # Increased to 8 seconds for batch commit with connection recovery
            db.session.commit()
            signal.alarm(0)
            print(f"✅ Updated {len(screenings_data)} screenings for patient {patient_id}")
        except TimeoutError:
            signal.alarm(0)
            try:
                db.session.rollback()
            except:
                pass  # Ignore rollback errors during timeout
            print(f"⏱️  Database commit timeout for patient {patient_id} - screenings skipped")
            # Don't raise - continue with other patients
        except Exception as commit_error:
            signal.alarm(0)
            try:
                db.session.rollback()
            except:
                pass  # Ignore rollback errors during connection issues
            print(f"ERROR during screening update commit: {commit_error}")
            # Don't raise - continue with other patients
        
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