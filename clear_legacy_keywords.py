
#!/usr/bin/env python3
"""
Script to clear legacy keyword fields for screening types that have unified keywords.
This prevents duplication issues where both unified and legacy fields contain data.
"""

from app import app, db
from models import ScreeningType

def clear_legacy_keywords():
    """Clear legacy keyword fields for screening types with unified keywords"""
    print("Clearing legacy keyword fields...")
    
    with app.app_context():
        # Get all screening types with unified keywords
        screening_types = ScreeningType.query.filter(
            ScreeningType.unified_keywords.isnot(None)
        ).all()
        
        updated_count = 0
        
        for screening_type in screening_types:
            # Check if any legacy fields have data
            has_legacy_data = (
                screening_type.content_keywords or 
                screening_type.document_keywords or 
                screening_type.filename_keywords
            )
            
            if has_legacy_data:
                print(f"Clearing legacy keywords for {screening_type.name} (ID: {screening_type.id})")
                
                # Clear legacy fields
                screening_type.content_keywords = None
                screening_type.document_keywords = None
                screening_type.filename_keywords = None
                
                updated_count += 1
        
        # Commit changes
        if updated_count > 0:
            db.session.commit()
            print(f"✅ Cleared legacy keywords for {updated_count} screening types")
        else:
            print("✅ No legacy keyword cleanup needed")

if __name__ == "__main__":
    clear_legacy_keywords()
