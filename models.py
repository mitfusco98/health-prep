from datetime import datetime
import enum
import json
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Association table for many-to-many relationship between Screening and MedicalDocument
screening_documents = db.Table('screening_documents',
    db.Column('screening_id', db.Integer, db.ForeignKey('screening.id'), primary_key=True),
    db.Column('document_id', db.Integer, db.ForeignKey('medical_document.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    db.Column('confidence_score', db.Float, default=1.0),  # Matching confidence from 0.0 to 1.0
    db.Column('match_source', db.String(50), default='automated')  # 'automated', 'manual', 'ai_generated'
)


class DocumentType(enum.Enum):
    CLINICAL_NOTE = "Clinical Note"
    DISCHARGE_SUMMARY = "Discharge Summary"
    RADIOLOGY_REPORT = "Radiology Report"
    LAB_REPORT = "Lab Report"
    MEDICATION_LIST = "Medication List"
    REFERRAL = "Referral"
    CONSULTATION = "Consultation"
    OPERATIVE_REPORT = "Operative Report"
    PATHOLOGY_REPORT = "Pathology Report"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        # Use stronger hashing with higher iteration count and salt rounds
        self.password_hash = generate_password_hash(
            password, method="pbkdf2:sha256:600000", salt_length=32
        )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    sex = db.Column(db.String(10), nullable=False)  # 'Male', 'Female', 'Other'
    mrn = db.Column(db.String(20), unique=True, nullable=False)  # Medical Record Number
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))
    insurance = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    conditions = db.relationship("Condition", backref="patient", lazy=True)
    immunizations = db.relationship("Immunization", backref="patient", lazy=True)
    vitals = db.relationship("Vital", backref="patient", lazy=True)
    visits = db.relationship("Visit", backref="patient", lazy=True)
    lab_results = db.relationship("LabResult", backref="patient", lazy=True)
    imaging_studies = db.relationship("ImagingStudy", backref="patient", lazy=True)
    consult_reports = db.relationship("ConsultReport", backref="patient", lazy=True)
    hospital_summaries = db.relationship(
        "HospitalSummary", backref="patient", lazy=True
    )
    # Screening relationship is handled in Screening model
    documents = db.relationship("MedicalDocument", backref="patient", lazy=True)
    # Note: The 'appointments' relationship is defined in the Appointment model with a backref

    @property
    def age(self):
        today = datetime.now().date()
        born = self.date_of_birth
        return (
            today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def update_demographics(self, form_data):
        """
        Update patient demographics from form data
        This centralized method ensures all demographics are updated in one place

        Args:
            form_data: Form data containing patient demographic information
        """
        # Update basic information
        self.first_name = form_data.first_name.data
        self.last_name = form_data.last_name.data
        self.date_of_birth = form_data.date_of_birth.data
        self.sex = form_data.sex.data
        self.mrn = form_data.mrn.data
        self.phone = form_data.phone.data
        self.email = form_data.email.data
        self.address = form_data.address.data
        self.insurance = form_data.insurance.data

        # The updated_at column will be automatically updated via SQLAlchemy's onupdate parameter

    def __repr__(self):
        return f"<Patient {self.full_name} (MRN: {self.mrn})>"


class Condition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))  # ICD-10 or other coding system
    diagnosed_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Condition {self.name} for Patient {self.patient_id}>"


class Immunization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    vaccine_name = db.Column(db.String(100), nullable=False)
    administration_date = db.Column(db.Date, nullable=False)
    dose_number = db.Column(db.Integer)
    manufacturer = db.Column(db.String(100))
    lot_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Immunization {self.vaccine_name} for Patient {self.patient_id}>"


class Vital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    weight = db.Column(db.Float)  # kg
    height = db.Column(db.Float)  # cm
    bmi = db.Column(db.Float)
    temperature = db.Column(db.Float)  # °C
    blood_pressure_systolic = db.Column(db.Integer)
    blood_pressure_diastolic = db.Column(db.Integer)
    pulse = db.Column(db.Integer)  # bpm
    respiratory_rate = db.Column(db.Integer)  # breaths per minute
    oxygen_saturation = db.Column(db.Float)  # %
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Vital for Patient {self.patient_id} on {self.date}>"


class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    visit_date = db.Column(db.DateTime, nullable=False)
    visit_type = db.Column(
        db.String(50)
    )  # e.g., 'Annual Physical', 'Follow-up', 'Urgent'
    provider = db.Column(db.String(100))
    reason = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Visit for Patient {self.patient_id} on {self.visit_date}>"


class LabResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    test_name = db.Column(db.String(100), nullable=False)
    test_date = db.Column(db.DateTime, nullable=False)
    result_value = db.Column(db.String(100))
    unit = db.Column(db.String(20))
    reference_range = db.Column(db.String(50))
    is_abnormal = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LabResult {self.test_name} for Patient {self.patient_id}>"


class ImagingStudy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    study_type = db.Column(db.String(100), nullable=False)  # e.g., 'X-Ray', 'MRI', 'CT'
    body_site = db.Column(db.String(100))
    study_date = db.Column(db.DateTime, nullable=False)
    findings = db.Column(db.Text)
    impression = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ImagingStudy {self.study_type} for Patient {self.patient_id}>"


class ConsultReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    specialist = db.Column(db.String(100))
    specialty = db.Column(db.String(100))  # e.g., 'Cardiology', 'Neurology'
    report_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200))
    findings = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ConsultReport from {self.specialist} for Patient {self.patient_id}>"


class HospitalSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    admission_date = db.Column(db.DateTime, nullable=False)
    discharge_date = db.Column(db.DateTime)
    hospital_name = db.Column(db.String(100))
    admitting_diagnosis = db.Column(db.String(200))
    discharge_diagnosis = db.Column(db.String(200))
    procedures = db.Column(db.Text)
    discharge_medications = db.Column(db.Text)
    followup_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<HospitalSummary for Patient {self.patient_id} on {self.admission_date}>"
        )


# ScreeningType model is defined at the bottom of the file to avoid circular imports


class Screening(db.Model):
    """Individual screening assignments for specific patients with automated status determination"""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    
    # Enhanced schema with FK and visibility support
    screening_type = db.Column(
        db.String(100), nullable=False
    )  # Primary screening type reference
    screening_type_id = db.Column(db.Integer, db.ForeignKey("screening_type.id"))  # FK relationship
    
    due_date = db.Column(db.Date)
    last_completed = db.Column(db.Date)
    frequency = db.Column(db.String(50))  # e.g., 'Annual', 'Every 5 years'
    status = db.Column(db.String(20), default='Incomplete')  # 'Due', 'Due Soon', 'Incomplete', 'Complete'
    notes = db.Column(db.Text)  # Keep for backward compatibility and general notes
    
    # Enhanced columns for data preservation system
    is_visible = db.Column(db.Boolean, default=True)  # Controls visibility instead of deletion
    is_system_generated = db.Column(db.Boolean, default=True)  # Track if auto-generated
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    patient = db.relationship("Patient", backref=db.backref("screenings", lazy=True))
    documents = db.relationship("MedicalDocument", 
                               secondary=screening_documents,
                               backref=db.backref("screenings", lazy=True),
                               lazy="dynamic")

    @property
    def matched_documents(self):
        """Get list of matched documents for this screening, filtering out deleted ones"""
        try:
            # Get all documents and filter out any that no longer exist
            valid_documents = []
            for doc in self.documents.all():
                if doc and hasattr(doc, 'id') and doc.id:
                    valid_documents.append(doc)
                else:
                    # Remove orphaned relationship
                    self._cleanup_orphaned_document_relationship(doc)
            return valid_documents
        except Exception as e:
            print(f"Error retrieving matched documents for screening {self.id}: {e}")
            return []

    @property
    def document_count(self):
        """Get count of valid matched documents"""
        return len(self.matched_documents)

    def get_valid_documents_with_access_check(self, user=None):
        """Get documents with access permission validation"""
        valid_documents = []
        for doc in self.matched_documents:
            try:
                # Check if document exists and is accessible
                if self._validate_document_access(doc, user):
                    valid_documents.append(doc)
            except Exception as e:
                print(f"Error validating document access for doc {doc.id}: {e}")
                continue
        return valid_documents

    def _validate_document_access(self, document, user=None):
        """Validate that a document exists and user has access"""
        try:
            # Check if document exists in database
            from app import db
            existing_doc = db.session.get(MedicalDocument, document.id)
            if not existing_doc:
                # Clean up orphaned relationship
                self._cleanup_orphaned_document_relationship(document)
                return False
            
            # For now, basic access check (can be enhanced with role-based permissions)
            # TODO: Add role-based access control based on user permissions
            return True
            
        except Exception as e:
            print(f"Error validating document access: {e}")
            return False

    def _cleanup_orphaned_document_relationship(self, document):
        """Remove orphaned document relationship"""
        try:
            if document in self.documents:
                self.documents.remove(document)
                db.session.flush()
                print(f"Cleaned up orphaned document relationship: screening {self.id}, document {document.id}")
        except Exception as e:
            print(f"Error cleaning up orphaned relationship: {e}")

    def validate_and_cleanup_document_relationships(self):
        """Validate all document relationships and clean up orphaned ones"""
        try:
            orphaned_count = 0
            for doc in list(self.documents.all()):  # Create a copy to avoid iteration issues
                try:
                    # Try to access the document's attributes
                    _ = doc.id, doc.filename
                    # Check if document still exists in database
                    from app import db
                    if not db.session.get(MedicalDocument, doc.id):
                        self._cleanup_orphaned_document_relationship(doc)
                        orphaned_count += 1
                except Exception:
                    self._cleanup_orphaned_document_relationship(doc)
                    orphaned_count += 1
            
            if orphaned_count > 0:
                db.session.commit()
                print(f"Cleaned up {orphaned_count} orphaned document relationships for screening {self.id}")
                
            return orphaned_count
        except Exception as e:
            print(f"Error during document relationship validation: {e}")
            return 0

    def get_document_confidence(self, document_id):
        """Get confidence score for a specific document relationship"""
        try:
            from sqlalchemy import text
            result = db.session.execute(
                text("SELECT confidence_score FROM screening_documents "
                     "WHERE screening_id = :screening_id AND document_id = :document_id"),
                {'screening_id': self.id, 'document_id': document_id}
            ).fetchone()
            return result[0] if result else 0.8  # Default confidence
        except Exception as e:
            print(f"Error getting document confidence: {e}")
            return 0.8  # Default confidence
    
    def add_document(self, document, confidence_score=1.0, match_source='automated', batch_mode=False):
        """Add a document to this screening with metadata"""
        try:
            # Check if document is already linked to avoid duplicates
            if document not in self.documents:
                # Use no_autoflush to prevent session conflicts during relationship changes
                with db.session.no_autoflush:
                    # Add document to the many-to-many relationship
                    self.documents.append(document)
                
                # Only flush if not in batch mode - batch mode will commit all at once
                if not batch_mode:
                    db.session.flush()
                
                # Store metadata for later update if in batch mode
                if batch_mode:
                    # Store for batch processing
                    if not hasattr(self, '_pending_document_metadata'):
                        self._pending_document_metadata = []
                    self._pending_document_metadata.append({
                        'document_id': document.id,
                        'confidence_score': confidence_score,
                        'match_source': match_source
                    })
                else:
                    # Update the association table with metadata immediately
                    try:
                        from sqlalchemy import text
                        db.session.execute(
                            text("UPDATE screening_documents SET confidence_score = :score, match_source = :source "
                                 "WHERE screening_id = :screening_id AND document_id = :document_id"),
                            {
                                'score': confidence_score,
                                'source': match_source,
                                'screening_id': self.id,
                                'document_id': document.id
                            }
                        )
                    except Exception as e:
                        # If metadata update fails, still keep the relationship
                        print(f"Warning: Could not update document metadata: {e}")
                        pass
        except Exception as e:
            print(f"Error adding document {document.id} to screening {self.id}: {e}")
            raise
    
    def process_pending_document_metadata(self):
        """Process any pending document metadata updates from batch operations"""
        if hasattr(self, '_pending_document_metadata') and self._pending_document_metadata:
            try:
                from sqlalchemy import text
                for metadata in self._pending_document_metadata:
                    db.session.execute(
                        text("UPDATE screening_documents SET confidence_score = :score, match_source = :source "
                             "WHERE screening_id = :screening_id AND document_id = :document_id"),
                        {
                            'score': metadata['confidence_score'],
                            'source': metadata['match_source'],
                            'screening_id': self.id,
                            'document_id': metadata['document_id']
                        }
                    )
                # Clear the pending metadata
                self._pending_document_metadata = []
            except Exception as e:
                print(f"Warning: Could not update batch document metadata: {e}")
                pass

    def remove_document(self, document):
        """Remove a document from this screening"""
        try:
            # Use direct SQL to avoid session conflicts during bulk operations
            from sqlalchemy import text
            result = db.session.execute(
                text("DELETE FROM screening_documents WHERE screening_id = :screening_id AND document_id = :document_id"),
                {'screening_id': self.id, 'document_id': document.id}
            )
            if result.rowcount > 0:
                print(f"  → Removed document {document.id} from screening {self.id}")
        except Exception as e:
            print(f"Error removing document {document.id} from screening {self.id}: {e}")
            # Try ORM method as fallback
            try:
                with db.session.no_autoflush:
                    # Check if document is actually in the relationship
                    existing_docs = list(self.documents.all())
                    if document in existing_docs:
                        self.documents.remove(document)
            except Exception as orm_error:
                print(f"ORM removal also failed: {orm_error}")

    def get_document_metadata(self, document):
        """Get metadata for a specific document relationship"""
        from sqlalchemy import text
        result = db.session.execute(
            text("SELECT confidence_score, match_source, created_at FROM screening_documents "
                 "WHERE screening_id = :screening_id AND document_id = :document_id"),
            {'screening_id': self.id, 'document_id': document.id}
        ).fetchone()
        
        if result:
            return {
                'confidence_score': result[0],
                'match_source': result[1],
                'created_at': result[2]
            }
        return None

    def __repr__(self):
        return f"<Screening {self.screening_type} for Patient {self.patient_id} - {self.status}>"


class MedicalDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    filename = db.Column(db.String(255))
    document_name = db.Column(db.String(255))  # Descriptive name for the document
    document_type = db.Column(
        db.String(50)
    )  # Stores the string value of DocumentType enum
    content = db.Column(
        db.Text, nullable=True
    )  # Text content (nullable to allow binary-only files)
    binary_content = db.Column(
        db.LargeBinary, nullable=True
    )  # Binary content for images
    is_binary = db.Column(db.Boolean, default=False)  # Flag to indicate binary content
    mime_type = db.Column(db.String(100), nullable=True)  # MIME type for binary content
    source_system = db.Column(db.String(100))  # EMR system name or source
    document_date = db.Column(db.DateTime)
    provider = db.Column(db.String(100))
    doc_metadata = db.Column(db.Text)  # JSON string with additional metadata
    is_processed = db.Column(db.Boolean, default=False)
    
    # OCR processing status tracking
    ocr_processed = db.Column(db.Boolean, default=False)
    ocr_confidence = db.Column(db.Float)  # OCR confidence score 0-100
    ocr_processing_date = db.Column(db.DateTime)
    ocr_text_length = db.Column(db.Integer)
    ocr_quality_flags = db.Column(db.Text)  # JSON array of quality flags
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship with Patient is already defined in the Patient model
    # Note: screenings relationship is defined in the Screening model via the association table

    @property
    def matched_screenings(self):
        """Get list of screenings that reference this document"""
        return self.screenings

    @property 
    def screening_count(self):
        """Get count of screenings that reference this document"""
        return len(self.screenings)

    def extract_fhir_metadata(self):
        """Extract FHIR-compatible metadata from document using existing doc_metadata field"""
        if not self.doc_metadata:
            return {}

        try:
            metadata = json.loads(self.doc_metadata)
            fhir_data = {}

            # Extract FHIR codes if available
            if 'fhir_primary_code' in metadata:
                fhir_data = metadata['fhir_primary_code']

            # Map document type to FHIR if no existing FHIR data
            if not fhir_data and self.document_type:
                fhir_data = self._map_document_type_to_fhir()

            return fhir_data

        except (json.JSONDecodeError, KeyError):
            return self._map_document_type_to_fhir()

    def _map_document_type_to_fhir(self):
        """Map document type to FHIR coding for Epic compatibility"""
        type_mappings = {
            'Lab Report': {
                'code': {
                    'coding': [{
                        'system': 'http://loinc.org',
                        'code': '11502-2',
                        'display': 'Laboratory report'
                    }]
                },
                'category': [{
                    'coding': [{
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'laboratory',
                        'display': 'Laboratory'
                    }]
                }]
            },
            'Radiology Report': {
                'code': {
                    'coding': [{
                        'system': 'http://loinc.org',
                        'code': '18748-4',
                        'display': 'Diagnostic imaging study'
                    }]
                },
                'category': [{
                    'coding': [{
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'imaging',
                        'display': 'Imaging'
                    }]
                }]
            },
            'Clinical Note': {
                'code': {
                    'coding': [{
                        'system': 'http://loinc.org',
                        'code': '11506-3',
                        'display': 'Progress note'
                    }]
                },
                'category': [{
                    'coding': [{
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'exam',
                        'display': 'Exam'
                    }]
                }]
            },
            'Discharge Summary': {
                'code': {
                    'coding': [{
                        'system': 'http://loinc.org',
                        'code': '18842-5',
                        'display': 'Discharge summary'
                    }]
                },
                'category': [{
                    'coding': [{
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': 'exam',
                        'display': 'Exam'
                    }]
                }]
            }
        }

        return type_mappings.get(self.document_type, {
            'code': {
                'coding': [{
                    'system': 'http://loinc.org',
                    'code': '34133-9',
                    'display': 'Summarization of episode note'
                }]
            },
            'category': [{
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                    'code': 'exam',
                    'display': 'Exam'
                }]
            }]
        })

    def __repr__(self):
        display_name = self.document_name if self.document_name else self.filename
        return f'<MedicalDocument "{display_name}" ({self.document_type}) for Patient {self.patient_id}>'


