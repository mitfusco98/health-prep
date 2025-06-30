#!/usr/bin/env python3
"""
Migration script to consolidate legacy keyword fields into unified_keywords field.

This script:
1. Retrieves all existing keywords from content_keywords, document_keywords, and filename_keywords fields
2. Combines them into a single unified list (removing duplicates)
3. Saves the unified list to the new unified_keywords field
4. Clears the legacy fields to prevent duplication

Usage:
    python migrate_to_unified_keywords.py
"""

import json
from app import app, db
from models import ScreeningType

def migrate_keywords():
    """Migrate all screening types to use unified keywords"""
    
    with app.app_context():
        print("Starting keyword migration to unified system...")
        
        # Get all screening types
        screening_types = ScreeningType.query.all()
        
        migrated_count = 0
        skipped_count = 0
        
        for screening_type in screening_types:
            print(f"\nProcessing: {screening_type.name} (ID: {screening_type.id})")
            
            # Check if already migrated (has unified_keywords but no legacy keywords)
            if screening_type.get_unified_keywords():
                print(f"  ✓ Already has unified keywords: {len(screening_type.get_unified_keywords())} keywords")
                skipped_count += 1
                continue
            
            # Collect all legacy keywords
            content_keywords = screening_type.get_content_keywords() or []
            document_keywords = screening_type.get_document_keywords() or []
            filename_keywords = screening_type.get_filename_keywords() or []
            
            # Combine all keywords
            all_keywords = []
            all_keywords.extend(content_keywords)
            all_keywords.extend(document_keywords)
            all_keywords.extend(filename_keywords)
            
            if not all_keywords:
                print(f"  - No keywords to migrate")
                skipped_count += 1
                continue
            
            # Remove duplicates while preserving order, convert to lowercase for consistency
            unique_keywords = []
            seen = set()
            
            for keyword in all_keywords:
                if keyword and isinstance(keyword, str):
                    keyword_clean = keyword.lower().strip()
                    if keyword_clean and keyword_clean not in seen:
                        unique_keywords.append(keyword_clean)
                        seen.add(keyword_clean)
            
            if unique_keywords:
                print(f"  - Found {len(all_keywords)} total keywords")
                print(f"  - Migrating {len(unique_keywords)} unique keywords: {unique_keywords}")
                
                # Set unified keywords
                screening_type.set_unified_keywords(unique_keywords)
                
                # Clear legacy fields
                screening_type.set_content_keywords([])
                screening_type.set_document_keywords([])
                screening_type.set_filename_keywords([])
                
                migrated_count += 1
                print(f"  ✓ Successfully migrated to unified keywords")
            else:
                print(f"  - No valid keywords found after cleaning")
                skipped_count += 1
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✅ Migration completed successfully!")
            print(f"   Migrated: {migrated_count} screening types")
            print(f"   Skipped: {skipped_count} screening types")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Migration failed: {str(e)}")
            raise

def verify_migration():
    """Verify the migration was successful"""
    
    with app.app_context():
        print("\n" + "="*60)
        print("VERIFICATION REPORT")
        print("="*60)
        
        screening_types = ScreeningType.query.all()
        
        unified_count = 0
        legacy_count = 0
        
        for screening_type in screening_types:
            unified_keywords = screening_type.get_unified_keywords()
            content_keywords = screening_type.get_content_keywords()
            document_keywords = screening_type.get_document_keywords()
            filename_keywords = screening_type.get_filename_keywords()
            
            has_unified = bool(unified_keywords)
            has_legacy = bool(content_keywords or document_keywords or filename_keywords)
            
            if has_unified:
                unified_count += 1
                print(f"✓ {screening_type.name}: {len(unified_keywords)} unified keywords")
            
            if has_legacy:
                legacy_count += 1
                total_legacy = len(content_keywords) + len(document_keywords) + len(filename_keywords)
                print(f"⚠ {screening_type.name}: {total_legacy} legacy keywords still present")
        
        print(f"\nSummary:")
        print(f"  Screening types with unified keywords: {unified_count}")
        print(f"  Screening types with legacy keywords: {legacy_count}")
        
        if legacy_count == 0:
            print(f"✅ Migration verification passed - no legacy keywords remain")
        else:
            print(f"⚠ Migration verification found {legacy_count} screening types with legacy keywords")

if __name__ == "__main__":
    print("Unified Keywords Migration Tool")
    print("="*40)
    
    try:
        migrate_keywords()
        verify_migration()
        
    except Exception as e:
        print(f"\n❌ Migration error: {str(e)}")
        exit(1)