"""
Script to add default screening types to the database.
Run this script to populate the screening types table with common medical screenings.
"""

from app import app, db
from models import ScreeningType

DEFAULT_SCREENING_TYPES = [
    {
        "name": "Vaccination History",
        "description": "Review of patient's immunization records",
        "default_frequency": "Annual",
        "gender_specific": None,
        "min_age": None,
        "max_age": None,
        "is_active": True,
    },
    {
        "name": "Lipid Panel",
        "description": "Blood test that measures lipids - fats and fatty substances in the blood",
        "default_frequency": "Annual",
        "gender_specific": None,
        "min_age": 20,
        "max_age": None,
        "is_active": True,
    },
    {
        "name": "A1c",
        "description": "Blood test that indicates average blood glucose level over the past 2-3 months",
        "default_frequency": "Biannual",
        "gender_specific": None,
        "min_age": 45,
        "max_age": None,
        "is_active": True,
    },
    {
        "name": "Colonoscopy",
        "description": "Procedure to examine the inside of the colon and rectum",
        "default_frequency": "Every 10 years",
        "gender_specific": None,
        "min_age": 45,
        "max_age": 75,
        "is_active": True,
    },
    {
        "name": "Pap Smear",
        "description": "Screening test for cervical cancer",
        "default_frequency": "Every 3 years",
        "gender_specific": "Female",
        "min_age": 21,
        "max_age": 65,
        "is_active": True,
    },
    {
        "name": "Mammogram",
        "description": "X-ray of the breast to detect breast cancer",
        "default_frequency": "Annual or Biennial",
        "gender_specific": "Female",
        "min_age": 40,
        "max_age": 74,
        "is_active": True,
    },
    {
        "name": "DEXA Scan",
        "description": "Bone density test to diagnose osteoporosis",
        "default_frequency": "Every 2 years",
        "gender_specific": "Female",
        "min_age": 65,
        "max_age": None,
        "is_active": True,
    },
    {
        "name": "PSA Test",
        "description": "Blood test that measures the amount of prostate-specific antigen in the blood",
        "default_frequency": "Annual",
        "gender_specific": "Male",
        "min_age": 50,
        "max_age": 70,
        "is_active": True,
    },
    {
        "name": "Blood Pressure",
        "description": "Measurement of the pressure of circulating blood on the walls of blood vessels",
        "default_frequency": "Annual",
        "gender_specific": None,
        "min_age": 18,
        "max_age": None,
        "is_active": True,
    },
    {
        "name": "Eye Exam",
        "description": "Comprehensive examination of the eyes to detect vision problems and eye diseases",
        "default_frequency": "Every 2 years",
        "gender_specific": None,
        "min_age": 40,
        "max_age": None,
        "is_active": True,
    },
]


def add_default_screening_types():
    """Add default screening types to the database"""
    with app.app_context():
        # Check if there are already screening types in the database
        existing_count = ScreeningType.query.count()
        if existing_count > 0:
            print(
                f"Found {existing_count} existing screening types. Skipping default population."
            )
            return

        # Add each default screening type
        for screening_data in DEFAULT_SCREENING_TYPES:
            screening_type = ScreeningType(**screening_data)
            db.session.add(screening_type)
            print(f"Adding screening type: {screening_data['name']}")

        # Commit the changes
        db.session.commit()
        print(
            f"Successfully added {len(DEFAULT_SCREENING_TYPES)} default screening types"
        )


if __name__ == "__main__":
    add_default_screening_types()
