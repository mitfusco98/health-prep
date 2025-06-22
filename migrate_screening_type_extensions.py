"""
Database Migration: Add extended fields to ScreeningType table
Adds: frequency_months, gender, keywords, filename_keywords, document_section
"""

import os
import sys
from sqlalchemy import text
from app import app, db

def add_screening_type_extensions():
    """Add extended fields to ScreeningType table"""
    
    with app.app_context():
        try:
            # Add new columns to ScreeningType table
            db.session.execute(text("""
                ALTER TABLE screening_type 
                ADD COLUMN IF NOT EXISTS frequency_months INTEGER;
            """))
            
            db.session.execute(text("""
                ALTER TABLE screening_type 
                ADD COLUMN IF NOT EXISTS gender VARCHAR(10);
            """))
            
            db.session.execute(text("""
                ALTER TABLE screening_type 
                ADD COLUMN IF NOT EXISTS keywords TEXT;
            """))
            
            db.session.execute(text("""
                ALTER TABLE screening_type 
                ADD COLUMN IF NOT EXISTS filename_keywords TEXT;
            """))
            
            db.session.execute(text("""
                ALTER TABLE screening_type 
                ADD COLUMN IF NOT EXISTS document_section VARCHAR(50);
            """))
            
            db.session.commit()
            print("✓ Added extended fields to ScreeningType table")
            
            # Migrate existing gender_specific to gender field
            db.session.execute(text("""
                UPDATE screening_type 
                SET gender = gender_specific 
                WHERE gender_specific IS NOT NULL AND gender IS NULL;
            """))
            
            # Convert existing frequency data to frequency_months
            db.session.execute(text("""
                UPDATE screening_type 
                SET frequency_months = CASE 
                    WHEN frequency_unit = 'years' THEN frequency_number * 12
                    WHEN frequency_unit = 'months' THEN frequency_number
                    WHEN frequency_unit = 'weeks' THEN ROUND(frequency_number * 0.25)
                    WHEN frequency_unit = 'days' THEN ROUND(frequency_number / 30.0)
                    ELSE NULL
                END
                WHERE frequency_number IS NOT NULL AND frequency_unit IS NOT NULL 
                AND frequency_months IS NULL;
            """))
            
            db.session.commit()
            print("✓ Migrated existing data to new fields")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error during migration: {str(e)}")
            raise

def verify_migration():
    """Verify the migration was successful"""
    
    with app.app_context():
        try:
            # Check if all columns exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'screening_type' 
                AND column_name IN ('frequency_months', 'gender', 'keywords', 'filename_keywords', 'document_section');
            """))
            
            columns = [row[0] for row in result]
            expected_columns = ['frequency_months', 'gender', 'keywords', 'filename_keywords', 'document_section']
            
            if set(columns) == set(expected_columns):
                print("✓ All new columns created successfully")
                
                # Check data migration
                result = db.session.execute(text("""
                    SELECT COUNT(*) as total,
                           COUNT(frequency_months) as with_freq_months,
                           COUNT(gender) as with_gender
                    FROM screening_type;
                """))
                
                stats = result.fetchone()
                print(f"✓ Data migration stats: {stats.total} total records, {stats.with_freq_months} with frequency_months, {stats.with_gender} with gender")
                return True
            else:
                missing = set(expected_columns) - set(columns)
                print(f"✗ Missing columns: {missing}")
                return False
                
        except Exception as e:
            print(f"✗ Error verifying migration: {str(e)}")
            return False

if __name__ == "__main__":
    print("Starting ScreeningType table extension migration...")
    add_screening_type_extensions()
    
    print("\nVerifying migration...")
    if verify_migration():
        print("\n✓ Migration completed successfully!")
    else:
        print("\n✗ Migration verification failed!")
        sys.exit(1)