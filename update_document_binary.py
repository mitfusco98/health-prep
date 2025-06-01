"""
Script to update the MedicalDocument table schema to support binary files.
"""
from app import app, db
import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)

def add_binary_columns():
    """Add binary content columns to MedicalDocument table"""
    with app.app_context():
        try:
            # Check if columns already exist
            with db.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT column_name FROM information_schema.columns WHERE table_name='medical_document' AND column_name='binary_content'")
                )
                rows = result.fetchall()
                if len(rows) == 0:
                    # Columns don't exist, add them
                    logging.info("Adding binary_content column to medical_document table")
                    conn.execute(text("ALTER TABLE medical_document ADD COLUMN binary_content BYTEA"))
                    conn.commit()
                    
                    logging.info("Adding is_binary column to medical_document table")
                    conn.execute(text("ALTER TABLE medical_document ADD COLUMN is_binary BOOLEAN DEFAULT FALSE"))
                    conn.commit()
                    
                    logging.info("Adding mime_type column to medical_document table")
                    conn.execute(text("ALTER TABLE medical_document ADD COLUMN mime_type VARCHAR(100)"))
                    conn.commit()
                    
                    logging.info("Making content column nullable")
                    conn.execute(text("ALTER TABLE medical_document ALTER COLUMN content DROP NOT NULL"))
                    conn.commit()
                    
                    logging.info("Schema update complete!")
                    return True
                else:
                    logging.info("Columns already exist, no changes needed")
                    return False
        except Exception as e:
            logging.error(f"Error updating schema: {str(e)}")
            return False

if __name__ == "__main__":
    add_binary_columns()