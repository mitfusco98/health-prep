#!/usr/bin/env python3
"""
Admin utility to manually clean up orphaned document relationships
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Screening, MedicalDocument
from automated_screening_routes import cleanup_orphaned_screening_documents

def main():
    """Main function to clean up orphaned document relationships"""
    with app.app_context():
        print("🔍 Starting orphaned document relationship cleanup...")
        
        try:
            # Count current relationships before cleanup
            total_screenings = Screening.query.count()
            print(f"📊 Found {total_screenings} total screenings in database")
            
            # Run the cleanup process
            cleaned_count = cleanup_orphaned_screening_documents()
            
            if cleaned_count > 0:
                print(f"✅ Successfully cleaned up {cleaned_count} orphaned document relationships")
                print("💾 Changes have been committed to database")
            else:
                print("✨ No orphaned document relationships found - system is clean!")
            
            # Verify results
            print("\n📈 Verification:")
            for screening in Screening.query.all():
                doc_count = screening.document_count
                if doc_count > 0:
                    valid_docs = screening.get_valid_documents_with_access_check()
                    print(f"   Screening {screening.id} ({screening.screening_type}): {len(valid_docs)} valid documents")
                    
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            db.session.rollback()
            return 1
            
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)