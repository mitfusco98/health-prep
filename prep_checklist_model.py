"""
PrepChecklist Model - Dynamic screening checklist system
Integrates screening types with keyword parsing for intelligent medical data matching
"""

from datetime import datetime, date
import json
import enum
from app import db
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship


class PrepChecklistSection(enum.Enum):
    """Sections that mirror the prep sheet structure"""
    PATIENT_INFO = "patient_info"
    ACTIVE_CONDITIONS = "active_conditions"
    VITAL_SIGNS = "vital_signs"
    SCREENING_CHECKLIST = "screening_checklist"
    LABORATORY_RESULTS = "laboratory_results"
    IMAGING_STUDIES = "imaging_studies"
    CONSULTS_REFERRALS = "consults_referrals"
    HOSPITAL_VISITS = "hospital_visits"
    IMMUNIZATIONS = "immunizations"
    PROVIDER_NOTES = "provider_notes"


class PrepChecklistItemType(enum.Enum):
    """Types of checklist items"""
    SCREENING_TYPE = "screening_type"           # Links to ScreeningType
    KEYWORD_MATCH = "keyword_match"             # Uses keywords to match data
    CONDITION_TRIGGERED = "condition_triggered" # Triggered by patient conditions
    AGE_GENDER_RULE = "age_gender_rule"        # Based on demographics
    CUSTOM_ITEM = "custom_item"                 # User-defined static item


class PrepChecklistMatchStatus(enum.Enum):
    """Status of data matching for checklist items"""
    NOT_CHECKED = "not_checked"
    FOUND = "found"
    NOT_FOUND = "not_found"
    PARTIALLY_FOUND = "partially_found"
    NEEDS_REVIEW = "needs_review"


class PrepChecklistTemplate(db.Model):
    """Master template for prep checklist configuration"""
    __tablename__ = 'prep_checklist_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    checklist_items = relationship("PrepChecklistItem", back_populates="template", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PrepChecklistTemplate {self.name}>"


class PrepChecklistItem(db.Model):
    """Individual items in the prep checklist with intelligent matching rules"""
    __tablename__ = 'prep_checklist_items'
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('prep_checklist_templates.id'), nullable=False)
    
    # Basic item configuration
    section = Column(SQLEnum(PrepChecklistSection), nullable=False)
    item_type = Column(SQLEnum(PrepChecklistItemType), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, default=0)
    is_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Screening type reference (for SCREENING_TYPE items)
    screening_type_id = Column(Integer, ForeignKey('screening_types.id'), nullable=True)
    
    # Keyword matching configuration
    primary_keywords = Column(Text)  # JSON array of primary keywords
    secondary_keywords = Column(Text)  # JSON array of secondary keywords
    excluded_keywords = Column(Text)  # JSON array of keywords to exclude
    
    # Age and gender rules
    min_age = Column(Integer)
    max_age = Column(Integer)
    gender_specific = Column(String(20))  # 'Male', 'Female', or None for all
    
    # Condition triggers
    trigger_conditions = Column(Text)  # JSON array of condition names/codes
    
    # Matching configuration
    match_confidence_threshold = Column(Integer, default=70)  # 0-100
    require_recent_data = Column(Boolean, default=True)
    recent_data_days = Column(Integer, default=365)
    
    # Display configuration
    show_in_summary = Column(Boolean, default=True)
    priority_level = Column(Integer, default=1)  # 1=High, 2=Medium, 3=Low
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    template = relationship("PrepChecklistTemplate", back_populates="checklist_items")
    screening_type = relationship("ScreeningType", foreign_keys=[screening_type_id])
    
    @property
    def primary_keywords_list(self):
        """Get primary keywords as a list"""
        if not self.primary_keywords:
            return []
        try:
            return json.loads(self.primary_keywords)
        except:
            return []
    
    @primary_keywords_list.setter
    def primary_keywords_list(self, keywords):
        """Set primary keywords from a list"""
        self.primary_keywords = json.dumps(keywords) if keywords else None
    
    @property
    def secondary_keywords_list(self):
        """Get secondary keywords as a list"""
        if not self.secondary_keywords:
            return []
        try:
            return json.loads(self.secondary_keywords)
        except:
            return []
    
    @secondary_keywords_list.setter
    def secondary_keywords_list(self, keywords):
        """Set secondary keywords from a list"""
        self.secondary_keywords = json.dumps(keywords) if keywords else None
    
    @property
    def excluded_keywords_list(self):
        """Get excluded keywords as a list"""
        if not self.excluded_keywords:
            return []
        try:
            return json.loads(self.excluded_keywords)
        except:
            return []
    
    @excluded_keywords_list.setter
    def excluded_keywords_list(self, keywords):
        """Set excluded keywords from a list"""
        self.excluded_keywords = json.dumps(keywords) if keywords else None
    
    @property
    def trigger_conditions_list(self):
        """Get trigger conditions as a list"""
        if not self.trigger_conditions:
            return []
        try:
            return json.loads(self.trigger_conditions)
        except:
            return []
    
    @trigger_conditions_list.setter
    def trigger_conditions_list(self, conditions):
        """Set trigger conditions from a list"""
        self.trigger_conditions = json.dumps(conditions) if conditions else None
    
    def applies_to_patient(self, patient):
        """Check if this checklist item applies to the given patient"""
        # Check age requirements
        if self.min_age and patient.age < self.min_age:
            return False
        if self.max_age and patient.age > self.max_age:
            return False
        
        # Check gender requirements
        if self.gender_specific and patient.sex.lower() != self.gender_specific.lower():
            return False
        
        return True
    
    def __repr__(self):
        return f"<PrepChecklistItem {self.title}>"


