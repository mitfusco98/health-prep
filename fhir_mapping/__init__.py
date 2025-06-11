"""
FHIR Mapping Module

This module provides utilities for converting internal healthcare data models
to FHIR (Fast Healthcare Interoperability Resources) format and vice versa.

FHIR R4 is the current standard for healthcare data exchange.
"""

from .patient_mapper import PatientMapper
from .base_mapper import BaseFHIRMapper
from .constants import FHIR_CONSTANTS

__all__ = ['PatientMapper', 'BaseFHIRMapper', 'FHIR_CONSTANTS']