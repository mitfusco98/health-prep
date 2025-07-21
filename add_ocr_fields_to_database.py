#!/usr/bin/env python3
"""
Add OCR status tracking fields to MedicalDocument table
Run this script to update the database schema for OCR integration
"""

import os
from app import app, db
from sqlalchemy import text
import logging

def add_ocr_fields():
    """Add OCR tracking columns to MedicalDocument table"""
    with app.app_context():
        try:
            # Check if OCR fields already exist
            with db.engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name='medical_document' AND column_name='ocr_processed'"
                    )
                )
                rows = result.fetchall()
                
                if len(rows) == 0:
                    print("Adding OCR status tracking fields to medical_document table...")
                    
                    # Add OCR processed flag
                    conn.execute(
                        text("ALTER TABLE medical_document ADD COLUMN ocr_processed BOOLEAN DEFAULT FALSE")
                    )
                    conn.commit()
                    print("✅ Added ocr_processed column")
                    
                    # Add OCR confidence score
                    conn.execute(
                        text("ALTER TABLE medical_document ADD COLUMN ocr_confidence FLOAT")
                    )
                    conn.commit()
                    print("✅ Added ocr_confidence column")
                    
                    # Add OCR processing date
                    conn.execute(
                        text("ALTER TABLE medical_document ADD COLUMN ocr_processing_date TIMESTAMP")
                    )
                    conn.commit()
                    print("✅ Added ocr_processing_date column")
                    
                    # Add OCR text length
                    conn.execute(
                        text("ALTER TABLE medical_document ADD COLUMN ocr_text_length INTEGER")
                    )
                    conn.commit()
                    print("✅ Added ocr_text_length column")
                    
                    # Add OCR quality flags
                    conn.execute(
                        text("ALTER TABLE medical_document ADD COLUMN ocr_quality_flags TEXT")
                    )
                    conn.commit()
                    print("✅ Added ocr_quality_flags column")
                    
                    print("🎉 All OCR fields added successfully!")
                    
                else:
                    print("OCR fields already exist in medical_document table")
                    
        except Exception as e:
            print(f"❌ Error adding OCR fields: {e}")
            raise


if __name__ == "__main__":
    add_ocr_fields()