class PrepChecklistResult(db.Model):
    """Results of checklist evaluation for a specific patient/date"""
    __tablename__ = 'prep_checklist_results'
    
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    template_id = Column(Integer, ForeignKey('prep_checklist_templates.id'), nullable=False)
    checklist_item_id = Column(Integer, ForeignKey('prep_checklist_items.id'), nullable=False)
    
    # Evaluation results
    match_status = Column(SQLEnum(PrepChecklistMatchStatus), default=PrepChecklistMatchStatus.NOT_CHECKED)
    confidence_score = Column(Integer, default=0)  # 0-100
    
    # Matched data details
    matched_data_type = Column(String(50))  # 'lab', 'imaging', 'consult', 'hospital', 'screening'
    matched_data_id = Column(Integer)  # ID of the matched record
    matched_keywords = Column(Text)  # JSON array of keywords that matched
    matched_text_snippet = Column(Text)  # Excerpt from matched document/data
    
    # Manual overrides
    manual_status = Column(String(20))  # Manual status set by user
    provider_notes = Column(Text)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    
    # Timestamps
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    data_date = Column(DateTime)  # Date of the matched data
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient")
    template = relationship("PrepChecklistTemplate")
    checklist_item = relationship("PrepChecklistItem")
    
    @property
    def matched_keywords_list(self):
        """Get matched keywords as a list"""
        if not self.matched_keywords:
            return []
        try:
            return json.loads(self.matched_keywords)
        except:
            return []
    
    @matched_keywords_list.setter
    def matched_keywords_list(self, keywords):
        """Set matched keywords from a list"""
        self.matched_keywords = json.dumps(keywords) if keywords else None
    
    def __repr__(self):
        return f"<PrepChecklistResult {self.checklist_item.title} - {self.match_status.value}>"


class PrepChecklistConfiguration(db.Model):
    """Global configuration for prep checklist system"""
    __tablename__ = 'prep_checklist_configuration'
    
    id = Column(Integer, primary_key=True)
    
    # Default template
    default_template_id = Column(Integer, ForeignKey('prep_checklist_templates.id'))
    
    # Evaluation settings
    auto_evaluate_on_data_add = Column(Boolean, default=True)
    require_manual_review = Column(Boolean, default=False)
    confidence_threshold = Column(Integer, default=70)
    
    # Data freshness settings
    max_lab_age_days = Column(Integer, default=365)
    max_imaging_age_days = Column(Integer, default=730)
    max_consult_age_days = Column(Integer, default=365)
    max_hospital_age_days = Column(Integer, default=1095)
    
    # Display settings
    show_confidence_scores = Column(Boolean, default=True)
    group_by_section = Column(Boolean, default=True)
    highlight_missing_items = Column(Boolean, default=True)
    
    # Integration settings
    sync_with_screening_types = Column(Boolean, default=True)
    auto_create_screening_items = Column(Boolean, default=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    default_template = relationship("PrepChecklistTemplate", foreign_keys=[default_template_id])
    
    @classmethod
    def get_config(cls):
        """Get or create the global configuration"""
        config = cls.query.first()
        if not config:
            config = cls()
            db.session.add(config)
            db.session.commit()
        return config
    
    def __repr__(self):
        return f"<PrepChecklistConfiguration>"