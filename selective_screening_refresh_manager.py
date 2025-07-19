"""
Selective Screening Refresh Manager
Implements intelligent selective refresh logic to avoid unnecessary reprocessing
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

from app import db
from models import ScreeningType, Patient, Screening, MedicalDocument


class ChangeType(Enum):
    """Types of changes that can trigger selective refresh"""
    KEYWORDS = "keywords"
    TRIGGER_CONDITIONS = "trigger_conditions"
    CUTOFF_SETTINGS = "cutoff_settings"
    FREQUENCY = "frequency"
    ACTIVATION_STATUS = "activation_status"
    AGE_CRITERIA = "age_criteria"
    GENDER_CRITERIA = "gender_criteria"
    NAME_CHANGE = "name_change"


@dataclass
class ScreeningTypeChange:
    """Represents a change to a screening type"""
    screening_type_id: int
    screening_type_name: str
    change_type: ChangeType
    old_value: Any
    new_value: Any
    timestamp: datetime
    affected_patient_criteria: Dict[str, Any]


@dataclass
class RefreshStats:
    """Statistics for refresh operations"""
    total_patients_checked: int = 0
    affected_patients: int = 0
    screenings_updated: int = 0
    screenings_cached: int = 0
    processing_time: float = 0.0
    change_summary: List[str] = None

    def __post_init__(self):
        if self.change_summary is None:
            self.change_summary = []


class SelectiveScreeningRefreshManager:
    """Manages selective refresh of screenings based on specific changes"""
    
    def __init__(self):
        self.dirty_screening_types: Set[int] = set()
        self.change_log: List[ScreeningTypeChange] = []
        self.cache_timeout_hours = 24  # Cache validity period
        
    def mark_screening_type_dirty(
        self, 
        screening_type_id: int, 
        change_type: ChangeType, 
        old_value: Any, 
        new_value: Any,
        affected_criteria: Optional[Dict[str, Any]] = None
    ):
        """Mark a screening type as dirty due to changes"""
        screening_type = ScreeningType.query.get(screening_type_id)
        if not screening_type:
            return
            
        change = ScreeningTypeChange(
            screening_type_id=screening_type_id,
            screening_type_name=screening_type.name,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.utcnow(),
            affected_patient_criteria=affected_criteria or {}
        )
        
        self.change_log.append(change)
        self.dirty_screening_types.add(screening_type_id)
        
        print(f"🔄 Marked screening type {screening_type.name} as dirty: {change_type.value}")
        
    def get_affected_patients(self, change: ScreeningTypeChange) -> Set[int]:
        """Determine which patients are affected by a specific change"""
        affected_patients = set()
        
        try:
            screening_type = ScreeningType.query.get(change.screening_type_id)
            if not screening_type:
                return affected_patients
                
            # Base query for all patients
            patient_query = Patient.query
            
            # Apply age criteria if screening type has age restrictions
            if screening_type.min_age is not None:
                patient_query = patient_query.filter(Patient.age >= screening_type.min_age)
            if screening_type.max_age is not None:
                patient_query = patient_query.filter(Patient.age <= screening_type.max_age)
                
            # Apply gender criteria if screening type is gender-specific
            if screening_type.gender_specific:
                patient_query = patient_query.filter(Patient.sex == screening_type.gender_specific)
                
            # For different change types, apply specific filtering
            if change.change_type == ChangeType.KEYWORDS:
                # Patients with documents that might match new/old keywords
                affected_patients.update(self._get_patients_with_document_content(
                    change.old_value, change.new_value
                ))
                
            elif change.change_type == ChangeType.TRIGGER_CONDITIONS:
                # Patients with conditions that match new/old trigger conditions
                affected_patients.update(self._get_patients_with_conditions(
                    change.old_value, change.new_value
                ))
                
            elif change.change_type == ChangeType.ACTIVATION_STATUS:
                if change.new_value:  # Being activated
                    # All eligible patients need screening generation
                    affected_patients.update([p.id for p in patient_query.all()])
                else:  # Being deactivated
                    # Patients with existing screenings of this type
                    existing_screenings = Screening.query.filter_by(
                        screening_type=screening_type.name
                    ).all()
                    affected_patients.update([s.patient_id for s in existing_screenings])
                    
            elif change.change_type in [ChangeType.FREQUENCY, ChangeType.CUTOFF_SETTINGS]:
                # Patients with existing screenings of this type
                existing_screenings = Screening.query.filter_by(
                    screening_type=screening_type.name
                ).all()
                affected_patients.update([s.patient_id for s in existing_screenings])
                
            elif change.change_type in [ChangeType.AGE_CRITERIA, ChangeType.GENDER_CRITERIA]:
                # All patients need to be re-evaluated for eligibility
                affected_patients.update([p.id for p in Patient.query.all()])
                
            print(f"   📊 Found {len(affected_patients)} patients affected by {change.change_type.value} change")
            
        except Exception as e:
            print(f"❌ Error determining affected patients: {e}")
            # Fall back to all patients if error occurs
            affected_patients.update([p.id for p in Patient.query.all()])
            
        return affected_patients
        
    def _get_patients_with_document_content(self, old_keywords: List[str], new_keywords: List[str]) -> Set[int]:
        """Find patients with documents that might match keyword changes"""
        affected_patients = set()
        
        try:
            # Combine old and new keywords to catch all potentially affected documents
            all_keywords = set(old_keywords or []) | set(new_keywords or [])
            
            if all_keywords:
                # Query documents that contain any of these keywords
                for keyword in all_keywords:
                    if keyword and len(keyword.strip()) > 2:  # Avoid very short keywords
                        keyword_pattern = f'%{keyword.lower()}%'
                        documents = MedicalDocument.query.filter(
                            db.or_(
                                MedicalDocument.extracted_text.ilike(keyword_pattern),
                                MedicalDocument.document_name.ilike(keyword_pattern)
                            )
                        ).all()
                        
                        affected_patients.update([doc.patient_id for doc in documents if doc.patient_id])
                        
        except Exception as e:
            print(f"⚠️ Error finding patients with document content: {e}")
            
        return affected_patients
        
    def _get_patients_with_conditions(self, old_conditions: List[Dict], new_conditions: List[Dict]) -> Set[int]:
        """Find patients with medical conditions that match trigger condition changes"""
        affected_patients = set()
        
        try:
            # For now, return patients who have any conditions
            # This could be enhanced with actual condition code matching
            from models import Condition
            conditions = Condition.query.all()
            affected_patients.update([c.patient_id for c in conditions if c.patient_id])
            
        except Exception as e:
            print(f"⚠️ Error finding patients with conditions: {e}")
            
        return affected_patients
        
    def process_selective_refresh(self, force_all: bool = False) -> RefreshStats:
        """Process selective refresh for dirty screening types"""
        start_time = time.time()
        stats = RefreshStats()
        
        try:
            if force_all or not self.dirty_screening_types:
                # Process all screening types
                return self._process_full_refresh()
                
            print(f"🔄 Processing selective refresh for {len(self.dirty_screening_types)} dirty screening types...")
            
            # Group changes by screening type
            changes_by_type = {}
            for change in self.change_log:
                if change.screening_type_id in self.dirty_screening_types:
                    if change.screening_type_id not in changes_by_type:
                        changes_by_type[change.screening_type_id] = []
                    changes_by_type[change.screening_type_id].append(change)
                    
            # Process each dirty screening type
            all_affected_patients = set()
            
            for screening_type_id, changes in changes_by_type.items():
                affected_patients = set()
                
                # Get all patients affected by any change to this screening type
                for change in changes:
                    affected_patients.update(self.get_affected_patients(change))
                    stats.change_summary.append(
                        f"{change.change_type.value} change to {change.screening_type_name}"
                    )
                    
                all_affected_patients.update(affected_patients)
                print(f"   📋 Screening type {screening_type_id}: {len(affected_patients)} affected patients")
                
            # Process affected patients
            stats.affected_patients = len(all_affected_patients)
            stats.total_patients_checked = len(all_affected_patients)
            
            if all_affected_patients:
                stats.screenings_updated = self._refresh_patients_screenings(
                    list(all_affected_patients), 
                    list(self.dirty_screening_types)
                )
                
            # Clear dirty flags after successful processing
            self.dirty_screening_types.clear()
            
            # Keep only recent changes in log (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            self.change_log = [c for c in self.change_log if c.timestamp > cutoff_time]
            
        except Exception as e:
            print(f"❌ Error in selective refresh: {e}")
            # Fall back to minimal processing
            stats.affected_patients = 0
            stats.screenings_updated = 0
            
        stats.processing_time = time.time() - start_time
        print(f"✅ Selective refresh completed in {stats.processing_time:.2f}s")
        return stats
        
    def _process_full_refresh(self) -> RefreshStats:
        """Fall back to full refresh when needed"""
        print("🔄 Performing full refresh...")
        start_time = time.time()
        stats = RefreshStats()
        
        try:
            from automated_screening_engine import ScreeningStatusEngine
            engine = ScreeningStatusEngine()
            
            all_patients = Patient.query.all()
            stats.total_patients_checked = len(all_patients)
            stats.affected_patients = len(all_patients)
            
            for patient in all_patients:
                try:
                    screenings = engine.generate_patient_screenings(patient.id)
                    stats.screenings_updated += len(screenings)
                except Exception as e:
                    print(f"⚠️ Error processing patient {patient.id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error in full refresh: {e}")
            
        stats.processing_time = time.time() - start_time
        return stats
        
    def _refresh_patients_screenings(self, patient_ids: List[int], screening_type_ids: List[int]) -> int:
        """Refresh screenings for specific patients and screening types"""
        updated_count = 0
        
        try:
            from automated_screening_engine import ScreeningStatusEngine
            engine = ScreeningStatusEngine()
            
            # Process in batches to avoid memory issues
            batch_size = 50
            for i in range(0, len(patient_ids), batch_size):
                batch = patient_ids[i:i + batch_size]
                
                for patient_id in batch:
                    try:
                        # Generate screenings for this patient
                        screenings = engine.generate_patient_screenings(patient_id)
                        
                        # Filter to only the screening types that changed
                        relevant_screenings = [
                            s for s in screenings 
                            if any(st_id for st_id in screening_type_ids 
                                  if ScreeningType.query.get(st_id) and 
                                  ScreeningType.query.get(st_id).name == s['screening_type'])
                        ]
                        
                        updated_count += len(relevant_screenings)
                        
                    except Exception as e:
                        print(f"⚠️ Error refreshing patient {patient_id}: {e}")
                        continue
                        
                # Commit batch
                try:
                    db.session.commit()
                except Exception as e:
                    print(f"⚠️ Error committing batch: {e}")
                    db.session.rollback()
                    
        except Exception as e:
            print(f"❌ Error refreshing patient screenings: {e}")
            
        return updated_count
        
    def get_refresh_status(self) -> Dict[str, Any]:
        """Get current refresh status and statistics"""
        return {
            "dirty_screening_types": len(self.dirty_screening_types),
            "recent_changes": len([c for c in self.change_log 
                                 if c.timestamp > datetime.utcnow() - timedelta(hours=1)]),
            "total_changes_logged": len(self.change_log),
            "last_change_time": max([c.timestamp for c in self.change_log]) if self.change_log else None,
            "cache_timeout_hours": self.cache_timeout_hours
        }
        
    def clear_all_dirty_flags(self):
        """Clear all dirty flags (use with caution)"""
        self.dirty_screening_types.clear()
        print("🧹 Cleared all dirty screening type flags")


# Global instance
selective_refresh_manager = SelectiveScreeningRefreshManager()