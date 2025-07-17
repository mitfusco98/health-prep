#!/usr/bin/env python3
"""
Utility to generate missing screenings for active screening types
"""

import logging
from app import app, db
from models import Patient, ScreeningType, Screening
from automated_screening_engine import ScreeningStatusEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_missing_screenings_for_type(screening_type_name):
    """Generate missing screenings for a specific screening type"""
    with app.app_context():
        try:
            # Get the screening type
            screening_type = ScreeningType.query.filter_by(name=screening_type_name, is_active=True).first()
            if not screening_type:
                logger.error(f"Screening type '{screening_type_name}' not found or not active")
                return 0
            
            logger.info(f"🔄 Generating missing screenings for: {screening_type_name}")
            
            # Initialize screening engine
            engine = ScreeningStatusEngine()
            generated_count = 0
            
            # Get all patients who should have this screening but don't
            patients_needing_screening = Patient.query.filter(
                ~Patient.id.in_(
                    db.session.query(Screening.patient_id).filter(
                        Screening.screening_type == screening_type.name,
                        Screening.is_visible == True
                    )
                )
            ).all()
            
            logger.info(f"Found {len(patients_needing_screening)} patients potentially needing {screening_type_name}")
            
            for patient in patients_needing_screening:
                try:
                    # Check if patient is eligible for this screening type
                    if engine._is_patient_eligible(patient, screening_type):
                        # Generate screening for this patient
                        new_screening = engine._create_screening_for_patient(patient, screening_type)
                        if new_screening:
                            generated_count += 1
                            logger.info(f"✅ Generated {screening_type_name} for {patient.full_name} (age {patient.age})")
                except Exception as patient_error:
                    logger.warning(f"⚠️ Error generating screening for {patient.full_name}: {patient_error}")
                    continue
            
            # Commit all changes
            db.session.commit()
            logger.info(f"🎉 COMPLETE: Generated {generated_count} new {screening_type_name} screenings")
            return generated_count
            
        except Exception as e:
            logger.error(f"❌ Error generating screenings for {screening_type_name}: {e}")
            db.session.rollback()
            return 0

def generate_missing_screenings_for_all_active_types():
    """Generate missing screenings for all active screening types with low counts"""
    with app.app_context():
        # Get active screening types that have fewer than expected screenings
        screening_types_to_process = [
            'HbA1c Test',  # Has 0 screenings but should have many
        ]
        
        total_generated = 0
        for screening_type_name in screening_types_to_process:
            count = generate_missing_screenings_for_type(screening_type_name)
            total_generated += count
        
        logger.info(f"🎯 TOTAL: Generated {total_generated} screenings across all types")
        return total_generated

if __name__ == "__main__":
    generate_missing_screenings_for_all_active_types()