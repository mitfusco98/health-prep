
#!/usr/bin/env python3
"""
Create A1C screening variants for different patient populations
"""

from app import app, db
from models import ScreeningType

def create_a1c_variants():
    """Create A1C screening variants with different frequencies"""
    
    with app.app_context():
        # Check if general A1C exists, if not create it
        general_a1c = ScreeningType.query.filter_by(name="A1c").first()
        if not general_a1c:
            general_a1c = ScreeningType(
                name="A1c",
                description="Blood test that indicates average blood glucose level over the past 2-3 months for general population",
                frequency_number=1,
                frequency_unit="years",
                gender_specific=None,
                min_age=45,
                max_age=None,
                is_active=True,
            )
            db.session.add(general_a1c)
            print("Created general A1c screening")

        # Create diabetes-specific A1C variant
        diabetes_a1c = ScreeningType.query.filter_by(name="A1c - Diabetes Management").first()
        if not diabetes_a1c:
            diabetes_a1c = ScreeningType(
                name="A1c - Diabetes Management",
                description="HbA1c monitoring for diabetes patients - every 3 months",
                frequency_number=3,
                frequency_unit="months",
                gender_specific=None,
                min_age=None,
                max_age=None,
                is_active=True,
            )
            # Set trigger conditions for diabetes
            diabetes_a1c.set_trigger_conditions([
                {
                    "system": "http://snomed.info/sct",
                    "code": "73211009",
                    "display": "Diabetes mellitus"
                },
                {
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "E11.9",
                    "display": "Type 2 diabetes mellitus"
                }
            ])
            db.session.add(diabetes_a1c)
            print("Created A1c - Diabetes Management screening")

        # Create pre-diabetes A1C variant
        prediabetes_a1c = ScreeningType.query.filter_by(name="A1c - Pre-diabetes Monitoring").first()
        if not prediabetes_a1c:
            prediabetes_a1c = ScreeningType(
                name="A1c - Pre-diabetes Monitoring",
                description="HbA1c monitoring for pre-diabetes patients - every 6 months",
                frequency_number=6,
                frequency_unit="months",
                gender_specific=None,
                min_age=None,
                max_age=None,
                is_active=True,
            )
            # Set trigger conditions for pre-diabetes
            prediabetes_a1c.set_trigger_conditions([
                {
                    "system": "http://snomed.info/sct",
                    "code": "15777000",
                    "display": "Prediabetes"
                }
            ])
            db.session.add(prediabetes_a1c)
            print("Created A1c - Pre-diabetes Monitoring screening")

        db.session.commit()
        print("All A1C variants created successfully!")
        
        # Test variant detection
        from screening_variant_manager import variant_manager
        variants = variant_manager.find_screening_variants("A1c")
        print(f"\nFound {len(variants)} A1c variants:")
        for variant in variants:
            print(f"  - {variant.name}")
            display_info = variant_manager.get_variant_display_info(variant)
            print(f"    Base: {display_info['base_name']}, Variant: {display_info['variant_suffix']}")

if __name__ == "__main__":
    create_a1c_variants()
