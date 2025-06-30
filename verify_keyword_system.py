
#!/usr/bin/env python3
"""
Keyword System Verification
Checks that the keyword system is working correctly without duplications.
"""

from app import app, db
from models import ScreeningType
import json

def verify_keyword_system():
    """Verify the keyword system is working correctly"""
    print("Verifying keyword system...")
    
    with app.app_context():
        screening_types = ScreeningType.query.all()
        
        total_issues = 0
        
        print(f"\nChecking {len(screening_types)} screening types:")
        print("-" * 60)
        
        for screening_type in screening_types:
            issues = []
            
            # Get all keyword fields
            unified_keywords = screening_type.get_unified_keywords()
            content_keywords = screening_type.get_content_keywords()
            document_keywords = screening_type.get_document_keywords()
            filename_keywords = screening_type.get_filename_keywords()
            
            # Check for legacy data
            if content_keywords:
                issues.append(f"Has {len(content_keywords)} content keywords")
            if document_keywords:
                issues.append(f"Has {len(document_keywords)} document keywords")
            if filename_keywords:
                issues.append(f"Has {len(filename_keywords)} filename keywords")
            
            # Check unified keywords
            unified_count = len(unified_keywords) if unified_keywords else 0
            
            # Print status
            status = "✅" if not issues else "❌"
            print(f"{status} {screening_type.name} (ID: {screening_type.id})")
            print(f"    Unified keywords: {unified_count}")
            
            if issues:
                for issue in issues:
                    print(f"    ⚠️  {issue}")
                total_issues += len(issues)
            
            # Show actual keywords if they exist
            if unified_keywords:
                print(f"    Keywords: {', '.join(unified_keywords[:5])}" + ("..." if len(unified_keywords) > 5 else ""))
            
            print()
        
        print("-" * 60)
        if total_issues == 0:
            print("🎉 VERIFICATION PASSED")
            print("No legacy keyword data detected. System is clean!")
        else:
            print(f"⚠️  VERIFICATION FOUND {total_issues} ISSUES")
            print("Legacy keyword data still exists. Run reset_keyword_system.py")
        
        return total_issues == 0

if __name__ == "__main__":
    verify_keyword_system()
