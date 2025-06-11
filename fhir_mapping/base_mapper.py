"""
Base FHIR Mapper

This module provides the base class and common utilities for all FHIR mappers.
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, List
from .constants import FHIR_CONSTANTS


class BaseFHIRMapper:
    """Base class for all FHIR resource mappers"""
    
    def __init__(self):
        self.constants = FHIR_CONSTANTS
    
    def create_base_resource(self, resource_type: str, resource_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a base FHIR resource structure
        
        Args:
            resource_type: The FHIR resource type (e.g., 'Patient', 'Observation')
            resource_id: Optional resource ID
            
        Returns:
            Dict containing base FHIR resource structure
        """
        resource = {
            "resourceType": resource_type,
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        if resource_id:
            resource["id"] = str(resource_id)
            
        return resource
    
    def format_date(self, date_obj: date) -> Optional[str]:
        """
        Format a date object to FHIR date format (YYYY-MM-DD)
        
        Args:
            date_obj: Python date object
            
        Returns:
            String in FHIR date format or None if date_obj is None
        """
        if not date_obj:
            return None
        return date_obj.strftime('%Y-%m-%d')
    
    def format_datetime(self, datetime_obj: datetime) -> Optional[str]:
        """
        Format a datetime object to FHIR dateTime format
        
        Args:
            datetime_obj: Python datetime object
            
        Returns:
            String in FHIR dateTime format or None if datetime_obj is None
        """
        if not datetime_obj:
            return None
        return datetime_obj.isoformat() + "Z"
    
    def create_identifier(self, value: str, system: Optional[str] = None, 
                         type_code: Optional[str] = None, type_display: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a FHIR identifier object
        
        Args:
            value: The identifier value
            system: The identifier system URI
            type_code: The identifier type code
            type_display: The identifier type display name
            
        Returns:
            Dict containing FHIR identifier structure
        """
        identifier = {
            "value": value
        }
        
        if system:
            identifier["system"] = system
            
        if type_code and type_display:
            identifier["type"] = {
                "coding": [{
                    "system": self.constants.CODE_SYSTEMS['HL7_IDENTIFIER_TYPE'],
                    "code": type_code,
                    "display": type_display
                }]
            }
            
        return identifier
    
    def create_contact_point(self, value: str, system: str, use: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a FHIR ContactPoint object
        
        Args:
            value: The contact value (phone number, email, etc.)
            system: The contact system ('phone', 'email', etc.)
            use: The contact use ('home', 'work', etc.)
            
        Returns:
            Dict containing FHIR ContactPoint structure
        """
        contact_point = {
            "system": system,
            "value": value
        }
        
        if use:
            contact_point["use"] = use
            
        return contact_point
    
    def create_human_name(self, given_names: List[str], family_name: str, 
                         use: str = "official") -> Dict[str, Any]:
        """
        Create a FHIR HumanName object
        
        Args:
            given_names: List of given names (first, middle, etc.)
            family_name: Family name (last name)
            use: Name use ('official', 'usual', etc.)
            
        Returns:
            Dict containing FHIR HumanName structure
        """
        name = {
            "use": use,
            "family": family_name,
            "given": given_names
        }
        
        return name
    
    def create_address(self, line: Optional[str] = None, city: Optional[str] = None,
                      state: Optional[str] = None, postal_code: Optional[str] = None,
                      country: Optional[str] = None, use: str = "home") -> Dict[str, Any]:
        """
        Create a FHIR Address object
        
        Args:
            line: Street address line
            city: City name
            state: State/province
            postal_code: Postal/zip code
            country: Country
            use: Address use ('home', 'work', etc.)
            
        Returns:
            Dict containing FHIR Address structure
        """
        address = {
            "use": use,
            "type": "physical"
        }
        
        if line:
            address["line"] = [line]
        if city:
            address["city"] = city
        if state:
            address["state"] = state
        if postal_code:
            address["postalCode"] = postal_code
        if country:
            address["country"] = country
            
        return address
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate that required fields are present in the data
        
        Args:
            data: The data dictionary to validate
            required_fields: List of required field names
            
        Returns:
            True if all required fields are present, False otherwise
        """
        for field in required_fields:
            if field not in data or data[field] is None:
                return False
        return True
    
    def clean_empty_fields(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove empty fields from a FHIR resource
        
        Args:
            resource: The FHIR resource dictionary
            
        Returns:
            Cleaned resource dictionary
        """
        cleaned = {}
        for key, value in resource.items():
            if value is not None:
                if isinstance(value, dict):
                    cleaned_value = self.clean_empty_fields(value)
                    if cleaned_value:
                        cleaned[key] = cleaned_value
                elif isinstance(value, list):
                    cleaned_list = [
                        self.clean_empty_fields(item) if isinstance(item, dict) else item
                        for item in value if item is not None
                    ]
                    if cleaned_list:
                        cleaned[key] = cleaned_list
                else:
                    cleaned[key] = value
        return cleaned