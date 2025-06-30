
#!/usr/bin/env python3
"""
Comprehensive Legacy System Removal
Removes all legacy keyword systems that are causing duplication issues.
"""

from app import app, db
from models import ScreeningType
import os
import glob

def remove_legacy_keyword_systems():
    """Remove all legacy keyword handling from the database"""
    print("🧹 Removing Legacy Keyword Systems")
    print("=" * 50)
    
    with app.app_context():
        # Step 1: Force clear ALL legacy keyword fields
        print("Step 1: Clearing all legacy keyword fields...")
        screening_types = ScreeningType.query.all()
        
        for screening_type in screening_types:
            # Force set legacy fields to None/NULL
            screening_type.content_keywords = None
            screening_type.document_keywords = None
            screening_type.filename_keywords = None
            
            print(f"  ✓ Cleared legacy fields for: {screening_type.name}")
        
        db.session.commit()
        print("✅ All legacy keyword fields cleared")

def remove_legacy_files():
    """Remove legacy keyword management files"""
    print("\nStep 2: Removing legacy keyword files...")
    
    legacy_files = [
        'screening_keyword_manager.py',
        'migrate_to_unified_keywords.py',
        'migrate_to_unified_config.py',
        'clear_legacy_keywords.py'
    ]
    
    removed_count = 0
    for file_path in legacy_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  ✓ Removed: {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"  ⚠️  Could not remove {file_path}: {str(e)}")
        else:
            print(f"  - Not found: {file_path}")
    
    print(f"✅ Removed {removed_count} legacy files")

def clean_screening_keyword_routes():
    """Clean up the screening keyword routes to use ONLY unified keywords"""
    print("\nStep 3: Cleaning screening keyword routes...")
    
    # This will be handled by a separate file update
    print("  ✓ Will update screening_keyword_routes.py to use only unified keywords")

def verify_cleanup():
    """Verify that cleanup was successful"""
    print("\nStep 4: Verification...")
    
    with app.app_context():
        screening_types = ScreeningType.query.all()
        issues_found = 0
        
        for screening_type in screening_types:
            # Check for any remaining legacy data
            if (screening_type.content_keywords or 
                screening_type.document_keywords or 
                screening_type.filename_keywords):
                
                print(f"  ❌ {screening_type.name}: Still has legacy keyword data")
                issues_found += 1
            else:
                unified_count = len(screening_type.get_unified_keywords() or [])
                print(f"  ✅ {screening_type.name}: {unified_count} unified keywords only")
        
        if issues_found == 0:
            print("\n🎉 Legacy system removal completed successfully!")
            return True
        else:
            print(f"\n⚠️  Found {issues_found} screening types with remaining legacy data")
            return False

if __name__ == "__main__":
    try:
        # Step 1: Remove legacy database fields
        remove_legacy_keyword_systems()
        
        # Step 2: Remove legacy files
        remove_legacy_files()
        
        # Step 3: Verify cleanup
        success = verify_cleanup()
        
        if success:
            print("\n" + "=" * 50)
            print("✅ LEGACY CLEANUP COMPLETE")
            print("All legacy keyword systems have been removed.")
            print("The system now uses ONLY unified keywords.")
            print("\nNext steps:")
            print("1. Update screening_keyword_routes.py")
            print("2. Clear any remaining cache")
            print("3. Test the keyword system")
        else:
            print("\n" + "=" * 50)
            print("❌ CLEANUP INCOMPLETE")
            print("Some legacy data remains. Manual intervention may be required.")
            
    except Exception as e:
        print(f"\n❌ ERROR during cleanup: {str(e)}")
