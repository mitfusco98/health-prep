"""
Encounter FHIR Mapper

This module provides functionality to convert internal Appointment objects
to FHIR Encounter resources and vice versa.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .base_mapper import BaseFHIRMapper
from .constants import FHIR_CONSTANTS


class EncounterMapper(BaseFHIRMapper):
    """Mapper for converting Appointment objects to/from FHIR Encounter resources"""
    
    def __init__(self):
        super().__init__()
    
    def to_fhir(self, appointment) -> Dict[str, Any]:
        """
        Convert internal Appointment object to FHIR Encounter resource
        
        Args:
            appointment: Internal Appointment model object with fields:
                        - id, patient_id, appointment_date, appointment_time
                        - note, status, created_at, updated_at
                        - patient (relationship)
                        
        Returns:
            Dict containing FHIR Encounter resource
        """
        # Validate required fields
        if not all([appointment.patient_id, appointment.appointment_date, 
                   appointment.appointment_time]):
            raise ValueError("Appointment missing required fields for FHIR conversion")
        
        # Create base FHIR Encounter resource
        fhir_encounter = self.create_base_resource(
            resource_type=self.constants.RESOURCE_TYPES['ENCOUNTER'],
            resource_id=str(appointment.id) if appointment.id else None
        )
        
        # Set encounter status
        fhir_encounter["status"] = self._map_appointment_status(appointment.status)
        
        # Set encounter class (ambulatory by default)
        fhir_encounter["class"] = self.constants.ENCOUNTER_CLASS['AMBULATORY']
        
        # Set encounter type
        fhir_encounter["type"] = [self._determine_encounter_type(appointment)]
        
        # Set subject (patient reference)
        fhir_encounter["subject"] = {
            "reference": f"Patient/{appointment.patient_id}",
            "display": getattr(appointment.patient, 'full_name', f"Patient {appointment.patient_id}") if hasattr(appointment, 'patient') else f"Patient {appointment.patient_id}"
        }
        
        # Set period
        fhir_encounter["period"] = self._create_encounter_period(appointment)
        
        # Add reason/note if available
        if appointment.note:
            fhir_encounter["reasonCode"] = [{
                "text": appointment.note
            }]
        
        # Add identifier for appointment reference
        fhir_encounter["identifier"] = [{
            "use": "official",
            "system": "http://your-organization.com/appointment-id",
            "value": str(appointment.id)
        }]
        
        # Add extensions for additional data
        extensions = self._create_encounter_extensions(appointment)
        if extensions:
            fhir_encounter["extension"] = extensions
        
        # Update meta information
        if hasattr(appointment, 'updated_at') and appointment.updated_at:
            fhir_encounter["meta"]["lastUpdated"] = self.format_datetime(appointment.updated_at)
        
        # Clean up empty fields
        return self.clean_empty_fields(fhir_encounter)
    
    def _map_appointment_status(self, internal_status: str) -> str:
        """Map internal appointment status to FHIR encounter status"""
        return self.constants.ENCOUNTER_STATUS_MAPPING.get(internal_status, 'planned')
    
    def _determine_encounter_type(self, appointment) -> Dict[str, Any]:
        """Determine the encounter type based on appointment data"""
        # Default to consultation type
        # You can enhance this logic based on your appointment categorization
        encounter_type = self.constants.ENCOUNTER_TYPE['CONSULTATION']
        
        # Check note for keywords to determine type
        if appointment.note:
            note_lower = appointment.note.lower()
            if any(word in note_lower for word in ['checkup', 'check-up', 'annual', 'physical']):
                encounter_type = self.constants.ENCOUNTER_TYPE['CHECKUP']
            elif any(word in note_lower for word in ['follow-up', 'followup', 'follow up']):
                encounter_type = self.constants.ENCOUNTER_TYPE['FOLLOWUP']
        
        return {
            "coding": [encounter_type],
            "text": encounter_type['display']
        }
    
    def _create_encounter_period(self, appointment) -> Dict[str, Any]:
        """Create FHIR Period for the encounter"""
        # Combine date and time for start
        start_datetime = appointment.date_time if hasattr(appointment, 'date_time') else \
                        datetime.combine(appointment.appointment_date, appointment.appointment_time)
        
        # Estimate end time (default 15 minutes for appointments)
        end_datetime = start_datetime + timedelta(minutes=15)
        
        period = {
            "start": self.format_datetime(start_datetime)
        }
        
        # Only add end time if appointment is finished
        if appointment.status == 'seen':
            period["end"] = self.format_datetime(end_datetime)
        
        return period
    
    def _create_encounter_extensions(self, appointment) -> List[Dict[str, Any]]:
        """Create FHIR extensions for additional appointment data"""
        extensions = []
        
        # Original appointment date as extension
        if hasattr(appointment, 'created_at') and appointment.created_at:
            scheduled_extension = {
                "url": "http://your-organization.com/fhir/StructureDefinition/appointment-scheduled",
                "valueDateTime": self.format_datetime(appointment.created_at)
            }
            extensions.append(scheduled_extension)
        
        # Appointment time as separate extension for easier querying
        appointment_time_extension = {
            "url": "http://your-organization.com/fhir/StructureDefinition/appointment-time",
            "valueTime": appointment.appointment_time.strftime('%H:%M:%S')
        }
        extensions.append(appointment_time_extension)
        
        return extensions
    
    def from_fhir(self, fhir_encounter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FHIR Encounter resource to internal appointment data format
        
        Args:
            fhir_encounter: FHIR Encounter resource dictionary
            
        Returns:
            Dict containing internal appointment data fields
        """
        appointment_data = {}
        
        # Extract patient ID from subject reference
        subject = fhir_encounter.get("subject", {})
        reference = subject.get("reference", "")
        if reference.startswith("Patient/"):
            appointment_data["patient_id"] = int(reference.split("/")[1])
        
        # Extract date and time from period
        period = fhir_encounter.get("period", {})
        start_datetime_str = period.get("start")
        if start_datetime_str:
            try:
                start_datetime = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
                appointment_data["appointment_date"] = start_datetime.date()
                appointment_data["appointment_time"] = start_datetime.time()
            except ValueError:
                pass  # Invalid datetime format
        
        # Map status back to internal format
        fhir_status = fhir_encounter.get("status", "planned")
        status_reverse_map = {v: k for k, v in self.constants.ENCOUNTER_STATUS_MAPPING.items()}
        appointment_data["status"] = status_reverse_map.get(fhir_status, "OOO")
        
        # Extract note from reasonCode
        reason_codes = fhir_encounter.get("reasonCode", [])
        if reason_codes and reason_codes[0].get("text"):
            appointment_data["note"] = reason_codes[0]["text"]
        
        return appointment_data
    
    def validate_fhir_encounter(self, fhir_encounter: Dict[str, Any]) -> bool:
        """
        Validate that a FHIR Encounter resource has required fields
        
        Args:
            fhir_encounter: FHIR Encounter resource dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["resourceType", "status", "class", "subject"]
        
        if not self.validate_required_fields(fhir_encounter, required_fields):
            return False
        
        # Check resource type
        if fhir_encounter.get("resourceType") != "Encounter":
            return False
        
        # Check that subject reference exists
        subject = fhir_encounter.get("subject", {})
        if not subject.get("reference"):
            return False
        
        return True
    
    def create_encounter_bundle(self, appointments: List) -> Dict[str, Any]:
        """
        Create FHIR Bundle from multiple appointments
        
        Args:
            appointments: List of Appointment model instances
            
        Returns:
            Dict containing FHIR Bundle resource
        """
        bundle = {
            "resourceType": "Bundle",
            "id": "encounter-bundle",
            "type": "collection",
            "timestamp": self.format_datetime(datetime.utcnow()),
            "total": len(appointments),
            "entry": []
        }
        
        for appointment in appointments:
            try:
                fhir_encounter = self.to_fhir(appointment)
                bundle["entry"].append({
                    "fullUrl": f"Encounter/{appointment.id}",
                    "resource": fhir_encounter
                })
            except ValueError:
                # Skip appointments with incomplete data
                bundle["total"] -= 1
                continue
        
        return bundle