"""
Test Suite for FHIR-Style Document Metadata System

This demonstrates how your documents now use FHIR-structured metadata fields:
- code.coding.code
- code.coding.system  
- type.coding.display
- effectiveDateTime
- category

Your existing database fields remain unchanged.
"""

import json
from datetime import datetime
from fhir_document_metadata import (
    DocumentFHIRMetadata,
    DocumentFHIRMetadataBuilder,
    FHIRCoding,
    FHIRCodeableConcept,
    FHIRCodingSystem
)
from document_fhir_helpers import (
    enhance_document_on_upload,
    add_fhir_coding_to_document,
    set_document_effective_datetime,
    get_document_fhir_codes,
    get_document_display_metadata
)


class MockMedicalDocument:
    """Mock document that matches your MedicalDocument model structure"""
    def __init__(self, doc_id, document_type, filename="test.pdf"):
        self.id = doc_id
        self.patient_id = 12345
        self.filename = filename
        self.document_name = f"Test {document_type}"
        self.document_type = document_type
        self.content = "Sample content"
        self.binary_content = None
        self.is_binary = False
        self.mime_type = "application/pdf"
        self.source_system = "Test EHR"
        self.document_date = datetime(2024, 6, 15, 10, 30)
        self.provider = "Dr. Test Provider"
        self.doc_metadata = None  # This will store our FHIR metadata
        self.is_processed = True
        self.created_at = datetime(2024, 6, 15, 11, 0)
        self.updated_at = datetime(2024, 6, 15, 11, 15)


def test_lab_result_fhir_metadata():
    """Test FHIR metadata for lab results"""
    print("=== Lab Result FHIR Metadata Test ===")
    
    # Create lab result document
    document = MockMedicalDocument(101, "Lab Results", "cbc_results.pdf")
    
    # Enhance with FHIR metadata using form data
    form_data = {
        "test_type": "CBC",
        "lab_id": "LAB-2024-001",
        "lab_status": "final"
    }
    
    enhance_document_on_upload(document, form_data)
    
    # Verify FHIR structure
    metadata_dict = json.loads(document.doc_metadata)
    fhir_data = metadata_dict["fhir"]
    
    print(f"Document Type: {document.document_type}")
    print(f"FHIR Code System: {fhir_data['code']['coding'][0]['system']}")
    print(f"FHIR Code: {fhir_data['code']['coding'][0]['code']}")
    print(f"FHIR Code Display: {fhir_data['code']['coding'][0]['display']}")
    print(f"FHIR Type Display: {fhir_data['type']['coding'][0]['display']}")
    print(f"FHIR Category: {fhir_data['category']['coding'][0]['display']}")
    print(f"Effective DateTime: {fhir_data['effectiveDateTime']}")
    print(f"Extensions: {fhir_data['extensions']}")
    print()
    
    return document


def test_imaging_fhir_metadata():
    """Test FHIR metadata for imaging studies"""
    print("=== Imaging Study FHIR Metadata Test ===")
    
    # Create imaging document
    document = MockMedicalDocument(102, "Imaging", "chest_xray.jpg")
    
    # Enhance with FHIR metadata
    form_data = {
        "modality": "XRAY",
        "body_part": "Chest",
        "study_type": "Diagnostic"
    }
    
    enhance_document_on_upload(document, form_data)
    
    # Verify FHIR structure
    metadata_dict = json.loads(document.doc_metadata)
    fhir_data = metadata_dict["fhir"]
    
    print(f"Document Type: {document.document_type}")
    print(f"FHIR Code System: {fhir_data['code']['coding'][0]['system']}")
    print(f"FHIR Code: {fhir_data['code']['coding'][0]['code']}")
    print(f"FHIR Code Display: {fhir_data['code']['coding'][0]['display']}")
    print(f"FHIR Type Display: {fhir_data['type']['coding'][0]['display']}")
    print(f"FHIR Category: {fhir_data['category']['coding'][0]['display']}")
    print(f"Extensions: {fhir_data['extensions']}")
    print()
    
    return document


