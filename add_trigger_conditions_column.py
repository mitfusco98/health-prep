"""
Database Migration: Add trigger_conditions column to ScreeningType table
Enables FHIR condition-based screening triggers using SNOMED, ICD-10, or custom codes
"""

from app import app, db
from models import ScreeningType
import json

def add_trigger_conditions_column():
    """Add trigger_conditions column to ScreeningType table"""
    
    with app.app_context():
        try:
            # Add the column using raw SQL to avoid model conflicts
            db.engine.execute("""
                ALTER TABLE screening_type 
                ADD COLUMN IF NOT EXISTS trigger_conditions TEXT;
            """)
            
            db.session.commit()
            print("✓ Successfully added trigger_conditions column to ScreeningType table")
            
            # Add some example trigger conditions to existing screening types
            add_example_trigger_conditions()
            
        except Exception as e:
            print(f"Error adding trigger_conditions column: {str(e)}")
            db.session.rollback()

def add_example_trigger_conditions():
    """Add example trigger conditions to existing screening types"""
    
    # Example trigger conditions for common screenings
    trigger_examples = {
        "Diabetes Screening": [
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
        ],
        "Cardiovascular Screening": [
            {
                "system": "http://snomed.info/sct",
                "code": "38341003", 
                "display": "Hypertensive disorder"
            },
            {
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": "I10",
                "display": "Essential hypertension"
            }
        ],
        "Cancer Screening": [
            {
                "system": "http://snomed.info/sct",
                "code": "395557000",
                "display": "Family history of malignant neoplasm"
            },
            {
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": "Z80.9", 
                "display": "Family history of malignant neoplasm, unspecified"
            }
        ]
    }
    
    # Update existing screening types with trigger conditions
    for screening_name, conditions in trigger_examples.items():
        screening_type = ScreeningType.query.filter_by(name=screening_name).first()
        if screening_type:
            screening_type.trigger_conditions = json.dumps(conditions)
            print(f"✓ Added trigger conditions to {screening_name}")
    
    # Create new screening types with trigger conditions if they don't exist
    for screening_name, conditions in trigger_examples.items():
        existing = ScreeningType.query.filter_by(name=screening_name).first()
        if not existing:
            new_screening = ScreeningType(
                name=screening_name,
                description=f"Condition-triggered {screening_name.lower()}",
                default_frequency="Annual",
                is_active=True,
                trigger_conditions=json.dumps(conditions)
            )
            db.session.add(new_screening)
            print(f"✓ Created new screening type: {screening_name}")
    
    db.session.commit()

if __name__ == "__main__":
    print("Adding trigger_conditions column to ScreeningType table...")
    add_trigger_conditions_column()
    print("Migration completed successfully!")