class PrepSheet(db.Model):
    """Preparation sheet documents with dual storage for internal and FHIR keys"""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))  # Path to generated file
    content = db.Column(db.Text)  # Generated prep sheet content
    prep_data = db.Column(db.Text)  # JSON of prep sheet data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # === DUAL STORAGE: Internal + FHIR Keys ===
    # Internal keys (for backward compatibility)
    tag = db.Column(db.String(100))  # Internal prep sheet tag
    section = db.Column(db.String(100))  # Prep sheet section classification
    matched_screening = db.Column(db.String(100))  # Associated screening types

    # FHIR-style keys (for Epic/FHIR exports)
    fhir_code_system = db.Column(db.String(255))  # e.g., "http://loinc.org"
    fhir_code_code = db.Column(db.String(50))  # e.g., "75492-9" (code.coding.code)
    fhir_code_display = db.Column(db.String(255))  # e.g., "Preventive care note"
    fhir_category_system = db.Column(db.String(255))  # e.g., "http://terminology.hl7.org/CodeSystem/observation-category"
    fhir_category_code = db.Column(db.String(50))  # e.g., "survey" (category)
    fhir_category_display = db.Column(db.String(255))  # e.g., "Survey"
    fhir_effective_datetime = db.Column(db.DateTime)  # effectiveDateTime for FHIR

    # Relationship
    patient = db.relationship("Patient", backref=db.backref("prep_sheets", lazy=True))

    def set_dual_storage_keys(self, internal_data=None, fhir_data=None):
        """
        Set both internal and FHIR keys for dual storage compatibility

        Args:
            internal_data: Dict with keys like {'tag': 'prep', 'section': 'preventive', 'matched_screening': 'annual'}
            fhir_data: Dict with FHIR coding structure
        """
        # Set internal keys
        if internal_data:
            self.tag = internal_data.get('tag')
            self.section = internal_data.get('section')
            self.matched_screening = internal_data.get('matched_screening')

        # Set FHIR keys
        if fhir_data:
            if 'code' in fhir_data and fhir_data['code']:
                self.fhir_code_system = fhir_data['code'].get('system')
                self.fhir_code_code = fhir_data['code'].get('code')
                self.fhir_code_display = fhir_data['code'].get('display')

            if 'category' in fhir_data and fhir_data['category']:
                self.fhir_category_system = fhir_data['category'].get('system')
                self.fhir_category_code = fhir_data['category'].get('code')
                self.fhir_category_display = fhir_data['category'].get('display')

            if 'effectiveDateTime' in fhir_data:
                self.fhir_effective_datetime = fhir_data['effectiveDateTime']

    def get_internal_keys(self):
        """Get internal keys as dictionary"""
        return {
            'tag': self.tag,
            'section': self.section,
            'matched_screening': self.matched_screening
        }

    def get_fhir_keys(self):
        """Get FHIR keys as structured dictionary"""
        return {
            'code': {
                'system': self.fhir_code_system,
                'code': self.fhir_code_code,
                'display': self.fhir_code_display
            } if self.fhir_code_code else None,
            'category': {
                'system': self.fhir_category_system,
                'code': self.fhir_category_code,
                'display': self.fhir_category_display
            } if self.fhir_category_code else None,
            'effectiveDateTime': self.fhir_effective_datetime
        }

    def __repr__(self):
        return f'<PrepSheet "{self.filename}" for Patient {self.patient_id} on {self.appointment_date}>'


