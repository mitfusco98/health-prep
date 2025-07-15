#!/usr/bin/env python3
"""
Automated Screening Generation Engine
Generates screening statuses based on document parsing rules and patient medical history
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import json
from app import app, db
from models import Patient, ScreeningType, Screening, MedicalDocument

class ScreeningStatusEngine:
    """Engine for automatic screening status determination"""

    STATUS_DUE = "Due"
    STATUS_DUE_SOON = "Due Soon"
    STATUS_INCOMPLETE = "Incomplete"
    STATUS_COMPLETE = "Complete"

    DUE_SOON_THRESHOLD_DAYS = 30  # Within 30 days of due date

    def __init__(self):
        self.app = app

    def generate_patient_screenings(self, patient_id: int) -> List[Dict]:
        """
        Generate automated screenings for a specific patient

        Args:
            patient_id: Patient ID to generate screenings for

        Returns:
            List of screening dictionaries with status determinations
        """
        with self.app.app_context():
            patient = Patient.query.get(patient_id)
            if not patient:
                return []

            # Get applicable screening types for this patient
            applicable_screenings = self._get_applicable_screening_types(patient)

            # Generate status for each applicable screening
            screenings = []
            for screening_type in applicable_screenings:
                screening_data = self._determine_screening_status(patient, screening_type)
                if screening_data:
                    screenings.append(screening_data)

            return screenings

    def generate_all_patient_screenings(self) -> Dict[int, List[Dict]]:
        """
        Generate automated screenings for all patients

        Returns:
            Dictionary mapping patient_id to list of screening data
        """
        with self.app.app_context():
            all_patients = Patient.query.all()
            results = {}

            for patient in all_patients:
                results[patient.id] = self.generate_patient_screenings(patient.id)

            return results

    def _get_applicable_screening_types(self, patient: Patient) -> List[ScreeningType]:
        """
        Get screening types applicable to this patient based on age, gender, and conditions
        CRITICAL: Only returns ACTIVE screening types to prevent processing inactive types

        Args:
            patient: Patient object

        Returns:
            List of applicable ScreeningType objects
        """
        applicable_types = []

        # Get all active screening types
        all_screening_types = ScreeningType.query.filter_by(is_active=True).all()

        for screening_type in all_screening_types:
            if self._patient_qualifies_for_screening(patient, screening_type):
                applicable_types.append(screening_type)

        return applicable_types

    def _patient_qualifies_for_screening(self, patient: Patient, screening_type: ScreeningType) -> bool:
        """
        Check if patient qualifies for this screening type

        Args:
            patient: Patient object
            screening_type: ScreeningType object

        Returns:
            True if patient qualifies for this screening
        """
        # Check age requirements
        if screening_type.min_age and patient.age < screening_type.min_age:
            return False
        if screening_type.max_age and patient.age > screening_type.max_age:
            return False

        # Check gender requirements
        if screening_type.gender_specific:
            if screening_type.gender_specific.lower() != patient.sex.lower():
                return False

        return True

    def _determine_screening_status(self, patient: Patient, screening_type: ScreeningType) -> Optional[Dict]:
        """
        Determine the status of a screening for a patient

        Args:
            patient: Patient object
            screening_type: ScreeningType object

        Returns:
            Dictionary with screening data and status, or None if not applicable
        """
        # Find documents that match this screening's parsing rules
        matching_documents = self._find_matching_documents(patient, screening_type)

        # Get existing screening record if any (for last_completed date)
        existing_screening = Screening.query.filter_by(
            patient_id=patient.id,
            screening_type=screening_type.name
        ).first()

        # Determine status based on documents and frequency
        status = self._calculate_status(
            screening_type=screening_type,
            matching_documents=matching_documents,
            existing_screening=existing_screening,
            patient=patient
        )

        # Calculate due date based on frequency and last completed
        due_date = self._calculate_due_date(screening_type, existing_screening)

        # Update last_completed based on most recent matching document's ACTUAL medical event date
        # CRITICAL RULE: Only set last_completed if there are matching documents
        last_completed = None
        if matching_documents:
            # Use document_date (actual medical event date) instead of created_at (system upload date)
            docs_with_dates = []
            for doc in matching_documents:
                if doc.document_date:
                    docs_with_dates.append((doc, doc.document_date))
                elif doc.created_at:
                    # Fallback to created_at if document_date is not available
                    docs_with_dates.append((doc, doc.created_at))

            if docs_with_dates:
                most_recent_doc, most_recent_date = max(docs_with_dates, key=lambda x: x[1])
                doc_date = most_recent_date.date() if hasattr(most_recent_date, 'date') else most_recent_date
                last_completed = doc_date
        # If no matching documents, last_completed remains None

        return {
            'patient_id': patient.id,
            'screening_type': screening_type.name,
            'screening_type_id': screening_type.id,
            'status': status,
            'due_date': due_date,
            'last_completed': last_completed,
            'frequency': self._format_frequency(screening_type),
            'matching_documents': len(matching_documents),
            'matched_documents': matching_documents,  # Pass the actual document objects
            'notes': self._generate_status_notes(status, matching_documents, due_date)
        }

    def _find_matching_documents(self, patient: Patient, screening_type: ScreeningType) -> List[MedicalDocument]:
        """
        Find patient documents that match the screening type's parsing rules

        Args:
            patient: Patient object
            screening_type: ScreeningType object

        Returns:
            List of matching MedicalDocument objects
        """
        matching_documents = []

        # Get all patient documents
        patient_documents = MedicalDocument.query.filter_by(patient_id=patient.id).all()

        for document in patient_documents:
            if self._document_matches_screening(document, screening_type):
                matching_documents.append(document)

        return matching_documents

    def _document_matches_screening(self, document: MedicalDocument, screening_type: ScreeningType) -> bool:
        """
        Check if a document matches the screening type's parsing rules using enhanced keyword matching

        Args:
            document: MedicalDocument object
            screening_type: ScreeningType object

        Returns:
            True if document matches screening criteria
        """
        # CRITICAL: If screening type has no keywords configured, no documents can match
        has_content_keywords = bool(screening_type.get_content_keywords())
        has_document_keywords = bool(screening_type.get_document_keywords())
        has_filename_keywords = bool(screening_type.filename_keywords)

        if not has_content_keywords and not has_document_keywords and not has_filename_keywords:
            # No keywords configured - no documents can match
            return False

        # Import enhanced matcher
        try:
            from enhanced_keyword_matcher import EnhancedKeywordMatcher
            matcher = EnhancedKeywordMatcher()
        except ImportError:
            # Fallback to simple matching if enhanced matcher not available
            return self._simple_document_matching(document, screening_type)

        # Check content keywords with enhanced matching
        content_match = False
        if has_content_keywords and document.content:
            try:
                content_keywords = json.loads(screening_type.content_keywords)
                if content_keywords:  # Only match if keywords exist
                    result = matcher.match_keywords_in_content(document.content, content_keywords)
                    content_match = result['is_match']
            except (json.JSONDecodeError, TypeError):
                pass

        # Check document type keywords (keep simple matching for this)
        doc_type_match = False
        if has_document_keywords and document.document_type:
            try:
                doc_keywords = json.loads(screening_type.document_keywords)
                if doc_keywords:  # Only match if keywords exist
                    doc_type_match = any(keyword.lower() in document.document_type.lower() 
                                       for keyword in doc_keywords)
            except (json.JSONDecodeError, TypeError):
                pass

        # Check filename keywords with enhanced matching
        filename_match = False
        if has_filename_keywords and document.filename:
            try:
                filename_keywords = json.loads(screening_type.filename_keywords)
                if filename_keywords:  # Only match if keywords exist
                    result = matcher.match_keywords_in_content(document.filename, filename_keywords)
                    filename_match = result['is_match']
            except (json.JSONDecodeError, TypeError):
                pass

        # Document matches if content matches AND (document type matches OR no doc type filter)
        # This ensures content relevance while allowing doc type filtering
        if has_document_keywords:
            # If doc type filter exists, require both content match AND doc type match
            return (content_match or filename_match) and doc_type_match
        else:
            # If no doc type filter, content or filename match is sufficient
            return content_match or filename_match

    def _simple_document_matching(self, document: MedicalDocument, screening_type: ScreeningType) -> bool:
        """
        Fallback simple matching method
        """
        # CRITICAL: If screening type has no keywords configured, no documents can match
        has_content_keywords = bool(screening_type.get_content_keywords())
        has_document_keywords = bool(screening_type.get_document_keywords())
        has_filename_keywords = bool(screening_type.filename_keywords)

        if not has_content_keywords and not has_document_keywords and not has_filename_keywords:
            # No keywords configured - no documents can match
            return False

        # Check content keywords
        if has_content_keywords:
            try:
                content_keywords = json.loads(screening_type.content_keywords)
                if content_keywords and document.content and any(keyword.lower() in document.content.lower() 
                                         for keyword in content_keywords):
                    return True
            except (json.JSONDecodeError, TypeError):
                pass

        # Check document type keywords
        if has_document_keywords:
            try:
                doc_keywords = json.loads(screening_type.document_keywords)
                if doc_keywords and document.document_type and any(keyword.lower() in document.document_type.lower() 
                                               for keyword in doc_keywords):
                    return True
            except (json.JSONDecodeError, TypeError):
                pass

        # Check filename keywords
        if has_filename_keywords:
            try:
                filename_keywords = json.loads(screening_type.filename_keywords)
                if filename_keywords and document.filename and any(keyword.lower() in document.filename.lower() 
                                          for keyword in filename_keywords):
                    return True
            except (json.JSONDecodeError, TypeError):
                pass

        return False

    def _calculate_status(self, screening_type: ScreeningType, matching_documents: List[MedicalDocument], 
                         existing_screening: Optional[Screening], patient: Patient) -> str:
        """
        Calculate the screening status based on documents and timing

        USER-DEFINED STATUS RULES:
        - 'incomplete' = no document matching but up to date on screening frequency 
        - 'due' = no document matches and overdue on screening frequency
        - 'due soon' = no document matching within 30 days of next deadline
        - 'Complete' = has matching documents

        Args:
            screening_type: ScreeningType object
            matching_documents: List of matching documents
            existing_screening: Existing Screening record if any
            patient: Patient object

        Returns:
            Status string: 'Due', 'Due Soon', 'Incomplete', or 'Complete'
        """
        # USER-DEFINED STATUS LOGIC:
        # 'incomplete' = no document matching but up to date on screening frequency 
        # 'due' = no document matches and overdue on screening frequency
        # 'due soon' = no document matching within 30 days of next deadline
        # 'Complete' = has matching documents

        # Step 1: If we have matching documents, it's Complete
        if matching_documents:
            return self.STATUS_COMPLETE

        # Step 2: No documents - determine timing-based status
        # Get the last completion date to calculate when next screening is due
        last_completed_date = None
        
        if existing_screening and existing_screening.last_completed:
            last_completed_date = existing_screening.last_completed
        else:
            # No previous completion - use today's date for calculations
            # This handles first-time screenings
            last_completed_date = date.today()

        # Calculate when next screening is due
        next_due_date = self._calculate_next_due_date(screening_type, last_completed_date)
        
        # If no frequency is defined, default to Due (requires manual review)
        if not next_due_date:
            return self.STATUS_DUE

        today = date.today()

        # Step 3: Apply timing logic for no-document cases
        if today > next_due_date:
            # Past due date = Due
            return self.STATUS_DUE
        elif today > (next_due_date - timedelta(days=self.DUE_SOON_THRESHOLD_DAYS)):
            # Within 30 days of due date = Due Soon
            return self.STATUS_DUE_SOON
        else:
            # Up to date on frequency but no documents = Incomplete
            return self.STATUS_INCOMPLETE

    def _calculate_due_date(self, screening_type: ScreeningType, existing_screening: Optional[Screening]) -> Optional[date]:
        """Calculate when screening is due"""
        if existing_screening and existing_screening.last_completed:
            return self._calculate_next_due_date(screening_type, existing_screening.last_completed)
        return None

    def _calculate_next_due_date(self, screening_type: ScreeningType, last_completed: date) -> Optional[date]:
        """
        Calculate next due date based on frequency

        Args:
            screening_type: ScreeningType object
            last_completed: Date of last completion

        Returns:
            Next due date or None if frequency not specified
        """
        if not screening_type.frequency_number or not screening_type.frequency_unit:
            return None

        if screening_type.frequency_unit == 'days':
            return last_completed + timedelta(days=screening_type.frequency_number)
        elif screening_type.frequency_unit == 'weeks':
            return last_completed + timedelta(weeks=screening_type.frequency_number)
        elif screening_type.frequency_unit == 'months':
            # Approximate months as 30 days
            return last_completed + timedelta(days=screening_type.frequency_number * 30)
        elif screening_type.frequency_unit == 'years':
            return last_completed + timedelta(days=screening_type.frequency_number * 365)

        return None

    def _format_frequency(self, screening_type: ScreeningType) -> str:
        """Format frequency for display"""
        if screening_type.frequency_number and screening_type.frequency_unit:
            if screening_type.frequency_number == 1:
                return f"Every {screening_type.frequency_unit[:-1]}"  # Remove 's' from plural
            else:
                return f"Every {screening_type.frequency_number} {screening_type.frequency_unit}"
        return screening_type.default_frequency or "As needed"

    def _generate_status_notes(self, status: str, matching_documents: List[MedicalDocument], due_date: Optional[date]) -> str:
        """Generate informative notes about the status"""
        notes = []

        # Add status-specific notes
        if status == self.STATUS_COMPLETE:
            notes.append(f"✓ Found {len(matching_documents)} matching document(s)")
        elif status == self.STATUS_DUE:
            if due_date:
                notes.append(f"⚠️ Due since {due_date.strftime('%Y-%m-%d')}")
            else:
                notes.append("⚠️ Due now")
        elif status == self.STATUS_DUE_SOON:
            if due_date:
                notes.append(f"📅 Due {due_date.strftime('%Y-%m-%d')}")
            notes.append(f"Found {len(matching_documents)} matching document(s)")
        elif status == self.STATUS_INCOMPLETE:
            notes.append("❌ No matching documents found")

        return " | ".join(notes)

    def _is_screening_due(self, screening_type: ScreeningType, patient: Patient) -> bool:
        """Check if a screening is currently due"""
        # Check if this screening type is used in any patient screenings
        patient_screenings = Screening.query.filter_by(
            screening_type=screening_type.name
        ).count()

        if patient_screenings > 0:
            return True
        else:
            return False

def test_screening_engine():
    """Test the screening engine with sample data"""
    engine = ScreeningStatusEngine()

    with app.app_context():
        # Test with first patient
        patients = Patient.query.limit(3).all()

        for patient in patients:
            print(f"\n=== Patient: {patient.full_name} (Age: {patient.age}) ===")
            screenings = engine.generate_patient_screenings(patient.id)

            if screenings:
                for screening in screenings:
                    print(f"  {screening['screening_type']}: {screening['status']}")
                    print(f"    Due: {screening['due_date'] or 'Not set'}")
                    print(f"    Notes: {screening['notes']}")
            else:
                print("  No applicable screenings")

if __name__ == "__main__":
    test_screening_engine()