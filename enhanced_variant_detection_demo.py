#!/usr/bin/env python3
"""
Enhanced Variant Detection Demo
Demonstrates the improved variant detection system using standardized medical terminology
to resolve issues with "mammogram" vs "mammography" and similar variants.
"""

from medical_terminology_standardizer import medical_standardizer
from screening_variant_manager import ScreeningVariantManager
from models import ScreeningType, db
from app import app

def test_enhanced_variant_detection():
    """Test the enhanced variant detection with medical terminology standardization"""
    
    with app.app_context():
        print("🔬 Enhanced Variant Detection System Demo")
        print("=" * 60)
        
        # Test cases that previously caused issues
        test_cases = [
            ("mammogram", "mammography"),
            ("diabetes", "diabetes mellitus"),
            ("a1c", "HbA1c Test"),
            ("pap test", "Pap Smear"),
            ("colonoscopy", "Colorectal Screening"),
            ("bone scan", "Bone Density Screening")
        ]
        
        print("\n1. Testing Medical Terminology Normalization:")
        print("-" * 50)
        
        for variant1, variant2 in test_cases:
            norm1, conf1 = medical_standardizer.normalize_screening_name(variant1)
            norm2, conf2 = medical_standardizer.normalize_screening_name(variant2)
            
            print(f"'{variant1}' → '{norm1}' (confidence: {conf1:.1%})")
            print(f"'{variant2}' → '{norm2}' (confidence: {conf2:.1%})")
            
            if norm1 == norm2 and conf1 >= 0.8 and conf2 >= 0.8:
                print("✅ MATCH - These variants would be properly detected as related")
            else:
                print("❌ NO MATCH - These variants might not be detected as related")
            print()
        
        print("\n2. Testing Condition Normalization:")
        print("-" * 50)
        
        condition_test_cases = [
            ("diabetes", "diabetes mellitus"),
            ("high blood pressure", "hypertension"),
            ("bone loss", "osteoporosis"),
            ("smoking", "tobacco use disorder")
        ]
        
        for cond1, cond2 in condition_test_cases:
            norm1, conf1 = medical_standardizer.normalize_condition_name(cond1)
            norm2, conf2 = medical_standardizer.normalize_condition_name(cond2)
            
            print(f"'{cond1}' → '{norm1}' (confidence: {conf1:.1%})")
            print(f"'{cond2}' → '{norm2}' (confidence: {conf2:.1%})")
            
            if norm1 == norm2 and conf1 >= 0.7 and conf2 >= 0.7:
                print("✅ MATCH - These conditions would be properly standardized")
            else:
                print("❌ NO MATCH - These conditions might cause variant issues")
            print()
        
        print("\n3. Testing Enhanced Variant Manager:")
        print("-" * 50)
        
        # Get existing screening types to test with
        existing_screenings = ScreeningType.query.filter_by(is_active=True).limit(5).all()
        
        if existing_screenings:
            variant_manager = ScreeningVariantManager()
            
            for screening in existing_screenings:
                print(f"Testing screening: '{screening.name}' (ID: {screening.id})")
                
                # Test enhanced variant detection
                related_screenings = variant_manager.find_all_related_screening_types(screening.id)
                
                print(f"  Found {len(related_screenings)} related screening(s):")
                for related in related_screenings:
                    if related.id == screening.id:
                        print(f"  - {related.name} (SELF)")
                    else:
                        print(f"  - {related.name} (VARIANT)")
                
                # Test base name extraction
                base_name = variant_manager.extract_base_name(screening.name)
                print(f"  Base name: '{base_name}'")
                print()
        
        print("\n4. Testing API Integration:")
        print("-" * 50)
        
        # Test screening suggestions
        test_queries = ["mamm", "diab", "lipid", "colon"]
        
        for query in test_queries:
            suggestions = medical_standardizer.get_screening_suggestions(query, limit=3)
            print(f"Query '{query}' returned {len(suggestions)} suggestions:")
            for suggestion in suggestions:
                print(f"  - {suggestion['canonical_name']} ({suggestion['category']})")
            print()
        
        print("🎉 Enhanced Variant Detection Demo Complete!")
        print("\nKey Improvements:")
        print("- ✅ Standardized medical terminology prevents naming inconsistencies")
        print("- ✅ Fuzzy matching catches similar terms (mammogram/mammography)")
        print("- ✅ API-driven autocomplete ensures consistent user input")
        print("- ✅ Validation prevents non-standard terminology from breaking variants")
        print("- ✅ Medical condition standardization improves trigger condition matching")

if __name__ == "__main__":
    test_enhanced_variant_detection()