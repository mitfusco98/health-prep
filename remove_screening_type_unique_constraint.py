"""
Script to remove the unique constraint from the screening_type table's name column.
This allows duplicate screening type names with different gender-specific settings.
"""

from app import app, db
from sqlalchemy import text

def remove_unique_constraint():
    """Remove the unique constraint from the screening_type table's name column"""
    with app.app_context():
        try:
            # First, try to drop the constraint
            db.session.execute(text("""
                ALTER TABLE screening_type 
                DROP CONSTRAINT IF EXISTS screening_type_name_key;
            """))
            db.session.commit()
            print("Successfully removed unique constraint from screening_type.name column")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error removing unique constraint: {str(e)}")
            return False

if __name__ == "__main__":
    remove_unique_constraint()