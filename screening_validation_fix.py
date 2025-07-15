#!/usr/bin/env python3
"""
Critical Fix: Screening Validation Logic
Ensures incomplete screenings cannot have matched documents
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ScreeningValidationFix:
    """
    Fix for screening validation logic to ensure:
    1. Incomplete screenings CANNOT have matched documents
    2. Only Complete/Due Soon screenings can have documents
    3. Performance optimization for /screenings page
    """

    def __init__(self):
        self.status_complete = "Complete"
        self.status_due = "Due"
        self.status_due_soon = "Due Soon"
        self.status_incomplete = "Incomplete"

    def validate_screening_document_relationship(self, screening, documents: List) -> bool:
        """
        Validate that screening-document relationships are correct

        Args:
            screening: Screening object
            documents: List of documents

        Returns:
            True if relationship is valid, False otherwise
        """
        # CRITICAL RULE: Incomplete screenings CANNOT have documents
        if screening.status == self.status_incomplete:
            if documents and len(documents) > 0:
                logger.error(f"❌ VALIDATION ERROR: Incomplete screening {screening.id} has {len(documents)} documents - this is invalid!")
                return False
            return True

        # Complete screenings MUST have documents
        if screening.status == self.status_complete:
            if not documents or len(documents) == 0:
                logger.error(f"❌ VALIDATION ERROR: Complete screening {screening.id} has no documents - this is invalid!")
                return False
            return True

        # Due and Due Soon can have or not have documents
        return True

    def fix_invalid_screening_relationships(self):
        """
        Fix all invalid screening-document relationships in the database
        """
        from app import db
        from models import Screening

        try:
            # Find all screenings with invalid relationships
            invalid_screenings = []

            # Check all screenings
            screenings = Screening.query.all()

            for screening in screenings:
                # Get associated documents
                documents = screening.documents.all() if hasattr(screening, 'documents') else []

                # Validate relationship
                if not self.validate_screening_document_relationship(screening, documents):
                    invalid_screenings.append(screening)

            # Fix invalid relationships
            fixed_count = 0
            for screening in invalid_screenings:
                if screening.status == self.status_incomplete:
                    # Remove all documents from incomplete screenings
                    screening.documents.clear()
                    logger.info(f"✅ Fixed: Removed documents from incomplete screening {screening.id}")
                    fixed_count += 1

                elif screening.status == self.status_complete:
                    # Complete screenings without documents should be marked as incomplete
                    screening.status = self.status_incomplete
                    screening.documents.clear()
                    screening.last_completed = None
                    logger.info(f"✅ Fixed: Changed complete screening {screening.id} to incomplete (no documents)")
                    fixed_count += 1

            # Commit changes
            db.session.commit()

            logger.info(f"✅ Fixed {fixed_count} invalid screening-document relationships")
            return {
                'success': True,
                'fixed_count': fixed_count,
                'total_checked': len(screenings)
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Error fixing screening relationships: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def run_screening_validation_fix():
    """
    Run the screening validation fix to ensure incomplete screenings have no documents
    """
    try:
        print("🔧 Running screening validation fix...")
        validator = ScreeningValidationFix()
        result = validator.fix_invalid_screening_relationships()

        if result['success']:
            print(f"✅ Fixed {result['fixed_count']} invalid relationships out of {result['total_checked']} screenings")
        else:
            print(f"❌ Validation fix failed: {result['error']}")

        return result

    except Exception as e:
        print(f"❌ Error running validation fix: {e}")
        return {'success': False, 'error': str(e)}

    def optimize_screening_queries(self):
        """
        Optimize screening queries for better performance
        """
        from app import db
        from models import Screening, ScreeningType, Patient

        try:
            # Create optimized query with proper joins and eager loading
            optimized_query = db.session.query(Screening).options(
                db.joinedload(Screening.patient),
                db.joinedload(Screening.screening_type),
                db.joinedload(Screening.documents)
            ).join(
                ScreeningType, Screening.screening_type_id == ScreeningType.id
            ).filter(
                ScreeningType.is_active == True
            )

            # Execute query and validate all results
            screenings = optimized_query.all()

            validation_results = []
            for screening in screenings:
                documents = screening.documents.all() if hasattr(screening, 'documents') else []
                is_valid = self.validate_screening_document_relationship(screening, documents)
                validation_results.append({
                    'screening_id': screening.id,
                    'status': screening.status,
                    'document_count': len(documents),
                    'is_valid': is_valid
                })

            valid_count = sum(1 for r in validation_results if r['is_valid'])

            logger.info(f"✅ Optimized query returned {len(screenings)} screenings, {valid_count} valid")

            return {
                'success': True,
                'total_screenings': len(screenings),
                'valid_screenings': valid_count,
                'validation_results': validation_results
            }

        except Exception as e:
            logger.error(f"❌ Error optimizing screening queries: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def run_screening_validation_fix():
    """
    Run the complete screening validation fix
    """
    from app import app

    with app.app_context():
        fixer = ScreeningValidationFix()

        print("🔧 Starting screening validation fix...")

        # Step 1: Fix invalid relationships
        print("Step 1: Fixing invalid screening-document relationships...")
        fix_result = fixer.fix_invalid_screening_relationships()
        if fix_result['success']:
            print(f"✅ Fixed {fix_result['fixed_count']} invalid relationships out of {fix_result['total_checked']} screenings")
        else:
            print(f"❌ Fix failed: {fix_result['error']}")

        # Step 2: Optimize queries
        print("Step 2: Optimizing screening queries...")
        optimize_result = fixer.optimize_screening_queries()
        if optimize_result['success']:
            print(f"✅ Optimized query performance: {optimize_result['valid_screenings']}/{optimize_result['total_screenings']} screenings are valid")
        else:
            print(f"❌ Optimization failed: {optimize_result['error']}")

        print("✅ Screening validation fix completed!")

if __name__ == "__main__":
    run_screening_validation_fix()