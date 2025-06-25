
#!/usr/bin/env python3
"""
Debug script to test multiple checkbox selections
"""

from app import app, db
from models import ChecklistSettings, ScreeningType

def test_multiple_selections():
    """Test multiple checkbox selections functionality"""
    print("=== Multiple Selections Debug Test ===")
    
    with app.app_context():
        # Get current settings
        settings = ChecklistSettings.query.first()
        if not settings:
            settings = ChecklistSettings()
            db.session.add(settings)
            db.session.commit()
        
        print(f"Current default_items: '{settings.default_items}'")
        print(f"Current default_items_list: {settings.default_items_list}")
        
        # Test setting multiple items
        test_items = ["Eye Exam", "Bone Density Screening", "Lipid Panel"]
        settings.default_items = '\n'.join(test_items)
        db.session.commit()
        
        print(f"After setting multiple items:")
        print(f"  default_items: '{settings.default_items}'")
        print(f"  default_items_list: {settings.default_items_list}")
        
        # Refresh from database to verify persistence
        db.session.refresh(settings)
        print(f"After refresh from database:")
        print(f"  default_items: '{settings.default_items}'")
        print(f"  default_items_list: {settings.default_items_list}")
        print(f"  Number of items: {len(settings.default_items_list)}")
        
        # Test with available screening types
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        print(f"\nAvailable screening types: {[st.name for st in screening_types]}")
        
        # Test which items would be valid
        valid_items = []
        for item in settings.default_items_list:
            screening_type = ScreeningType.query.filter_by(name=item).first()
            if screening_type:
                valid_items.append(item)
                print(f"  ✓ '{item}' - valid screening type")
            else:
                print(f"  ✗ '{item}' - no matching screening type")
        
        print(f"\nValid items: {valid_items}")
        print("=== Test Complete ===")

if __name__ == "__main__":
    test_multiple_selections()
