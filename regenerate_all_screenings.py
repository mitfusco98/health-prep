#!/usr/bin/env python3
"""
Regenerate All Screenings with Unified Engine
Clears existing screenings and regenerates them using the new reliable unified engine
"""

import logging
from datetime import datetime
from app import app, db
from models import Patient, ScreeningType, Screening
from unified_screening_engine import unified_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def regenerate_all_screenings(clear_existing=True):
    """
    Regenerate all screenings using the unified engine
    
    Args:
        clear_existing: Whether to clear existing screenings first
    """
    with app.app_context():
        try:
            logger.info("🔄 Starting screening regeneration with unified engine")
            
            # Clear existing screenings if requested
            if clear_existing:
                logger.info("🗑️ Clearing existing screenings...")
                existing_count = Screening.query.count()
                Screening.query.delete()
                db.session.commit()
                logger.info(f"✅ Cleared {existing_count} existing screenings")
            
            # Generate new screenings with unified engine
            logger.info("🚀 Generating new screenings with unified engine...")
            results = unified_engine.bulk_generate_screenings()
            
            # Report results
            logger.info("🎯 REGENERATION COMPLETE")
            logger.info(f"   Generated: {results['total_generated']}")
            logger.info(f"   Skipped: {results['total_skipped']}")
            logger.info(f"   Errors: {results['errors']}")
            logger.info(f"   Time: {results['processing_time']:.2f}s")
            
            logger.info("\n📊 BY SCREENING TYPE:")
            for screening_type, count in results['by_screening_type'].items():
                logger.info(f"   {screening_type}: {count}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during regeneration: {e}")
            db.session.rollback()
            return {"error": str(e)}

def check_screening_counts():
    """Check screening counts by type"""
    with app.app_context():
        logger.info("📊 CURRENT SCREENING COUNTS:")
        
        # Get active screening types
        active_types = ScreeningType.query.filter_by(is_active=True).all()
        
        for screening_type in active_types:
            count = Screening.query.filter_by(
                screening_type=screening_type.name,
                is_visible=True
            ).count()
            logger.info(f"   {screening_type.name}: {count}")

def validate_unified_engine():
    """Test the unified engine with a sample patient"""
    with app.app_context():
        logger.info("🧪 TESTING UNIFIED ENGINE:")
        
        # Get a sample patient
        patient = Patient.query.first()
        if not patient:
            logger.error("No patients found for testing")
            return
        
        logger.info(f"Testing with patient: {patient.full_name}")
        
        # Test with a few screening types
        screening_types = ScreeningType.query.filter_by(is_active=True).limit(3).all()
        
        for screening_type in screening_types:
            # Test eligibility
            is_eligible, reason = unified_engine.is_patient_eligible(patient, screening_type)
            logger.info(f"   {screening_type.name}: {'✅ Eligible' if is_eligible else '❌ Not eligible'} - {reason}")
            
            # Test status determination
            if is_eligible:
                status_info = unified_engine.determine_screening_status(patient, screening_type)
                logger.info(f"      Status: {status_info['status']}")
                logger.info(f"      Matching docs: {len(status_info['matching_documents'])}")

if __name__ == "__main__":
    print("🏥 SCREENING REGENERATION UTILITY")
    print("=" * 50)
    
    # Check current state
    check_screening_counts()
    
    # Test unified engine
    validate_unified_engine()
    
    # Ask user confirmation
    response = input("\n🔄 Regenerate all screenings with unified engine? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        results = regenerate_all_screenings(clear_existing=True)
        
        if 'error' not in results:
            print("\n✅ Regeneration successful!")
            check_screening_counts()
        else:
            print(f"\n❌ Regeneration failed: {results['error']}")
    else:
        print("❌ Regeneration cancelled")