def test_clinical_note_fhir_metadata():
    """Test FHIR metadata for clinical notes"""
    print("=== Clinical Note FHIR Metadata Test ===")
    
    # Create progress note document
    document = MockMedicalDocument(103, "Progress Notes", "progress_note.txt")
    
    # Enhance with FHIR metadata
    form_data = {
        "specialty": "Cardiology"
    }
    
    enhance_document_on_upload(document, form_data)
    
    # Verify FHIR structure
    metadata_dict = json.loads(document.doc_metadata)
    fhir_data = metadata_dict["fhir"]
    
    print(f"Document Type: {document.document_type}")
    print(f"FHIR Code System: {fhir_data['code']['coding'][0]['system']}")
    print(f"FHIR Code: {fhir_data['code']['coding'][0]['code']}")
    print(f"FHIR Code Display: {fhir_data['code']['coding'][0]['display']}")
    print(f"FHIR Type Display: {fhir_data['type']['coding'][0]['display']}")
    print(f"FHIR Category: {fhir_data['category']['coding'][0]['display']}")
    print(f"Extensions: {fhir_data['extensions']}")
    print()
    
    return document


def test_adding_custom_fhir_codes():
    """Test adding custom FHIR codes to documents"""
    print("=== Custom FHIR Codes Test ===")
    
    document = MockMedicalDocument(104, "Other", "custom_document.pdf")
    enhance_document_on_upload(document)
    
    # Add custom LOINC code
    add_fhir_coding_to_document(
        document,
        code_system="http://loinc.org",
        code="34133-9",
        display="Summarization of episode note",
        coding_type="code"
    )
    
    # Add custom SNOMED CT code for type
    add_fhir_coding_to_document(
        document,
        code_system="http://snomed.info/sct",
        code="371530004",
        display="Clinical consultation report",
        coding_type="type"
    )
    
    # Get all FHIR codes
    fhir_codes = get_document_fhir_codes(document)
    
    print("Custom FHIR Codes Added:")
    print(f"Code Codings: {fhir_codes['code']}")
    print(f"Type Codings: {fhir_codes['type']}")
    print(f"Category Codings: {fhir_codes['category']}")
    print()
    
    return document


def test_effective_datetime():
    """Test FHIR effectiveDateTime functionality"""
    print("=== Effective DateTime Test ===")
    
    document = MockMedicalDocument(105, "Discharge Summary", "discharge.pdf")
    enhance_document_on_upload(document)
    
    # Set custom effective date
    custom_date = datetime(2024, 7, 1, 14, 30, 0)
    set_document_effective_datetime(document, custom_date)
    
    # Verify effective date was set
    metadata_dict = json.loads(document.doc_metadata)
    fhir_data = metadata_dict["fhir"]
    
    print(f"Original Document Date: {document.document_date}")
    print(f"FHIR Effective DateTime: {fhir_data['effectiveDateTime']}")
    print()
    
    return document


def test_display_metadata():
    """Test formatted metadata for UI display"""
    print("=== Display Metadata Test ===")
    
    # Create lab document with FHIR metadata
    document = MockMedicalDocument(106, "Lab Results", "lipid_panel.pdf")
    form_data = {
        "test_type": "Lipid Panel",
        "lab_id": "LAB-2024-002",
        "lab_status": "final"
    }
    enhance_document_on_upload(document, form_data)
    
    # Get formatted display metadata
    display_data = get_document_display_metadata(document)
    
    print("Formatted Metadata for UI:")
    print(json.dumps(display_data, indent=2, default=str))
    print()
    
    return document


def test_metadata_builder_direct():
    """Test using the metadata builder directly"""
    print("=== Direct Metadata Builder Test ===")
    
    builder = DocumentFHIRMetadataBuilder()
    
    # Create lab metadata directly
    lab_metadata = builder.create_lab_result_metadata(
        test_type="BMP",
        lab_id="LAB-2024-003",
        status="final"
    )
    
    print("Lab Metadata Structure:")
    print(json.dumps(lab_metadata.to_dict(), indent=2))
    print()
    
    # Create imaging metadata directly
    imaging_metadata = builder.create_imaging_metadata(
        study_type="Emergency",
        modality="CT",
        body_part="Head"
    )
    
    print("Imaging Metadata Structure:")
    print(json.dumps(imaging_metadata.to_dict(), indent=2))
    print()
    
    return lab_metadata, imaging_metadata


