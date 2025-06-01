"""
Electronic Health Record (EHR) integration module for HealthPrep
Supports FHIR (Fast Healthcare Interoperability Resources) standard
"""

import json
import logging
import os
import requests
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union

import models
from app import db
from utils import group_documents_by_type

# Configure logging
logger = logging.getLogger(__name__)


class EHRVendor(Enum):
    """Supported EHR system vendors"""
    EPIC = "Epic"
    CERNER = "Cerner"
    ALLSCRIPTS = "Allscripts"
    ATHENAHEALTH = "AthenaHealth"
    ECLINICALWORKS = "eClinicalWorks"
    NEXTGEN = "NextGen"
    GENERIC_FHIR = "Generic FHIR"


class EHRConnectionConfig:
    """Configuration for an EHR system connection"""
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        vendor: EHRVendor = EHRVendor.GENERIC_FHIR,
        use_auth_header: bool = True
    ):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.client_id = client_id
        self.client_secret = client_secret
        self.vendor = vendor
        self.use_auth_header = use_auth_header
        self.auth_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None


class EHRIntegrationService:
    """Service for integrating with EHR systems"""
    
    def __init__(self):
        self.connections = {}  # Dictionary of EHRConnectionConfig objects
        
    def add_connection(self, connection: EHRConnectionConfig):
        """Add a new EHR connection to the service"""
        self.connections[connection.name] = connection
        logger.info(f"Added connection to EHR system: {connection.name}")
        
    def remove_connection(self, connection_name: str):
        """Remove an EHR connection from the service"""
        if connection_name in self.connections:
            del self.connections[connection_name]
            logger.info(f"Removed connection to EHR system: {connection_name}")
            
    def get_connection(self, connection_name: str) -> Optional[EHRConnectionConfig]:
        """Get an EHR connection by name"""
        return self.connections.get(connection_name)
    
    def list_connections(self) -> List[str]:
        """List all available EHR connections"""
        return list(self.connections.keys())
    
    def validate_key_for_client_use(self, api_key: str) -> bool:
        """Validate that an API key is safe for client-side use"""
        if not api_key:
            return False
        
        # Never allow service or admin keys
        forbidden_patterns = [
            'service_role', 'admin', 'root', 'sk_', 'rk_', 
            'secret', 'private', 'confidential'
        ]
        
        api_key_lower = api_key.lower()
        for pattern in forbidden_patterns:
            if pattern in api_key_lower:
                logger.error(f"Blocked service-level key usage: {pattern}")
                return False
        
        return True
    
    def get_client_safe_credentials(self, connection_name: str) -> Dict[str, str]:
        """Get only client-safe credentials for frontend use"""
        connection = self.get_connection(connection_name)
        if not connection:
            return {}
        
        safe_data = {
            'name': connection.name,
            'base_url': connection.base_url,
            'vendor': connection.vendor.value,
            'auth_type': 'public' if connection.api_key else 'none'
        }
        
        # Only include public/anon keys, never service keys
        if connection.api_key and self.validate_key_for_client_use(connection.api_key):
            # Only expose if it's confirmed to be a public key
            if 'anon' in connection.api_key.lower() or 'public' in connection.api_key.lower():
                safe_data['has_public_key'] = True
        
        return safe_data

    def get_auth_token(self, connection_name: str) -> Optional[str]:
        """Get an authentication token for an EHR system
        
        Will get a new token if none exists, or if the existing token is expired.
        Uses OAuth2 client credentials flow if client_id and client_secret are provided.
        Otherwise, uses the API key if provided.
        """
        connection = self.get_connection(connection_name)
        if not connection:
            logger.error(f"Connection not found: {connection_name}")
            return None
            
        # Check if we have a valid token already
        if connection.auth_token and connection.token_expiry and connection.token_expiry > datetime.now():
            return connection.auth_token
            
        # Need to get a new token
        if connection.client_id and connection.client_secret:
            # Use OAuth2 client credentials flow
            try:
                token_url = f"{connection.base_url}/token"
                payload = {
                    "grant_type": "client_credentials",
                    "client_id": connection.client_id,
                    "client_secret": connection.client_secret
                }
                
                response = requests.post(token_url, data=payload)
                response.raise_for_status()
                
                token_data = response.json()
                connection.auth_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour if not specified
                connection.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"Got new auth token for {connection_name}, expires in {expires_in} seconds")
                return connection.auth_token
                
            except Exception as e:
                logger.error(f"Error getting OAuth token for {connection_name}: {str(e)}")
                return None
        
        # If no client credentials, use API key if available
        if connection.api_key:
            return connection.api_key
            
        logger.error(f"No authentication method available for {connection_name}")
        return None
    
    def make_api_request(
        self, 
        connection_name: str, 
        endpoint: str, 
        method: str = "GET", 
        params: Optional[Dict] = None, 
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make a request to an EHR API endpoint"""
        connection = self.get_connection(connection_name)
        if not connection:
            logger.error(f"Connection not found: {connection_name}")
            return None
            
        # Get auth token
        auth_token = self.get_auth_token(connection_name)
        if not auth_token and (connection.client_id or connection.api_key):
            logger.error(f"Failed to get authentication token for {connection_name}")
            return None
            
        # Prepare headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Add authentication
        if auth_token and connection.use_auth_header:
            if connection.client_id:  # OAuth
                headers["Authorization"] = f"Bearer {auth_token}"
            else:  # API key
                headers["X-API-KEY"] = auth_token
                
        # Build URL
        url = f"{connection.base_url}/{endpoint.lstrip('/')}"
        
        # Make the request
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=data if data else None,
                timeout=30
            )
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited by {connection_name}, retrying after {retry_after} seconds")
                time.sleep(retry_after)
                return self.make_api_request(connection_name, endpoint, method, params, data)
                
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return None


# FHIR-specific functionality
class FHIRService:
    """Service for interacting with FHIR-compatible EHR systems"""
    
    def __init__(self, ehr_service: EHRIntegrationService):
        self.ehr_service = ehr_service
        
    def get_patient(self, connection_name: str, patient_id: str) -> Optional[Dict]:
        """Get a patient by ID from the EHR system"""
        return self.ehr_service.make_api_request(
            connection_name=connection_name,
            endpoint=f"Patient/{patient_id}"
        )
        
    def search_patients(
        self, 
        connection_name: str, 
        family_name: Optional[str] = None,
        given_name: Optional[str] = None,
        birthdate: Optional[str] = None,
        identifier: Optional[str] = None,
        mrn: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Search for patients in the EHR system"""
        params = {}
        
        if family_name:
            params["family"] = family_name
        if given_name:
            params["given"] = given_name
        if birthdate:
            params["birthdate"] = birthdate
        if identifier:
            params["identifier"] = identifier
        if mrn:
            # MRN is typically stored as an identifier
            params["identifier"] = f"MRN|{mrn}"
            
        response = self.ehr_service.make_api_request(
            connection_name=connection_name,
            endpoint="Patient",
            params=params
        )
        
        if response and "entry" in response:
            return [entry["resource"] for entry in response["entry"]]
        return []
    
    def get_conditions(self, connection_name: str, patient_id: str) -> Optional[List[Dict]]:
        """Get conditions (problems) for a patient"""
        params = {
            "patient": patient_id,
            "_sort": "-recorded-date"
        }
        
        response = self.ehr_service.make_api_request(
            connection_name=connection_name,
            endpoint="Condition",
            params=params
        )
        
        if response and "entry" in response:
            return [entry["resource"] for entry in response["entry"]]
        return []
    
    def get_observations(
        self, 
        connection_name: str, 
        patient_id: str,
        category: Optional[str] = None,
        code: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get observations (measurements, vital signs, lab results) for a patient"""
        params = {
            "patient": patient_id,
            "_sort": "-date"
        }
        
        if category:
            params["category"] = category
        if code:
            params["code"] = code
        if date_from:
            params["date"] = f"ge{date_from}"
        if date_to:
            if "date" in params:
                params["date"] += f"&date=le{date_to}"
            else:
                params["date"] = f"le{date_to}"
                
        response = self.ehr_service.make_api_request(
            connection_name=connection_name,
            endpoint="Observation",
            params=params
        )
        
        if response and "entry" in response:
            return [entry["resource"] for entry in response["entry"]]
        return []
        
    def get_documents(
        self, 
        connection_name: str, 
        patient_id: str,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get clinical documents for a patient"""
        params = {
            "patient": patient_id,
            "_sort": "-date"
        }
        
        if category:
            params["category"] = category
        if date_from:
            params["date"] = f"ge{date_from}"
        if date_to:
            if "date" in params:
                params["date"] += f"&date=le{date_to}"
            else:
                params["date"] = f"le{date_to}"
                
        response = self.ehr_service.make_api_request(
            connection_name=connection_name,
            endpoint="DocumentReference",
            params=params
        )
        
        if response and "entry" in response:
            return [entry["resource"] for entry in response["entry"]]
        return []
        
    def import_patient(self, connection_name: str, fhir_patient: Dict) -> Optional[models.Patient]:
        """Import a patient from FHIR format into the local database"""
        try:
            # Extract data from FHIR patient resource
            identifier = next((id for id in fhir_patient.get("identifier", []) 
                              if id.get("type", {}).get("coding", [{}])[0].get("code") == "MR"), None)
            mrn = identifier.get("value") if identifier else None
            
            if not mrn:
                logger.error("Patient has no MRN identifier")
                return None
                
            # Check if patient already exists
            existing_patient = models.Patient.query.filter_by(mrn=mrn).first()
            if existing_patient:
                logger.info(f"Patient with MRN {mrn} already exists, updating")
                patient = existing_patient
            else:
                logger.info(f"Creating new patient with MRN {mrn}")
                patient = models.Patient(mrn=mrn)
                
            # Update patient data
            name = fhir_patient.get("name", [{}])[0]
            patient.first_name = name.get("given", [""])[0] if name.get("given") else ""
            patient.last_name = name.get("family", "")
            
            # Handle birthdate
            birthdate = fhir_patient.get("birthDate")
            if birthdate:
                try:
                    patient.date_of_birth = datetime.strptime(birthdate, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Invalid birthdate format: {birthdate}")
            
            # Handle gender
            gender_map = {
                "male": "Male",
                "female": "Female",
                "other": "Other",
                "unknown": "Other"
            }
            patient.sex = gender_map.get(fhir_patient.get("gender", "unknown"), "Other")
            
            # Handle contact info
            telecom = fhir_patient.get("telecom", [])
            phone = next((t.get("value") for t in telecom if t.get("system") == "phone"), None)
            email = next((t.get("value") for t in telecom if t.get("system") == "email"), None)
            patient.phone = phone or ""
            patient.email = email or ""
            
            # Handle address
            address = fhir_patient.get("address", [{}])[0] if fhir_patient.get("address") else {}
            address_parts = []
            if address.get("line"):
                address_parts.extend(address.get("line", []))
            if address.get("city"):
                address_parts.append(address.get("city"))
            if address.get("state"):
                address_parts.append(address.get("state"))
            if address.get("postalCode"):
                address_parts.append(address.get("postalCode"))
            patient.address = "\n".join(address_parts) if address_parts else ""
            
            # Save to database
            if not existing_patient:
                db.session.add(patient)
            db.session.commit()
            
            return patient
            
        except Exception as e:
            logger.error(f"Error importing patient: {str(e)}")
            db.session.rollback()
            return None
    
    def import_conditions(self, connection_name: str, patient: models.Patient, fhir_conditions: List[Dict]) -> int:
        """Import conditions from FHIR format into the local database"""
        try:
            count = 0
            for fhir_condition in fhir_conditions:
                # Extract condition code and name
                coding = fhir_condition.get("code", {}).get("coding", [{}])[0]
                code = coding.get("code", "")
                name = coding.get("display") or fhir_condition.get("code", {}).get("text", "Unknown Condition")
                
                # Check if condition already exists
                existing_condition = models.Condition.query.filter_by(
                    patient_id=patient.id,
                    code=code,
                    name=name
                ).first()
                
                if existing_condition:
                    logger.info(f"Condition {name} already exists for patient {patient.id}")
                    continue
                    
                # Extract date
                onset_date = None
                onset_datetime = fhir_condition.get("onsetDateTime")
                if onset_datetime:
                    try:
                        onset_date = datetime.fromisoformat(onset_datetime.replace("Z", "+00:00") if onset_datetime else onset_datetime)
                    except ValueError:
                        logger.warning(f"Invalid onset date format: {onset_datetime}")
                
                # Determine if condition is active
                clinical_status = fhir_condition.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
                is_active = clinical_status in ("active", "recurrence", "relapse")
                
                # Create new condition
                condition = models.Condition(
                    patient_id=patient.id,
                    name=name,
                    code=code,
                    diagnosed_date=onset_date,
                    is_active=is_active,
                    notes=fhir_condition.get("note", [{}])[0].get("text", "") if fhir_condition.get("note") else ""
                )
                
                db.session.add(condition)
                count += 1
                
            db.session.commit()
            return count
            
        except Exception as e:
            logger.error(f"Error importing conditions: {str(e)}")
            db.session.rollback()
            return 0
    
    def import_vital_signs(
        self, 
        connection_name: str, 
        patient: models.Patient, 
        fhir_observations: List[Dict]
    ) -> int:
        """Import vital signs from FHIR observations into the local database"""
        try:
            # Group observations by date
            observations_by_date = {}
            for obs in fhir_observations:
                effective_date = None
                
                # Try to get the effective date
                effective_datetime = obs.get("effectiveDateTime")
                if effective_datetime:
                    try:
                        effective_date = datetime.fromisoformat(
                            effective_datetime.replace("Z", "+00:00") if effective_datetime else effective_datetime
                        ).date()
                    except ValueError:
                        logger.warning(f"Invalid date format: {effective_datetime}")
                        continue
                else:
                    # Skip observations without a date
                    continue
                
                # Initialize group for this date
                if effective_date not in observations_by_date:
                    observations_by_date[effective_date] = []
                    
                observations_by_date[effective_date].append(obs)
            
            # Process each date's observations
            count = 0
            for date, obs_list in observations_by_date.items():
                # Check if vitals already exist for this date
                existing_vitals = models.Vital.query.filter_by(
                    patient_id=patient.id,
                    date=date
                ).first()
                
                if existing_vitals:
                    logger.info(f"Vitals for {date} already exist for patient {patient.id}")
                    continue
                
                # Extract vital sign values
                vitals_data = {
                    "weight": None,
                    "height": None,
                    "temperature": None,
                    "blood_pressure_systolic": None,
                    "blood_pressure_diastolic": None,
                    "pulse": None,
                    "respiratory_rate": None,
                    "oxygen_saturation": None
                }
                
                for obs in obs_list:
                    coding = obs.get("code", {}).get("coding", [{}])[0]
                    code = coding.get("code", "")
                    
                    # Get the value
                    value = None
                    if obs.get("valueQuantity"):
                        value = obs.get("valueQuantity", {}).get("value")
                    elif obs.get("component"):
                        # Handle components (like blood pressure)
                        components = obs.get("component", [])
                        for component in components:
                            component_code = component.get("code", {}).get("coding", [{}])[0].get("code", "")
                            component_value = component.get("valueQuantity", {}).get("value")
                            
                            if component_code == "8480-6" and component_value:  # Systolic
                                vitals_data["blood_pressure_systolic"] = component_value
                            elif component_code == "8462-4" and component_value:  # Diastolic
                                vitals_data["blood_pressure_diastolic"] = component_value
                    
                    # Map FHIR codes to our vitals fields
                    if code == "29463-7" and value:  # Weight
                        # Convert from kg if needed
                        unit = obs.get("valueQuantity", {}).get("unit", "kg").lower()
                        if unit in ("lb", "lbs", "pound", "pounds"):
                            value = value * 0.45359237  # Convert to kg
                        vitals_data["weight"] = value
                    elif code == "8302-2" and value:  # Height
                        # Convert to cm if needed
                        unit = obs.get("valueQuantity", {}).get("unit", "cm").lower()
                        if unit in ("in", "inch", "inches"):
                            value = value * 2.54  # Convert to cm
                        vitals_data["height"] = value
                    elif code == "8310-5" and value:  # Temperature
                        # Convert to Celsius if needed
                        unit = obs.get("valueQuantity", {}).get("unit", "Cel").lower()
                        if unit in ("f", "fahrenheit"):
                            value = (value - 32) * 5/9  # Convert to Celsius
                        vitals_data["temperature"] = value
                    elif code == "8867-4" and value:  # Pulse
                        vitals_data["pulse"] = value
                    elif code == "9279-1" and value:  # Respiratory rate
                        vitals_data["respiratory_rate"] = value
                    elif code == "2708-6" and value:  # Oxygen saturation
                        vitals_data["oxygen_saturation"] = value
                
                # Calculate BMI if we have height and weight
                bmi = None
                if vitals_data["weight"] and vitals_data["height"]:
                    height_m = vitals_data["height"] / 100  # Convert cm to m
                    bmi = round(vitals_data["weight"] / (height_m * height_m), 1)
                
                # Create new vitals record
                vitals = models.Vital(
                    patient_id=patient.id,
                    date=date,
                    weight=vitals_data["weight"],
                    height=vitals_data["height"],
                    bmi=bmi,
                    temperature=vitals_data["temperature"],
                    blood_pressure_systolic=vitals_data["blood_pressure_systolic"],
                    blood_pressure_diastolic=vitals_data["blood_pressure_diastolic"],
                    pulse=vitals_data["pulse"],
                    respiratory_rate=vitals_data["respiratory_rate"],
                    oxygen_saturation=vitals_data["oxygen_saturation"]
                )
                
                db.session.add(vitals)
                count += 1
            
            db.session.commit()
            return count
            
        except Exception as e:
            logger.error(f"Error importing vital signs: {str(e)}")
            db.session.rollback()
            return 0
    
    def import_documents(
        self, 
        connection_name: str, 
        patient: models.Patient, 
        fhir_documents: List[Dict]
    ) -> int:
        """Import clinical documents from FHIR format into the local database"""
        try:
            count = 0
            for fhir_doc in fhir_documents:
                # Extract document metadata
                doc_id = fhir_doc.get("id")
                
                # Skip if no ID
                if not doc_id:
                    continue
                    
                # Check if document already exists
                existing_doc = models.MedicalDocument.query.filter_by(
                    patient_id=patient.id,
                    source_system=connection_name,
                    filename=f"FHIR-{doc_id}"
                ).first()
                
                if existing_doc:
                    logger.info(f"Document {doc_id} already exists for patient {patient.id}")
                    continue
                
                # Extract document type
                type_coding = fhir_doc.get("type", {}).get("coding", [{}])[0]
                doc_type = type_coding.get("display") or type_coding.get("code", "")
                
                # Map FHIR document type to our document types
                document_type_map = {
                    "34133-9": models.DocumentType.DISCHARGE_SUMMARY.value,  # Discharge summary
                    "11490-0": models.DocumentType.DISCHARGE_SUMMARY.value,  # Discharge note
                    "18842-5": models.DocumentType.DISCHARGE_SUMMARY.value,  # Discharge summary
                    "28570-0": models.DocumentType.OPERATIVE_REPORT.value,   # Procedure note
                    "59258-4": models.DocumentType.OPERATIVE_REPORT.value,   # Procedure report
                    "28578-3": models.DocumentType.OPERATIVE_REPORT.value,   # Operative note
                    "11526-1": models.DocumentType.PATHOLOGY_REPORT.value,   # Pathology study
                    "18743-5": models.DocumentType.PATHOLOGY_REPORT.value,   # Autopsy report
                    "18805-2": models.DocumentType.PATHOLOGY_REPORT.value,   # Pathology report
                    "18751-8": models.DocumentType.RADIOLOGY_REPORT.value,   # Radiology study
                    "55111-9": models.DocumentType.RADIOLOGY_REPORT.value,   # Radiology imaging study
                    "68604-8": models.DocumentType.RADIOLOGY_REPORT.value,   # Radiology report
                    "11502-2": models.DocumentType.LAB_REPORT.value,         # Laboratory report
                    "26436-6": models.DocumentType.LAB_REPORT.value,         # Laboratory studies
                    "11488-4": models.DocumentType.CONSULTATION.value,       # Consultation note
                    "11490-0": models.DocumentType.CONSULTATION.value,       # Physician note
                    "18776-5": models.DocumentType.CONSULTATION.value,       # Consultation report
                    "10160-0": models.DocumentType.MEDICATION_LIST.value,    # Medication list
                    "57017-6": models.DocumentType.MEDICATION_LIST.value,    # Patient medication list
                    "57828-6": models.DocumentType.MEDICATION_LIST.value,    # Prescription list
                }
                
                mapped_type = document_type_map.get(
                    type_coding.get("code", ""), 
                    models.DocumentType.UNKNOWN.value
                )
                
                # Get document date
                doc_date = None
                doc_date_str = fhir_doc.get("date")
                if doc_date_str:
                    try:
                        doc_date = datetime.fromisoformat(doc_date_str.replace("Z", "+00:00") if doc_date_str else doc_date_str)
                    except ValueError:
                        logger.warning(f"Invalid document date format: {doc_date_str}")
                        doc_date = datetime.now()
                else:
                    doc_date = datetime.now()
                
                # Try to get document content
                content = ""
                if fhir_doc.get("content"):
                    for content_item in fhir_doc.get("content", []):
                        attachment = content_item.get("attachment", {})
                        if attachment.get("contentType") == "text/plain" and attachment.get("data"):
                            import base64
                            content = base64.b64decode(attachment.get("data")).decode("utf-8", errors="replace")
                            break
                        elif attachment.get("url"):
                            # Get content from URL
                            try:
                                # Need to implement document retrieval
                                pass
                            except Exception as e:
                                logger.error(f"Error retrieving document content: {str(e)}")
                
                # If no content, use a placeholder
                if not content:
                    content = f"Document content not available. Document ID: {doc_id}. Type: {doc_type}."
                
                # Create document metadata
                metadata = {
                    "document_type": mapped_type,
                    "fhir_id": doc_id,
                    "fhir_type": type_coding.get("code", ""),
                    "fhir_type_display": type_coding.get("display", "")
                }
                
                # Extract author information
                if fhir_doc.get("author"):
                    authors = []
                    for author_ref in fhir_doc.get("author", []):
                        if author_ref.get("display"):
                            authors.append(author_ref.get("display"))
                    if authors:
                        metadata["authors"] = authors
                
                # Create new document
                document = models.MedicalDocument(
                    patient_id=patient.id,
                    filename=f"FHIR-{doc_id}",
                    document_type=mapped_type,
                    content=content,
                    source_system=connection_name,
                    document_date=doc_date,
                    provider=", ".join(metadata.get("authors", [])) if metadata.get("authors") else None,
                    doc_metadata=json.dumps(metadata)
                )
                
                db.session.add(document)
                count += 1
            
            db.session.commit()
            return count
            
        except Exception as e:
            logger.error(f"Error importing documents: {str(e)}")
            db.session.rollback()
            return 0


# Create global instances
ehr_service = EHRIntegrationService()
fhir_service = FHIRService(ehr_service)

# Example of how to set up a connection
def setup_example_connection():
    """Set up an example EHR connection for demonstration purposes"""
    connection = EHRConnectionConfig(
        name="Example FHIR Server",
        base_url="https://server.example.com/fhir",
        api_key=os.environ.get("EXAMPLE_FHIR_API_KEY"),
        vendor=EHRVendor.GENERIC_FHIR
    )
    ehr_service.add_connection(connection)
    return connection
