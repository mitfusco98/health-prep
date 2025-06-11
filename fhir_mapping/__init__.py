"""
FHIR Mapping Module

This module provides utilities for converting internal healthcare data models
to FHIR (Fast Healthcare Interoperability Resources) format and vice versa.

FHIR R4 is the current standard for healthcare data exchange.
"""

from .patient_mapper import PatientMapper
from .encounter_mapper import EncounterMapper
from .document_reference_mapper import DocumentReferenceMapper
from .base_mapper import BaseFHIRMapper
from .constants import FHIR_CONSTANTS

__all__ = ['PatientMapper', 'EncounterMapper', 'DocumentReferenceMapper', 'BaseFHIRMapper', 'FHIR_CONSTANTS']