class EHRConnection(db.Model):
    """Configuration for an external EHR system connection"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    vendor = db.Column(db.String(50), nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    auth_type = db.Column(db.String(20), nullable=False)  # 'none', 'api_key', 'oauth'
    api_key = db.Column(db.String(255))
    client_id = db.Column(db.String(255))
    client_secret = db.Column(db.String(255))
    use_auth_header = db.Column(db.Boolean, default=True)
    additional_config = db.Column(db.Text)  # JSON string with any extra configuration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    import_history = db.relationship(
        "EHRImportHistory", backref="connection", lazy=True
    )

    def __repr__(self):
        return f"<EHRConnection {self.name} ({self.vendor})>"

    @property
    def config_dict(self):
        """Return connection configuration as a dictionary"""
        config = {
            "name": self.name,
            "vendor": self.vendor,
            "base_url": self.base_url,
            "auth_type": self.auth_type,
            "use_auth_header": self.use_auth_header,
        }

        if self.auth_type == "api_key" and self.api_key:
            config["api_key"] = self.api_key
        elif self.auth_type == "oauth":
            config["client_id"] = self.client_id
            config["client_secret"] = self.client_secret

        if self.additional_config:
            try:
                additional = json.loads(self.additional_config)
                config.update(additional)
            except json.JSONDecodeError:
                pass

        return config


class EHRImportHistory(db.Model):
    """Record of data imports from EHR systems"""

    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(
        db.Integer, db.ForeignKey("ehr_connection.id"), nullable=False
    )
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"))
    patient_name = db.Column(db.String(200))  # In case the patient wasn't imported
    ehr_patient_id = db.Column(db.String(100))  # ID in the external EHR system
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    imported_data_types = db.Column(
        db.String(255)
    )  # Comma-separated list: 'patient,conditions,vitals,documents'
    imported_items = db.Column(db.Integer, default=0)  # Count of items imported
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)

    def __repr__(self):
        return f'<EHRImportHistory {self.id} for {self.patient_name or "Unknown"} from {self.connection.name if self.connection else "Unknown"}>'


class Appointment(db.Model):
    """Daily appointment schedule for patients"""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    note = db.Column(db.String(200))
    status = db.Column(
        db.String(20), default="OOO"
    )  # Options: 'OOO', 'waiting', 'provider', 'seen'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    patient = db.relationship("Patient", backref=db.backref("appointments", lazy=True))

    @property
    def date_time(self):
        """Return a datetime object combining the date and time"""
        from datetime import datetime as dt

        return dt.combine(self.appointment_date, self.appointment_time)

    def __repr__(self):
        return f"<Appointment for {self.patient.full_name} on {self.appointment_date} at {self.appointment_time}>"


class ScreeningType(db.Model):
    """Defines screening types that can be assigned to patients"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    default_frequency = db.Column(db.String(50))  # e.g., "Annual", "Every 3 years" - kept for backward compatibility
    frequency_number = db.Column(db.Integer)  # e.g., 1, 3, 6
    frequency_unit = db.Column(db.String(20))  # e.g., "days", "weeks", "months", "years"
    gender_specific = db.Column(db.String(10))  # "Male" or "Female" or None for all
    min_age = db.Column(
        db.Integer
    )  # Minimum age for this screening, null if no minimum
    max_age = db.Column(
        db.Integer
    )  # Maximum age for this screening, null if no maximum
    is_active = db.Column(db.Boolean, default=True)

    # === FHIR TRIGGER CONDITIONS ===
    trigger_conditions = db.Column(db.Text)  # JSON array of condition codes that trigger this screening

    # === DOCUMENT SECTION MAPPINGS ===
    document_section_mappings = db.Column(db.Text)  # JSON mapping of document sections to FHIR categories

    # === KEYWORD FIELDS FOR DYNAMIC PARSING ===
    content_keywords = db.Column(db.Text)  # JSON array of keywords for content parsing
    document_keywords = db.Column(db.Text)  # JSON array of keywords for document type parsing
    filename_keywords = db.Column(db.Text)  # JSON array of keywords for filename parsing
    status = db.Column(db.String(20), default='active')  # Status field (active, inactive, draft)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Don't specify a relationship here since the original Screening table doesn't have a foreign key

    def set_trigger_conditions(self, conditions_list):
        """
        Set trigger conditions as JSON array

        Args:
            conditions_list: List of condition codes like [
                {
                    "system": "http://snomed.info/sct",
                    "code": "73211009",
                    "display": "Diabetes mellitus"
                },
                {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "E11.9",
                    "display": "Type 2 diabetes mellitus without complications"
                }
            ]
        """
        if conditions_list:
            import json
            self.trigger_conditions = json.dumps(conditions_list)
        else:
            self.trigger_conditions = None

    def get_trigger_conditions(self):
        """Get trigger conditions as list of dictionaries
        FIXED: Handle HTML entities in JSON trigger conditions field"""
        if not self.trigger_conditions:
            return []

        try:
            import json
            import html
            # FIXED: Handle HTML entities like &quot; in JSON data
            clean_trigger_json = html.unescape(self.trigger_conditions)
            return json.loads(clean_trigger_json)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"⚠️ Warning: Invalid JSON in trigger conditions field for {self.name}: {e}")
            return []

    def matches_condition_code(self, condition_code, code_system=None):
        """
        Check if a condition code matches any of the trigger conditions

        Args:
            condition_code: The code to check (e.g., "73211009", "E11.9")
            code_system: Optional system URL to match against

        Returns:
            bool: True if condition matches any trigger condition
        """
        trigger_conditions = self.get_trigger_conditions()


    @property
    def formatted_frequency(self):
        """Return a formatted frequency string from structured fields, blank if not set"""
        if self.frequency_number and self.frequency_unit:
            if self.frequency_number == 1:
                # Handle singular forms
                unit_singular = {
                    'days': 'day',
                    'weeks': 'week', 
                    'months': 'month',                    'years': 'year'
                }
                return f"Every {unit_singular.get(self.frequency_unit, self.frequency_unit)}"
            else:
                return f"Every {self.frequency_number} {self.frequency_unit}"
        else:
            return ""

    @property
    def frequency_in_days(self):
        """Convert structured frequency to approximate days for calculations"""
        if not self.frequency_number or not self.frequency_unit:
            return None

        multipliers = {
            'days': 1,
            'weeks': 7,
            'months': 30,  # Approximate
            'years': 365   # Approximate
        }

        multiplier = multipliers.get(self.frequency_unit)
        if multiplier:
            return self.frequency_number * multiplier
        return None

    def set_content_keywords(self, keywords_list):
        """
        Set unified keywords as JSON array (used for both content and filename matching)

        Args:
            keywords_list: List of keywords for content and filename parsing like ["mammogram", "breast", "screening"]
        """
        if keywords_list:
            self.content_keywords = json.dumps(keywords_list)
        else:
            self.content_keywords = None

    def get_content_keywords(self):
        """Get unified keywords as list (used for both content and filename matching)"""
        if not self.content_keywords:
            return []

        try:
            return json.loads(self.content_keywords)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_document_keywords(self, keywords_list):
        """
        Set document section keywords as JSON array

        Args:
            keywords_list: List of keywords for document type parsing like ["radiology", "lab", "pathology"]
        """
        if keywords_list:
            self.document_keywords = json.dumps(keywords_list)
        else:
            self.document_keywords = None

    def get_document_keywords(self):
        """Get document section keywords as list"""
        if not self.document_keywords:
            return []

        try:
            return json.loads(self.document_keywords)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_filename_keywords(self, keywords_list):
        """
        Legacy method - now redirects to set_content_keywords for unified approach

        Args:
            keywords_list: List of keywords for filename parsing like ["mammo", "xray", "ct"]
        """
        # For backward compatibility, merge with existing content keywords
        existing_keywords = self.get_content_keywords()
        if keywords_list:
            all_keywords = list(set(existing_keywords + keywords_list))
            self.set_content_keywords(all_keywords)

    def get_filename_keywords(self):
        """Legacy method - now returns content keywords for unified approach"""
        return self.get_content_keywords()

    def get_all_keywords(self):
        """Get all keywords combined for comprehensive parsing"""
        all_keywords = []
        all_keywords.extend(self.get_content_keywords())  # This now includes both content and filename keywords
        all_keywords.extend(self.get_document_keywords())
        return list(set(all_keywords))  # Remove duplicates

    def matches_keywords(self, text, keyword_type='all'):
        """
        Check if text matches any keywords of specified type

        Args:
            text: Text to search in
            keyword_type: 'content', 'document', 'filename', or 'all'

        Returns:
            bool: True if any keywords match
        """
        if not text:
            return False

        text_lower = text.lower()

        if keyword_type == 'content' or keyword_type == 'filename':
            # Both content and filename now use the same unified keywords
            keywords = self.get_content_keywords()
        elif keyword_type == 'document':
            keywords = self.get_document_keywords()
        else:  # 'all'
            keywords = self.get_all_keywords()

        return any(keyword.lower() in text_lower for keyword in keywords)

    def set_document_section_mappings(self, mappings_dict):
        """
        Set document section to FHIR category mappings

        Args:
            mappings_dict: Dictionary mapping document sections to FHIR categories like {
                "labs": {
                    "fhir_category": {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory"
                    }
                },
                "imaging": {
                    "fhir_category": {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category", 
                        "code": "imaging",
                        "display": "Imaging"
                    }
                },
                "consults": {
                    "fhir_category": {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "exam", 
                        "display": "Exam"
                    }
                }
            }
        """
        if mappings_dict:
            import json
            self.document_section_mappings = json.dumps(mappings_dict)
        else:
            self.document_section_mappings = None

    def get_document_section_mappings(self):
        """Get document section mappings as dictionary"""
        if not self.document_section_mappings:
            return {}

        try:
            import json
            return json.loads(self.document_section_mappings)
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_fhir_category_for_section(self, section_name):
        """
        Get FHIR category for a document section

        Args:
            section_name: Name of the document section (e.g., "labs", "imaging")

        Returns:
            dict: FHIR category structure or None if not mapped
        """
        mappings = self.get_document_section_mappings()
        section_mapping = mappings.get(section_name.lower())

        if section_mapping and 'fhir_category' in section_mapping:
            return section_mapping['fhir_category']

        return None

    def matches_document_section(self, document_section, document_type=None):
        """
        Check if a document section matches this screening type's criteria

        Args:
            document_section: The document section to check
            document_type: Optional document type for additional context

        Returns:
            bool: True if document section matches screening criteria
        """
        mappings = self.get_document_section_mappings()

        if not mappings:
            return False

        # Direct section match
        if document_section.lower() in mappings:
            return True

        # Check for document type mapping
        if document_type:
            for section, config in mappings.items():
                if 'document_types' in config:
                    if document_type.lower() in [dt.lower() for dt in config['document_types']]:
                        return True

        return False

    def __repr__(self):
        return f"<ScreeningType {self.name}>"