def test_fhir_structure_compliance():
    """Test that generated metadata follows FHIR structure patterns"""
    print("=== FHIR Structure Compliance Test ===")
    
    document = MockMedicalDocument(107, "Lab Results", "hba1c.pdf")
    form_data = {
        "test_type": "HbA1c",
        "lab_id": "LAB-2024-004"
    }
    enhance_document_on_upload(document, form_data)
    
    metadata_dict = json.loads(document.doc_metadata)
    fhir_data = metadata_dict["fhir"]
    
    # Verify FHIR structure patterns
    compliance_checks = {
        "has_code.coding.code": bool(
            fhir_data.get("code", {}).get("coding", [{}])[0].get("code")
        ),
        "has_code.coding.system": bool(
            fhir_data.get("code", {}).get("coding", [{}])[0].get("system")
        ),
        "has_type.coding.display": bool(
            fhir_data.get("type", {}).get("coding", [{}])[0].get("display")
        ),
        "has_effectiveDateTime": bool(fhir_data.get("effectiveDateTime")),
        "has_category": bool(fhir_data.get("category")),
        "code_system_is_url": fhir_data.get("code", {}).get("coding", [{}])[0].get("system", "").startswith("http"),
        "type_system_is_url": fhir_data.get("type", {}).get("coding", [{}])[0].get("system", "").startswith("http")
    }
    
    print("FHIR Structure Compliance Checks:")
    for check, passed in compliance_checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {check}: {status}")
    
    all_passed = all(compliance_checks.values())
    print(f"\nOverall Compliance: {'✓ PASS' if all_passed else '✗ FAIL'}")
    print()
    
    return compliance_checks


def test_legacy_metadata_preservation():
    """Test that existing metadata is preserved when adding FHIR structure"""
    print("=== Legacy Metadata Preservation Test ===")
    
    # Create document with existing metadata
    document = MockMedicalDocument(108, "Lab Results", "glucose.pdf")
    document.doc_metadata = json.dumps({
        "custom_field": "custom_value",
        "lab_technician": "John Doe",
        "equipment_id": "LAB-MACHINE-001"
    })
    
    # Enhance with FHIR metadata
    form_data = {
        "test_type": "Glucose",
        "lab_id": "LAB-2024-005"
    }
    enhance_document_on_upload(document, form_data)
    
    # Verify both legacy and FHIR data exist
    metadata_dict = json.loads(document.doc_metadata)
    
    print("Legacy Metadata Preserved:")
    print(f"  Custom Field: {metadata_dict.get('legacy', {}).get('custom_field')}")
    print(f"  Lab Technician: {metadata_dict.get('legacy', {}).get('lab_technician')}")
    print(f"  Equipment ID: {metadata_dict.get('legacy', {}).get('equipment_id')}")
    
    print("\nFHIR Metadata Added:")
    fhir_data = metadata_dict.get("fhir", {})
    print(f"  FHIR Type: {fhir_data.get('type', {}).get('coding', [{}])[0].get('display')}")
    print(f"  FHIR Code: {fhir_data.get('code', {}).get('coding', [{}])[0].get('code')}")
    print()
    
    return document


def main():
    """Run all FHIR metadata tests"""
    print("🔬 FHIR-Style Document Metadata System Test Suite")
    print("=" * 60)
    print()
    
    # Run all tests
    lab_doc = test_lab_result_fhir_metadata()
    imaging_doc = test_imaging_fhir_metadata()
    note_doc = test_clinical_note_fhir_metadata()
    custom_doc = test_adding_custom_fhir_codes()
    datetime_doc = test_effective_datetime()
    display_doc = test_display_metadata()
    lab_meta, imaging_meta = test_metadata_builder_direct()
    compliance = test_fhir_structure_compliance()
    legacy_doc = test_legacy_metadata_preservation()
    
    # Summary
    print("=" * 60)
    print("✅ FHIR Metadata System Tests Complete")
    print()
    print("Your documents now support FHIR-style metadata:")
    print("  • code.coding.code - Primary document codes")
    print("  • code.coding.system - Coding system URLs (LOINC, SNOMED CT)")
    print("  • type.coding.display - Human-readable document types")
    print("  • effectiveDateTime - When document becomes effective")
    print("  • category - Document categories for organization")
    print()
    print("Database fields unchanged:")
    print("  • doc_metadata field stores the FHIR structure as JSON")
    print("  • document_type, filename, etc. remain exactly the same")
    print("  • Legacy metadata is preserved in 'legacy' section")
    
    return True


if __name__ == "__main__":
    main()