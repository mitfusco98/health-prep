"""
Patient FHIR Mapper

This module provides functionality to convert internal Patient objects
to FHIR Patient resources and vice versa.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_mapper import BaseFHIRMapper
from .constants import FHIR_CONSTANTS


class PatientMapper(BaseFHIRMapper):
    """Mapper for converting Patient objects to/from FHIR Patient resources"""
    
    def __init__(self):
        super().__init__()
    
    def to_fhir(self, patient) -> Dict[str, Any]:
        """
        Convert internal Patient object to FHIR Patient resource
        
        Args:
            patient: Internal Patient model object with fields:
                    - id, first_name, last_name, dob, sex, mrn
                    - phone, email, address, insurance (optional)
                    - created_at, updated_at (optional)
                    
        Returns:
            Dict containing FHIR Patient resource
        """
        # Validate required fields
        if not all([patient.first_name, patient.last_name, patient.date_of_birth, 
                   patient.sex, patient.mrn]):
            raise ValueError("Patient missing required fields for FHIR conversion")
        
        # Create base FHIR Patient resource
        fhir_patient = self.create_base_resource(
            resource_type=self.constants.RESOURCE_TYPES['PATIENT'],
            resource_id=str(patient.id) if patient.id else None
        )
        
        # Set patient as active by default
        fhir_patient["active"] = True
        
        # Add identifiers
        fhir_patient["identifier"] = self._create_patient_identifiers(patient)
        
        # Add name
        fhir_patient["name"] = self._create_patient_names(patient)
        
        # Add contact information
        telecom = self._create_patient_telecom(patient)
        if telecom:
            fhir_patient["telecom"] = telecom
        
        # Add gender
        fhir_patient["gender"] = self._map_gender(patient.sex)
        
        # Add birth date
        fhir_patient["birthDate"] = self.format_date(patient.date_of_birth)
        
        # Add address if available
        address = self._create_patient_address(patient)
        if address:
            fhir_patient["address"] = [address]
        
        # Add extensions for additional data
        extensions = self._create_patient_extensions(patient)
        if extensions:
            fhir_patient["extension"] = extensions
        
        # Add meta information
        if hasattr(patient, 'updated_at') and patient.updated_at:
            fhir_patient["meta"]["lastUpdated"] = self.format_datetime(patient.updated_at)
        
        # Clean up empty fields
        return self.clean_empty_fields(fhir_patient)
    
    def _create_patient_identifiers(self, patient) -> List[Dict[str, Any]]:
        """Create FHIR identifiers for the patient"""
        identifiers = []
        
        # Medical Record Number (MRN) - primary identifier
        mrn_identifier = self.create_identifier(
            value=patient.mrn,
            type_code=self.constants.IDENTIFIER_TYPES['MRN']['code'],
            type_display=self.constants.IDENTIFIER_TYPES['MRN']['display']
        )
        mrn_identifier["use"] = "official"
        identifiers.append(mrn_identifier)
        
        # Internal ID as secondary identifier
        if patient.id:
            internal_id = self.create_identifier(
                value=str(patient.id),
                system="http://your-organization.com/patient-id",
                type_code="PN",
                type_display="Person number"
            )
            internal_id["use"] = "secondary"
            identifiers.append(internal_id)
        
        return identifiers
    
    def _create_patient_names(self, patient) -> List[Dict[str, Any]]:
        """Create FHIR HumanName objects for the patient"""
        names = []
        
        # Official name
        official_name = self.create_human_name(
            given_names=[patient.first_name],
            family_name=patient.last_name,
            use="official"
        )
        names.append(official_name)
        
        return names
    
    def _create_patient_telecom(self, patient) -> List[Dict[str, Any]]:
        """Create FHIR ContactPoint objects for patient contact information"""
        telecom = []
        
        # Phone number
        if hasattr(patient, 'phone') and patient.phone:
            phone_contact = self.create_contact_point(
                value=patient.phone,
                system=self.constants.CONTACT_POINT_SYSTEMS['PHONE'],
                use=self.constants.CONTACT_POINT_USES['HOME']
            )
            telecom.append(phone_contact)
        
        # Email address
        if hasattr(patient, 'email') and patient.email:
            email_contact = self.create_contact_point(
                value=patient.email,
                system=self.constants.CONTACT_POINT_SYSTEMS['EMAIL'],
                use=self.constants.CONTACT_POINT_USES['HOME']
            )
            telecom.append(email_contact)
        
        return telecom
    
    def _map_gender(self, internal_gender: str) -> str:
        """Map internal gender value to FHIR administrative-gender"""
        return self.constants.GENDER_MAPPING.get(internal_gender, 'unknown')
    
    def _create_patient_address(self, patient) -> Optional[Dict[str, Any]]:
        """Create FHIR Address object for the patient"""
        if not hasattr(patient, 'address') or not patient.address:
            return None
        
        # Parse address string into components
        # This is a simple implementation - you may want to enhance this
        # based on your address format
        address_parts = patient.address.split(',') if patient.address else []
        
        address = self.create_address(
            line=address_parts[0].strip() if address_parts else patient.address,
            city=address_parts[1].strip() if len(address_parts) > 1 else None,
            state=address_parts[2].strip() if len(address_parts) > 2 else None,
            postal_code=address_parts[3].strip() if len(address_parts) > 3 else None,
            use=self.constants.ADDRESS_USES['HOME']
        )
        
        return address
    
    def _create_patient_extensions(self, patient) -> List[Dict[str, Any]]:
        """Create FHIR extensions for additional patient data"""
        extensions = []
        
        # Insurance information as extension
        if hasattr(patient, 'insurance') and patient.insurance:
            insurance_extension = {
                "url": "http://your-organization.com/fhir/StructureDefinition/insurance-info",
                "valueString": patient.insurance
            }
            extensions.append(insurance_extension)
        
        # Creation timestamp as extension
        if hasattr(patient, 'created_at') and patient.created_at:
            created_extension = {
                "url": "http://your-organization.com/fhir/StructureDefinition/created-at",
                "valueDateTime": self.format_datetime(patient.created_at)
            }
            extensions.append(created_extension)
        
        return extensions
    
    def from_fhir(self, fhir_patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FHIR Patient resource to internal patient data format
        
        Args:
            fhir_patient: FHIR Patient resource dictionary
            
        Returns:
            Dict containing internal patient data fields
        """
        patient_data = {}
        
        # Extract MRN from identifiers
        identifiers = fhir_patient.get("identifier", [])
        mrn_identifier = next(
            (id for id in identifiers 
             if id.get("type", {}).get("coding", [{}])[0].get("code") == "MR"),
            None
        )
        if mrn_identifier:
            patient_data["mrn"] = mrn_identifier.get("value")
        
        # Extract name
        names = fhir_patient.get("name", [])
        if names:
            name = names[0]  # Use first name entry
            patient_data["first_name"] = name.get("given", [""])[0] if name.get("given") else ""
            patient_data["last_name"] = name.get("family", "")
        
        # Extract birth date
        birth_date = fhir_patient.get("birthDate")
        if birth_date:
            try:
                patient_data["date_of_birth"] = datetime.strptime(birth_date, "%Y-%m-%d").date()
            except ValueError:
                pass  # Invalid date format
        
        # Extract gender
        fhir_gender = fhir_patient.get("gender", "unknown")
        gender_reverse_map = {v: k for k, v in self.constants.GENDER_MAPPING.items()}
        patient_data["sex"] = gender_reverse_map.get(fhir_gender, "Other")
        
        # Extract contact information
        telecom = fhir_patient.get("telecom", [])
        for contact in telecom:
            if contact.get("system") == "phone":
                patient_data["phone"] = contact.get("value", "")
            elif contact.get("system") == "email":
                patient_data["email"] = contact.get("value", "")
        
        # Extract address
        addresses = fhir_patient.get("address", [])
        if addresses:
            address = addresses[0]  # Use first address
            address_parts = []
            if address.get("line"):
                address_parts.extend(address["line"])
            if address.get("city"):
                address_parts.append(address["city"])
            if address.get("state"):
                address_parts.append(address["state"])
            if address.get("postalCode"):
                address_parts.append(address["postalCode"])
            
            patient_data["address"] = ", ".join(address_parts) if address_parts else ""
        
        # Extract extensions
        extensions = fhir_patient.get("extension", [])
        for ext in extensions:
            if ext.get("url") == "http://your-organization.com/fhir/StructureDefinition/insurance-info":
                patient_data["insurance"] = ext.get("valueString", "")
        
        return patient_data
    
    def validate_fhir_patient(self, fhir_patient: Dict[str, Any]) -> bool:
        """
        Validate that a FHIR Patient resource has required fields
        
        Args:
            fhir_patient: FHIR Patient resource dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["resourceType", "identifier", "name", "gender", "birthDate"]
        
        if not self.validate_required_fields(fhir_patient, required_fields):
            return False
        
        # Check resource type
        if fhir_patient.get("resourceType") != "Patient":
            return False
        
        # Check that at least one identifier exists
        if not fhir_patient.get("identifier"):
            return False
        
        # Check that at least one name exists
        if not fhir_patient.get("name"):
            return False
        
        return True