class PatientAlert(db.Model):
    """Patient-specific alerts that appear on prep sheets"""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    alert_type = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'Allergy', 'Clinical', 'Administrative'
    description = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    start_date = db.Column(db.Date, default=datetime.utcnow().date)
    end_date = db.Column(db.Date, nullable=True)  # If null, alert is permanent
    is_active = db.Column(db.Boolean, default=True)
    severity = db.Column(db.String(20), default="Medium")  # 'High', 'Medium', 'Low'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    patient = db.relationship("Patient", backref=db.backref("alerts", lazy=True))

    def __repr__(self):
        return f"<PatientAlert {self.description} for Patient {self.patient_id}>"


class ChecklistSettings(db.Model):
    """Settings for the prep sheet quality checklist"""

    id = db.Column(db.Integer, primary_key=True)
    layout_style = db.Column(db.String(20), default="list")  # 'list' or 'table'
    show_notes = db.Column(db.Boolean, default=True)
    # Status options are now permanently fixed - no user customization
    # Always use: due, due_soon, incomplete, completed
    content_sources = db.Column(
        db.Text, default="database,age_based,gender_based,condition_based"
    )  # Comma-separated list
    default_items = db.Column(
        db.Text, nullable=True
    )  # Newline-separated list of default items

    # Time-based filtering settings
    labs_cutoff_months = db.Column(db.Integer, default=6)  # Exclude labs older than X months
    imaging_cutoff_months = db.Column(db.Integer, default=12)  # Exclude imaging older than X months  
    consults_cutoff_months = db.Column(db.Integer, default=12)  # Exclude consults older than X months
    hospital_cutoff_months = db.Column(db.Integer, default=24)  # Exclude hospital visits older than X months
    # Screening-specific cutoffs removed - conflicts with screening frequency settings
    # Cutoffs now only apply to: labs, imaging, consults, hospital
    
    # Confidence threshold settings for document matching
    confidence_high_threshold = db.Column(db.Float, default=0.8)  # High confidence threshold (green)
    confidence_medium_threshold = db.Column(db.Float, default=0.5)  # Medium confidence threshold (yellow)
    # Low confidence is anything below medium threshold (red) visits

    # General cutoff months for prep sheet items (overrides specific cutoffs if set)
    cutoff_months = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def status_options_list(self):
        """Return permanently fixed status options"""
        return ['due', 'due_soon', 'incomplete', 'completed']

    @property
    def default_items_list(self):
        """Return default_items string to list"""
        if self.default_items:
            return [item.strip() for item in self.default_items.split("\n") if item.strip()]

    @property
    def content_sources_list(self):
        """Return content sources as a list"""
        if self.content_sources:
            return [source.strip() for source in self.content_sources.split(",")]
        return []

    @property
    def custom_status_list(self):
        """Custom status options removed - return empty list"""
        return []

    # Screening-specific cutoff methods removed to prevent conflicts with screening frequency settings

    def get_cutoff_date(self, cutoff_months, base_date=None):
        """Convert months to a cutoff date from base_date (or today)"""
        from datetime import datetime, timedelta
        import calendar

        if base_date is None:
            base_date = datetime.now().date()
        elif isinstance(base_date, str):
            base_date = datetime.strptime(base_date, '%Y-%m-%d').date()
        elif isinstance(base_date, datetime):
            base_date = base_date.date()

        # Go back the specified number of months
        year = base_date.year
        month = base_date.month - cutoff_months

        while month <= 0:
            month += 12
            year -= 1

        # Handle day overflow (e.g., Jan 31 -> Feb 28)
        max_day = calendar.monthrange(year, month)[1]
        day = min(base_date.day, max_day)

        return datetime(year, month, day).date()

    def __repr__(self):
        return f"<ChecklistSettings id={self.id}>"


