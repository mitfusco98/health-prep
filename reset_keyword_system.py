
#!/usr/bin/env python3
"""
Complete Keyword System Reset and Reinstallation
This script completely clears all keyword data and reinstalls with clean unified keywords only.
"""

from app import app, db
from models import ScreeningType
import json

def reset_keyword_system():
    """Complete reset of the keyword system"""
    print("Starting complete keyword system reset...")
    
    with app.app_context():
        # Get all screening types
        screening_types = ScreeningType.query.all()
        
        print(f"Found {len(screening_types)} screening types to reset")
        
        # Step 1: Completely clear ALL keyword fields for ALL screening types
        print("\nStep 1: Clearing all keyword fields...")
        for screening_type in screening_types:
            print(f"  - Clearing all keywords for: {screening_type.name} (ID: {screening_type.id})")
            
            # Clear unified keywords
            screening_type.unified_keywords = None
            
            # Clear legacy fields
            screening_type.content_keywords = None
            screening_type.document_keywords = None
            screening_type.filename_keywords = None
            
        # Commit clearing
        db.session.commit()
        print("✅ All keyword fields cleared")
        
        # Step 2: Install fresh default keywords using only unified field
        print("\nStep 2: Installing fresh default keywords...")
        
        default_keywords = {
            "Mammogram": ["mammogram", "mammography", "breast imaging", "breast screening", "mammo"],
            "Colonoscopy": ["colonoscopy", "colon screening", "colorectal", "colonography", "colo"],
            "Bone Density Screening": ["dexa", "dxa", "bone density", "osteoporosis screening"],
            "Pap Smear": ["pap smear", "cervical screening", "cytology", "pap test"],
            "Cholesterol Screening": ["cholesterol", "lipid panel", "lipids", "hdl", "ldl"],
            "Blood Pressure Check": ["blood pressure", "hypertension", "bp check", "systolic", "diastolic"],
            "Diabetes Screening": ["glucose", "a1c", "hba1c", "diabetes", "blood sugar"],
            "Prostate Screening": ["psa", "prostate", "prostate cancer screening"],
            "Skin Cancer Screening": ["dermatology", "skin check", "mole check", "melanoma"],
            "Eye Exam": ["ophthalmology", "eye exam", "vision", "glaucoma", "retinal"]
        }
        
        installed_count = 0
        for screening_type in screening_types:
            if screening_type.name in default_keywords:
                keywords = default_keywords[screening_type.name]
                print(f"  - Installing {len(keywords)} keywords for: {screening_type.name}")
                screening_type.set_unified_keywords(keywords)
                installed_count += 1
            else:
                print(f"  - No default keywords for: {screening_type.name}")
        
        # Step 3: Commit the new keywords
        db.session.commit()
        print(f"✅ Installed keywords for {installed_count} screening types")
        
        # Step 4: Verification
        print("\nStep 3: Verification...")
        verification_passed = True
        
        for screening_type in screening_types:
            # Reload from database to ensure fresh data
            db.session.refresh(screening_type)
            
            unified_keywords = screening_type.get_unified_keywords()
            content_keywords = screening_type.get_content_keywords()
            document_keywords = screening_type.get_document_keywords()
            filename_keywords = screening_type.get_filename_keywords()
            
            # Check for any legacy data
            has_legacy = bool(content_keywords or document_keywords or filename_keywords)
            
            if has_legacy:
                print(f"  ❌ {screening_type.name}: Still has legacy keyword data")
                verification_passed = False
            else:
                keyword_count = len(unified_keywords) if unified_keywords else 0
                print(f"  ✅ {screening_type.name}: {keyword_count} unified keywords only")
        
        if verification_passed:
            print("\n🎉 Keyword system reset completed successfully!")
            print("All screening types now use unified keywords only.")
        else:
            print("\n⚠️  Some issues detected during verification")
            return False
        
        return True

def clear_keyword_cache():
    """Clear any cached keyword data"""
    print("\nClearing keyword cache...")
    
    # Import the cache from screening_keyword_routes
    try:
        from screening_keyword_routes import _request_cache
        if _request_cache:
            cache_keys = list(_request_cache.keys())
            _request_cache.clear()
            print(f"✅ Cleared {len(cache_keys)} cached keyword entries")
        else:
            print("✅ Cache was already empty")
    except ImportError:
        print("⚠️  Could not import cache - this is okay")

if __name__ == "__main__":
    print("🔄 Complete Keyword System Reset")
    print("=" * 50)
    
    try:
        # Step 1: Reset the database
        success = reset_keyword_system()
        
        if success:
            # Step 2: Clear any cached data
            clear_keyword_cache()
            
            print("\n" + "=" * 50)
            print("✅ RESET COMPLETE")
            print("The keyword system has been completely reset.")
            print("All duplication issues should now be resolved.")
            print("You can now add new keywords through the web interface.")
        else:
            print("\n" + "=" * 50)
            print("❌ RESET FAILED")
            print("Some issues were detected. Please check the output above.")
    
    except Exception as e:
        print(f"\n❌ ERROR during reset: {str(e)}")
        print("You may need to check the database connection or model definitions.")
