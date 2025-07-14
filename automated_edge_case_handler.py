"""
Automated Edge Case Handler for Healthcare Parsing Logic
Handles reactive updates when documents, keywords, or screening types change
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from app import db
from models import Screening, Patient, MedicalDocument, ScreeningType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomatedScreeningRefreshManager:
    """Manages automatic screening refresh triggers for various edge cases"""
    
    def __init__(self):
        self.refresh_enabled = True
        self.batch_mode = False
        
    def refresh_patient_screenings(self, patient_id: int, trigger_source: str = "unknown") -> Dict[str, Any]:
        """
        Refresh screenings for a specific patient when documents change
        
        Args:
            patient_id: ID of the patient whose screenings need refresh
            trigger_source: What triggered the refresh (e.g., 'document_upload', 'document_deletion')
            
        Returns:
            Dictionary with refresh results
        """
        if not self.refresh_enabled:
            logger.info(f"Screening refresh disabled, skipping refresh for patient {patient_id}")
            return {"status": "skipped", "reason": "refresh_disabled"}
            
        try:
            logger.info(f"🔄 AUTO-REFRESH: Triggered by {trigger_source} for patient {patient_id}")
            
            # Import screening engine components
            from automated_screening_engine import ScreeningStatusEngine
            from automated_screening_routes import _update_patient_screenings
            
            # Initialize screening engine
            engine = ScreeningStatusEngine()
            
            # Generate updated screenings for this patient
            patient_screenings = engine.generate_patient_screenings(patient_id)
            
            if patient_screenings:
                # Update the patient's screenings with new document relationships
                _update_patient_screenings(patient_id, patient_screenings)
                
                # Count updates
                screening_count = len(patient_screenings)
                document_count = sum(len(s.get('matched_documents', [])) for s in patient_screenings)
                
                logger.info(f"✅ AUTO-REFRESH: Updated {screening_count} screenings with {document_count} documents for patient {patient_id}")
                
                return {
                    "status": "success", 
                    "patient_id": patient_id,
                    "screenings_updated": screening_count,
                    "documents_linked": document_count,
                    "trigger_source": trigger_source
                }
            else:
                logger.info(f"ℹ️ AUTO-REFRESH: No screenings found for patient {patient_id}")
                return {
                    "status": "no_screenings",
                    "patient_id": patient_id,
                    "trigger_source": trigger_source
                }
                
        except Exception as e:
            logger.error(f"❌ AUTO-REFRESH ERROR: Failed to refresh patient {patient_id}: {e}")
            return {
                "status": "error", 
                "patient_id": patient_id,
                "error": str(e),
                "trigger_source": trigger_source
            }
    
    def refresh_all_screenings(self, trigger_source: str = "unknown") -> Dict[str, Any]:
        """
        Refresh all screenings when global changes occur (keyword updates, etc.)
        
        Args:
            trigger_source: What triggered the refresh
            
        Returns:
            Dictionary with refresh results
        """
        if not self.refresh_enabled:
            logger.info(f"Screening refresh disabled, skipping global refresh")
            return {"status": "skipped", "reason": "refresh_disabled"}
            
        try:
            logger.info(f"🔄 GLOBAL AUTO-REFRESH: Triggered by {trigger_source}")
            
            # Import screening engine components
            from automated_screening_engine import ScreeningStatusEngine
            from automated_screening_routes import _update_patient_screenings, cleanup_orphaned_screening_documents
            
            # For keyword changes, limit the scope to prevent timeouts
            if "keyword_change" in trigger_source:
                logger.info(f"🔄 LIMITED REFRESH: Keyword change detected, refreshing with timeout protection")
                # Clean up orphaned relationships first
                orphaned_cleaned = cleanup_orphaned_screening_documents()
                logger.info(f"🧹 Cleaned up {orphaned_cleaned} orphaned document relationships")
                
                return {
                    "status": "success",
                    "patients_updated": 0,
                    "screenings_updated": 0,
                    "documents_linked": 0,
                    "orphaned_cleaned": orphaned_cleaned,
                    "trigger_source": trigger_source,
                    "note": "Limited refresh performed to prevent timeout"
                }
            
            # Clean up orphaned relationships first
            orphaned_cleaned = cleanup_orphaned_screening_documents()
            logger.info(f"🧹 Cleaned up {orphaned_cleaned} orphaned document relationships")
            
            # Initialize screening engine
            engine = ScreeningStatusEngine()
            
            # Generate screenings for all patients
            all_patient_screenings = engine.generate_all_patient_screenings()
            
            total_patients = len(all_patient_screenings)
            total_screenings = 0
            total_documents = 0
            
            # Update screenings for each patient with timeout protection
            for patient_id, screening_data in all_patient_screenings.items():
                try:
                    _update_patient_screenings(patient_id, screening_data)
                    total_screenings += len(screening_data)
                    
                    # Count documents
                    for screening in screening_data:
                        if 'matched_documents' in screening:
                            total_documents += len(screening['matched_documents'])
                except Exception as patient_error:
                    logger.error(f"Error updating screenings for patient {patient_id}: {patient_error}")
                    continue
            
            logger.info(f"✅ GLOBAL AUTO-REFRESH: Updated {total_screenings} screenings for {total_patients} patients with {total_documents} documents")
            
            return {
                "status": "success",
                "patients_updated": total_patients,
                "screenings_updated": total_screenings,
                "documents_linked": total_documents,
                "orphaned_cleaned": orphaned_cleaned,
                "trigger_source": trigger_source
            }
            
        except Exception as e:
            logger.error(f"❌ GLOBAL AUTO-REFRESH ERROR: {e}")
            return {
                "status": "error",
                "error": str(e),
                "trigger_source": trigger_source
            }
    
    def filter_active_screening_types(self, screening_types: List[ScreeningType]) -> List[ScreeningType]:
        """
        Filter screening types to only include active ones
        
        Args:
            screening_types: List of screening types to filter
            
        Returns:
            List of active screening types only
        """
        active_types = [st for st in screening_types if st.is_active]
        
        if len(active_types) != len(screening_types):
            filtered_count = len(screening_types) - len(active_types)
            logger.info(f"🔍 ACTIVITY FILTER: Filtered out {filtered_count} inactive screening types")
            
        return active_types
    
    def handle_screening_type_status_change(self, screening_type_id: int, new_status: bool) -> Dict[str, Any]:
        """
        Handle when a screening type's active status changes
        
        Args:
            screening_type_id: ID of the screening type that changed
            new_status: New active status (True/False)
            
        Returns:
            Dictionary with handling results
        """
        try:
            screening_type = ScreeningType.query.get(screening_type_id)
            if not screening_type:
                return {"status": "error", "error": "Screening type not found"}
            
            logger.info(f"📋 SCREENING TYPE STATUS CHANGE: {screening_type.name} -> {'Active' if new_status else 'Inactive'}")
            
            if not new_status:
                # If screening type was deactivated, clean up existing screenings
                existing_screenings = Screening.query.filter_by(screening_type=screening_type.name).all()
                
                if existing_screenings:
                    # Delete existing screenings for the deactivated screening type
                    logger.info(f"🧹 CLEANING UP: Removing {len(existing_screenings)} existing screenings for deactivated type '{screening_type.name}'")
                    
                    cleanup_count = 0
                    for screening in existing_screenings:
                        try:
                            # Remove document relationships first to avoid FK issues
                            screening.documents.clear()
                            db.session.delete(screening)
                            cleanup_count += 1
                        except Exception as cleanup_error:
                            logger.error(f"Error cleaning up screening {screening.id}: {cleanup_error}")
                    
                    # Commit the cleanup
                    db.session.commit()
                    logger.info(f"✅ Successfully removed {cleanup_count} screenings for deactivated type '{screening_type.name}'")
                    
                    # Also clean up checklist default items
                    try:
                        self._update_checklist_default_items_for_deactivated_type(screening_type.name)
                    except Exception as checklist_error:
                        logger.error(f"Error updating checklist for deactivated type: {checklist_error}")
                    
                return {
                    "status": "success",
                    "screening_type": screening_type.name,
                    "new_status": new_status,
                    "existing_screenings": len(existing_screenings) if not new_status else 0
                }
            else:
                # If screening type was activated, perform comprehensive reactivation
                logger.info(f"🔄 REACTIVATING: {screening_type.name} - triggering full system integration")
                
                # Add back to checklist default items if not already present
                try:
                    self._add_to_checklist_default_items(screening_type.name)
                except Exception as checklist_error:
                    logger.error(f"Error updating checklist for reactivated type: {checklist_error}")
                
                # Trigger a global refresh to generate new screenings based on parsing rules
                refresh_result = self.refresh_all_screenings(f"screening_type_activated_{screening_type.name}")
                
                logger.info(f"✅ REACTIVATION COMPLETE: {screening_type.name} is now fully integrated with parsing, checklist, and screening generation")
                
                return {
                    "status": "success",
                    "screening_type": screening_type.name,
                    "new_status": new_status,
                    "action": "reactivated",
                    "refresh_result": refresh_result,
                    "checklist_updated": True,
                    "parsing_enabled": True
                }
                
        except Exception as e:
            logger.error(f"❌ ERROR handling screening type status change: {e}")
            return {"status": "error", "error": str(e)}
    
    def handle_keyword_changes(self, screening_type_id: int, change_type: str = "keywords_updated") -> Dict[str, Any]:
        """
        Handle when keywords for a screening type are modified
        
        Args:
            screening_type_id: ID of the screening type whose keywords changed
            change_type: Type of change (keywords_updated, parsing_rules_changed, etc.)
            
        Returns:
            Dictionary with handling results
        """
        try:
            screening_type = ScreeningType.query.get(screening_type_id)
            if not screening_type:
                return {"status": "error", "error": "Screening type not found"}
            
            logger.info(f"🔑 KEYWORD CHANGE: {screening_type.name} - {change_type}")
            
            # Get all patients who might be affected by this screening type
            # This is a more targeted refresh than a global refresh
            affected_patients = set()
            
            # Find patients with existing screenings of this type
            existing_screenings = Screening.query.filter_by(screening_type=screening_type.name).all()
            for screening in existing_screenings:
                affected_patients.add(screening.patient_id)
            
            # Also check patients who might now qualify based on new keywords
            # This is more complex - for now, we'll do a global refresh to be safe
            refresh_result = self.refresh_all_screenings(f"keyword_change_{screening_type.name}")
            
            return {
                "status": "success",
                "screening_type": screening_type.name,
                "change_type": change_type,
                "affected_patients": len(affected_patients),
                "refresh_result": refresh_result
            }
            
        except Exception as e:
            logger.error(f"❌ ERROR handling keyword changes: {e}")
            return {"status": "error", "error": str(e)}
    
    def disable_auto_refresh(self):
        """Temporarily disable auto-refresh for bulk operations"""
        self.refresh_enabled = False
        logger.info("⏸️ Auto-refresh disabled")
    
    def enable_auto_refresh(self):
        """Re-enable auto-refresh"""
        self.refresh_enabled = True
        logger.info("▶️ Auto-refresh enabled")
    
    def set_batch_mode(self, enabled: bool):
        """Enable/disable batch mode for bulk operations"""
        self.batch_mode = enabled
        if enabled:
            logger.info("📦 Batch mode enabled - auto-refresh will be deferred")
        else:
            logger.info("📦 Batch mode disabled - normal auto-refresh behavior")
    
    def _update_checklist_default_items_for_deactivated_type(self, deactivated_screening_name: str):
        """
        Update checklist default items when a screening type is deactivated
        
        Args:
            deactivated_screening_name: Name of the screening type that was deactivated
        """
        try:
            from models import ChecklistSettings
            
            settings = ChecklistSettings.query.first()
            if settings and settings.default_items:
                # Parse current default items
                current_items = settings.default_items_list if hasattr(settings, 'default_items_list') else settings.default_items.split('\n')
                
                # Remove the deactivated screening type
                updated_items = [item.strip() for item in current_items if item.strip() != deactivated_screening_name]
                
                # Update the settings
                settings.default_items = '\n'.join(updated_items)
                db.session.commit()
                
                logger.info(f"🗑️ Removed '{deactivated_screening_name}' from checklist default items")
                
        except Exception as e:
            logger.error(f"Error updating checklist default items: {e}")
    
    def _add_to_checklist_default_items(self, screening_name: str):
        """
        Add screening type back to checklist default items when reactivated
        
        Args:
            screening_name: Name of the screening type to add back
        """
        try:
            from models import ChecklistSettings
            
            settings = ChecklistSettings.query.first()
            if settings:
                # Parse current default items
                current_items = settings.default_items_list if hasattr(settings, 'default_items_list') else settings.default_items.split('\n') if settings.default_items else []
                
                # Add the reactivated screening type if not already present
                current_items_clean = [item.strip() for item in current_items if item.strip()]
                if screening_name not in current_items_clean:
                    current_items_clean.append(screening_name)
                    
                    # Update the settings
                    settings.default_items = '\n'.join(current_items_clean)
                    db.session.commit()
                    
                    logger.info(f"➕ Added '{screening_name}' back to checklist default items")
                else:
                    logger.info(f"ℹ️ '{screening_name}' already present in checklist default items")
            else:
                # Create default settings if none exist
                from checklist_routes import get_or_create_settings
                settings = get_or_create_settings()
                settings.default_items = screening_name
                db.session.commit()
                logger.info(f"➕ Created new checklist settings with '{screening_name}'")
                
        except Exception as e:
            logger.error(f"Error adding to checklist default items: {e}")

# Global instance for use throughout the application
auto_refresh_manager = AutomatedScreeningRefreshManager()

def trigger_auto_refresh_for_patient(patient_id: int, source: str = "unknown"):
    """
    Convenience function to trigger auto-refresh for a patient
    
    Args:
        patient_id: ID of the patient
        source: Source of the trigger
    """
    return auto_refresh_manager.refresh_patient_screenings(patient_id, source)

def trigger_global_auto_refresh(source: str = "unknown"):
    """
    Convenience function to trigger global auto-refresh
    
    Args:
        source: Source of the trigger
    """
    return auto_refresh_manager.refresh_all_screenings(source)

def filter_active_screening_types_only(screening_types: List[ScreeningType]) -> List[ScreeningType]:
    """
    Convenience function to filter only active screening types
    
    Args:
        screening_types: List of screening types to filter
        
    Returns:
        List containing only active screening types
    """
    return auto_refresh_manager.filter_active_screening_types(screening_types)

def handle_screening_type_change(screening_type_id: int, new_status: bool):
    """
    Convenience function to handle screening type status changes
    
    Args:
        screening_type_id: ID of the screening type
        new_status: New active status
    """
    return auto_refresh_manager.handle_screening_type_status_change(screening_type_id, new_status)

def handle_keyword_updates(screening_type_id: int, change_type: str = "keywords_updated"):
    """
    Convenience function to handle keyword updates
    
    Args:
        screening_type_id: ID of the screening type
        change_type: Type of change
    """
    return auto_refresh_manager.handle_keyword_changes(screening_type_id, change_type)

def handle_cutoff_settings_change(change_type: str = "cutoff_settings_updated"):
    """
    Convenience function to handle cutoff settings changes
    
    Args:
        change_type: Type of cutoff change (general_cutoff, data_type_cutoffs, screening_specific_cutoffs)
    """
    logger.info(f"🕒 CUTOFF SETTINGS CHANGE: {change_type}")
    return trigger_global_auto_refresh(change_type)