class AdminLog(db.Model):
    """Admin activity and system event logging"""

    __tablename__ = "admin_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    event_type = db.Column(
        db.String(50), nullable=False, index=True
    )  # login_fail, validation_error, admin_action, etc.
    event_details = db.Column(
        db.Text, nullable=True
    )  # JSON string with additional details
    request_id = db.Column(
        db.String(36), nullable=True, index=True
    )  # UUID for request tracking
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6 address
    user_agent = db.Column(db.String(500), nullable=True)

    # Relationship
    user = db.relationship("User", backref=db.backref("admin_logs", lazy=True))

    def __repr__(self):
        return f"<AdminLog {self.event_type} at {self.timestamp}>"

    @property
    def event_details_dict(self):
        """Return event details as a dictionary"""
        if not self.event_details:
            return {}
        try:
            # First try to parse as JSON
            import json

            return json.loads(self.event_details)
        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, try to evaluate as Python dict
            try:
                import ast

                return ast.literal_eval(self.event_details)
            except (ValueError, SyntaxError):
                # If both fail, try to extract basic info from string format
                try:
                    # Handle old string format like "{'route': '/path', 'method': 'GET'}"
                    if self.event_details.strip().startswith(
                        "{"
                    ) and self.event_details.strip().endswith("}"):
                        # Try to fix common formatting issues
                        fixed_details = self.event_details.replace("'", '"')
                        return json.loads(fixed_details)
                except:
                    pass
                # Return raw string in a dict if all else fails
                return {"raw": self.event_details, "parsed": False}

    @classmethod
    def log_event(
        cls,
        event_type,
        user_id=None,
        event_details=None,
        request_id=None,
        ip_address=None,
        user_agent=None,
    ):
        """
        Convenience method to create a new admin log entry

        Args:
            event_type: Type of event (required)
            user_id: ID of the user associated with the event
            event_details: Dictionary or string with event details
            request_id: Request tracking ID
            ip_address: IP address of the request
            user_agent: User agent string
        """
        if isinstance(event_details, dict):
            event_details = json.dumps(event_details)

        log_entry = cls(
            event_type=event_type,
            user_id=user_id,
            event_details=event_details,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        db.session.add(log_entry)
        return log_entry


class Keyword(db.Model):
    """Keywords for document and screening matching"""

    __tablename__ = "keywords"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Keyword {self.name}>"


class ScreeningKeyword(db.Model):
    """Many-to-many relationship between screening types and keywords"""

    __tablename__ = "screening_keywords"

    id = db.Column(db.Integer, primary_key=True)
    screening_id = db.Column(db.Integer, db.ForeignKey("screening_type.id"), nullable=False)
    keyword_id = db.Column(db.Integer, db.ForeignKey("keywords.id"), nullable=False)
    weight = db.Column(db.Float, default=1.0)
    section = db.Column(db.String(50))  # 'labs', 'imaging', 'consults', etc.
    case_sensitive = db.Column(db.Boolean, default=False)
    exact_match = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    screening_type = db.relationship("ScreeningType", backref=db.backref("keyword_associations", lazy=True))
    keyword = db.relationship("Keyword", backref=db.backref("screening_associations", lazy=True))

    def __repr__(self):
        return f"<ScreeningKeyword screening_id={self.screening_id} keyword_id={self.keyword_id}>"


class KeywordConfig(db.Model):
    """Configuration settings for keyword matching per screening type"""

    __tablename__ = "keyword_configs"

    id = db.Column(db.Integer, primary_key=True)
    screening_id = db.Column(db.Integer, db.ForeignKey("screening_type.id"), nullable=False, unique=True)
    config = db.Column(db.Text)  # JSON string with configuration data
    fallback_enabled = db.Column(db.Boolean, default=True)
    confidence_threshold = db.Column(db.Float, default=0.3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    screening_type = db.relationship("ScreeningType", backref=db.backref("keyword_config", uselist=False))

    def __repr__(self):
        return f"<KeywordConfig for screening_id={self.screening_id}>"

    @property
    def config_dict(self):
        """Return configuration as a dictionary"""
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_config(self, config_dict):
        """Set configuration from a dictionary"""
        if config_dict:
            self.config = json.dumps(config_dict)
        else:
            self.config = None