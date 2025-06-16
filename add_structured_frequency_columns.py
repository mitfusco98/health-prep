
"""
Migration script to add structured frequency columns to ScreeningType table
"""

from app import app, db
from models import ScreeningType

def add_structured_frequency_columns():
    """Add frequency_number and frequency_unit columns to ScreeningType"""
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('screening_type')]
            
            if 'frequency_number' not in columns:
                # Add frequency_number column
                db.engine.execute('ALTER TABLE screening_type ADD COLUMN frequency_number INTEGER')
                print("✓ Added frequency_number column")
            else:
                print("✓ frequency_number column already exists")
                
            if 'frequency_unit' not in columns:
                # Add frequency_unit column
                db.engine.execute('ALTER TABLE screening_type ADD COLUMN frequency_unit VARCHAR(20)')
                print("✓ Added frequency_unit column")
            else:
                print("✓ frequency_unit column already exists")
                
            print("\n🔄 Migration completed successfully!")
            print("\nNow you can:")
            print("1. Use the new structured frequency inputs in forms")
            print("2. Convert existing text frequencies to structured format")
            print("3. Update any existing screening types with structured frequency data")
            
        except Exception as e:
            print(f"❌ Error during migration: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    add_structured_frequency_columns()
