"""
DocumentReference FHIR Mapper

This module provides functionality to convert internal MedicalDocument objects
to FHIR DocumentReference resources and vice versa.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from .base_mapper import BaseFHIRMapper
from .constants import FHIR_CONSTANTS


class DocumentReferenceMapper(BaseFHIRMapper):
    """Mapper for converting MedicalDocument objects to/from FHIR DocumentReference resources"""
    
    def __init__(self):
        super().__init__()
    
    def to_fhir(self, document) -> Dict[str, Any]:
        """
        Convert internal MedicalDocument object to FHIR DocumentReference resource
        
        Args:
            document: Internal MedicalDocument model object with fields:
                     - id, patient_id, filename, document_name, document_type
                     - content, binary_content, is_binary, mime_type
                     - source_system, document_date, provider, doc_metadata
                     - created_at, updated_at
                     
        Returns:
            Dict containing FHIR DocumentReference resource
        """
        # Validate required fields
        if not all([document.patient_id, document.filename]):
            raise ValueError("Document missing required fields for FHIR conversion")
        
        # Create base FHIR DocumentReference resource
        fhir_document = self.create_base_resource(
            resource_type=self.constants.RESOURCE_TYPES['DOCUMENT_REFERENCE'],
            resource_id=str(document.id) if document.id else None
        )
        
        # Set document status (current by default)
        fhir_document["status"] = self.constants.DOCUMENT_STATUS['CURRENT']
        
        # Set document status (final by default for processed documents)
        if hasattr(document, 'is_processed') and document.is_processed:
            fhir_document["docStatus"] = self.constants.DOC_STATUS['FINAL']
        else:
            fhir_document["docStatus"] = self.constants.DOC_STATUS['PRELIMINARY']
        
        # Set document type
        fhir_document["type"] = self._create_document_type(document)
        
        # Set document category
        fhir_document["category"] = [self._determine_document_category(document)]
        
        # Set subject (patient reference)
        fhir_document["subject"] = {
            "reference": f"Patient/{document.patient_id}",
            "display": f"Patient {document.patient_id}"
        }
        
        # Set date (use document_date if available, otherwise created_at)
        if hasattr(document, 'document_date') and document.document_date:
            fhir_document["date"] = self.format_datetime(document.document_date)
        elif hasattr(document, 'created_at') and document.created_at:
            fhir_document["date"] = self.format_datetime(document.created_at)
        
        # Add author if provider is available
        if hasattr(document, 'provider') and document.provider:
            fhir_document["author"] = [{
                "display": document.provider
            }]
        
        # Add authenticator/source system
        if hasattr(document, 'source_system') and document.source_system:
            fhir_document["authenticator"] = {
                "display": document.source_system
            }
        
        # Set content attachment
        fhir_document["content"] = [self._create_content_attachment(document)]
        
        # Add identifier for internal document reference
        fhir_document["identifier"] = [{
            "use": "official",
            "system": "http://your-organization.com/document-id",
            "value": str(document.id)
        }]
        
        # Add context if available
        context = self._create_document_context(document)
        if context:
            fhir_document["context"] = context
        
        # Add extensions for additional data
        extensions = self._create_document_extensions(document)
        if extensions:
            fhir_document["extension"] = extensions
        
        # Update meta information
        if hasattr(document, 'updated_at') and document.updated_at:
            fhir_document["meta"]["lastUpdated"] = self.format_datetime(document.updated_at)
        
        # Clean up empty fields
        return self.clean_empty_fields(fhir_document)
    
    def _create_document_type(self, document) -> Dict[str, Any]:
        """Create FHIR document type coding"""
        document_type = getattr(document, 'document_type', 'Other')
        
        # Map to FHIR coding
        type_mapping = self.constants.DOCUMENT_TYPE_MAPPING.get(document_type)
        if not type_mapping:
            type_mapping = self.constants.DOCUMENT_TYPE_MAPPING['Other']
        
        return {
            "coding": [type_mapping],
            "text": document_type
        }
    
    def _determine_document_category(self, document) -> Dict[str, Any]:
        """Determine document category based on document type"""
        document_type = getattr(document, 'document_type', 'Other')
        
        # Map document types to categories
        if document_type in ['Lab Results']:
            category = self.constants.DOCUMENT_CATEGORY['LABORATORY']
        elif document_type in ['Imaging', 'Radiology']:
            category = self.constants.DOCUMENT_CATEGORY['IMAGING']
        else:
            category = self.constants.DOCUMENT_CATEGORY['CLINICAL']
        
        return {
            "coding": [category],
            "text": category['display']
        }
    
    def _create_content_attachment(self, document) -> Dict[str, Any]:
        """Create FHIR content attachment"""
        attachment = {}
        
        # Set content type/MIME type
        if hasattr(document, 'mime_type') and document.mime_type:
            attachment["contentType"] = document.mime_type
        elif hasattr(document, 'is_binary') and document.is_binary:
            attachment["contentType"] = "application/octet-stream"
        else:
            attachment["contentType"] = "text/plain"
        
        # Set title (use document_name if available, otherwise filename)
        if hasattr(document, 'document_name') and document.document_name:
            attachment["title"] = document.document_name
        elif hasattr(document, 'filename') and document.filename:
            attachment["title"] = document.filename
        
        # Set URL reference (construct URL for document access)
        if hasattr(document, 'id') and document.id:
            attachment["url"] = f"http://your-organization.com/documents/{document.id}"
        
        # Set size if available
        if hasattr(document, 'binary_content') and document.binary_content:
            attachment["size"] = len(document.binary_content)
        elif hasattr(document, 'content') and document.content:
            attachment["size"] = len(document.content.encode('utf-8'))
        
        # Set creation date
        if hasattr(document, 'document_date') and document.document_date:
            attachment["creation"] = self.format_datetime(document.document_date)
        elif hasattr(document, 'created_at') and document.created_at:
            attachment["creation"] = self.format_datetime(document.created_at)
        
        # Determine format
        format_code = self._determine_content_format(document)
        if format_code:
            attachment["format"] = format_code
        
        return {
            "attachment": attachment,
            "format": format_code if format_code else self.constants.CONTENT_FORMAT['TEXT']
        }
    
    def _determine_content_format(self, document) -> Optional[Dict[str, Any]]:
        """Determine content format based on MIME type"""
        if hasattr(document, 'mime_type') and document.mime_type:
            if 'pdf' in document.mime_type.lower():
                return self.constants.CONTENT_FORMAT['PDF']
            elif 'text' in document.mime_type.lower():
                return self.constants.CONTENT_FORMAT['TEXT']
        
        # Default based on binary flag
        if hasattr(document, 'is_binary') and document.is_binary:
            return self.constants.CONTENT_FORMAT['PDF']
        
        return self.constants.CONTENT_FORMAT['TEXT']
    
    def _create_document_context(self, document) -> Optional[Dict[str, Any]]:
        """Create document context information"""
        context = {}
        
        # Add source system as encounter reference if available
        if hasattr(document, 'source_system') and document.source_system:
            context["sourcePatientInfo"] = {
                "display": f"Source: {document.source_system}"
            }
        
        # Add document metadata as related information
        if hasattr(document, 'doc_metadata') and document.doc_metadata:
            try:
                metadata = json.loads(document.doc_metadata)
                if metadata:
                    context["related"] = [{
                        "display": f"Metadata: {str(metadata)[:100]}..."
                    }]
            except (json.JSONDecodeError, TypeError):
                pass
        
        return context if context else None
    
    def _create_document_extensions(self, document) -> List[Dict[str, Any]]:
        """Create FHIR extensions for additional document data"""
        extensions = []
        
        # Original filename as extension
        if hasattr(document, 'filename') and document.filename:
            filename_extension = {
                "url": "http://your-organization.com/fhir/StructureDefinition/original-filename",
                "valueString": document.filename
            }
            extensions.append(filename_extension)
        
        # Processing status as extension
        if hasattr(document, 'is_processed'):
            processed_extension = {
                "url": "http://your-organization.com/fhir/StructureDefinition/is-processed",
                "valueBoolean": document.is_processed
            }
            extensions.append(processed_extension)
        
        # Binary content flag as extension
        if hasattr(document, 'is_binary'):
            binary_extension = {
                "url": "http://your-organization.com/fhir/StructureDefinition/is-binary",
                "valueBoolean": document.is_binary
            }
            extensions.append(binary_extension)
        
        # Document metadata as extension
        if hasattr(document, 'doc_metadata') and document.doc_metadata:
            metadata_extension = {
                "url": "http://your-organization.com/fhir/StructureDefinition/document-metadata",
                "valueString": document.doc_metadata
            }
            extensions.append(metadata_extension)
        
        return extensions
    
    def from_fhir(self, fhir_document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FHIR DocumentReference resource to internal document data format
        
        Args:
            fhir_document: FHIR DocumentReference resource dictionary
            
        Returns:
            Dict containing internal document data fields
        """
        document_data = {}
        
        # Extract patient ID from subject reference
        subject = fhir_document.get("subject", {})
        reference = subject.get("reference", "")
        if reference.startswith("Patient/"):
            document_data["patient_id"] = int(reference.split("/")[1])
        
        # Extract document type
        doc_type = fhir_document.get("type", {})
        type_text = doc_type.get("text")
        if type_text:
            document_data["document_type"] = type_text
        
        # Extract document date
        doc_date = fhir_document.get("date")
        if doc_date:
            try:
                document_data["document_date"] = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # Extract content information
        content_list = fhir_document.get("content", [])
        if content_list:
            attachment = content_list[0].get("attachment", {})
            
            # Extract filename/title
            title = attachment.get("title")
            if title:
                document_data["document_name"] = title
                if '.' in title:
                    document_data["filename"] = title
                else:
                    document_data["filename"] = f"{title}.txt"
            
            # Extract MIME type
            content_type = attachment.get("contentType")
            if content_type:
                document_data["mime_type"] = content_type
                document_data["is_binary"] = not content_type.startswith("text/")
        
        # Extract author/provider
        authors = fhir_document.get("author", [])
        if authors:
            document_data["provider"] = authors[0].get("display", "")
        
        # Extract authenticator/source system
        authenticator = fhir_document.get("authenticator", {})
        if authenticator:
            document_data["source_system"] = authenticator.get("display", "")
        
        # Extract extensions
        extensions = fhir_document.get("extension", [])
        for ext in extensions:
            url = ext.get("url", "")
            if "is-processed" in url:
                document_data["is_processed"] = ext.get("valueBoolean", False)
            elif "document-metadata" in url:
                document_data["doc_metadata"] = ext.get("valueString", "")
        
        return document_data
    
    def validate_fhir_document_reference(self, fhir_document: Dict[str, Any]) -> bool:
        """
        Validate that a FHIR DocumentReference resource has required fields
        
        Args:
            fhir_document: FHIR DocumentReference resource dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["resourceType", "status", "type", "subject", "content"]
        
        if not self.validate_required_fields(fhir_document, required_fields):
            return False
        
        # Check resource type
        if fhir_document.get("resourceType") != "DocumentReference":
            return False
        
        # Check that subject reference exists
        subject = fhir_document.get("subject", {})
        if not subject.get("reference"):
            return False
        
        # Check that content has attachment
        content_list = fhir_document.get("content", [])
        if not content_list or not content_list[0].get("attachment"):
            return False
        
        return True
    
    def create_document_bundle(self, documents: List) -> Dict[str, Any]:
        """
        Create FHIR Bundle from multiple documents
        
        Args:
            documents: List of MedicalDocument model instances
            
        Returns:
            Dict containing FHIR Bundle resource
        """
        bundle = {
            "resourceType": "Bundle",
            "id": "document-bundle",
            "type": "collection",
            "timestamp": self.format_datetime(datetime.utcnow()),
            "total": len(documents),
            "entry": []
        }
        
        for document in documents:
            try:
                fhir_document = self.to_fhir(document)
                bundle["entry"].append({
                    "fullUrl": f"DocumentReference/{document.id}",
                    "resource": fhir_document
                })
            except ValueError:
                # Skip documents with incomplete data
                bundle["total"] -= 1
                continue
        
        return bundle