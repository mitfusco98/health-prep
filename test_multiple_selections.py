
from app import app, db
from models import ChecklistSettings
from organized.routes.checklist_routes import get_or_create_settings

def test_multiple_selections():
    """Test that multiple selections can be saved properly"""
    with app.app_context():
        # Get or create settings
        settings = get_or_create_settings()
        
        # Test with multiple items
        test_items = ['Mammogram', 'Colonoscopy', 'Bone Density Screening']
        settings.default_items = '\n'.join(test_items)
        
        try:
            db.session.commit()
            print(f"✓ Successfully saved multiple items: {test_items}")
            
            # Verify by refreshing from database
            db.session.refresh(settings)
            saved_items = settings.default_items_list
            print(f"✓ Retrieved items from database: {saved_items}")
            
            if len(saved_items) == len(test_items):
                print("✓ Multiple items correctly saved and retrieved!")
                return True
            else:
                print(f"✗ Expected {len(test_items)} items, got {len(saved_items)}")
                return False
                
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error saving multiple items: {e}")
            return False

if __name__ == '__main__':
    test_multiple_selections()
