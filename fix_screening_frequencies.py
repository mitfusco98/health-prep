
#!/usr/bin/env python3
"""
Fix Missing Screening Type Frequencies
Ensures all active screening types have proper frequency definitions
"""

from app import app, db
from models import ScreeningType, Screening

def fix_missing_frequencies():
    """Fix screening types that are missing frequency definitions"""
    
    with app.app_context():
        print("🔧 Fixing missing screening type frequencies...")
        
        # Get all active screening types
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        
        # Default frequencies for common screening types
        default_frequencies = {
            'Mammogram': {'number': 1, 'unit': 'years'},
            'Pap Smear': {'number': 3, 'unit': 'years'},
            'Colonoscopy': {'number': 10, 'unit': 'years'},
            'A1c': {'number': 6, 'unit': 'months'},
            'Lipid Panel': {'number': 1, 'unit': 'years'},
            'Blood Pressure Check': {'number': 1, 'unit': 'years'},
            'Vaccination History': {'number': 1, 'unit': 'years'},
            'Diabetes Management': {'number': 6, 'unit': 'months'},
            'Hypertension Monitoring': {'number': 3, 'unit': 'months'},
            'Cancer Risk Screening': {'number': 1, 'unit': 'years'},
            'Bone Density': {'number': 2, 'unit': 'years'},
            'Eye Exam': {'number': 2, 'unit': 'years'},
            'Skin Cancer Screening': {'number': 1, 'unit': 'years'},
            'Prostate Screening': {'number': 1, 'unit': 'years'},
            'Chest X-Ray': {'number': 1, 'unit': 'years'},
            'Depression Screening': {'number': 1, 'unit': 'years'},
            'Immunization Update': {'number': 1, 'unit': 'years'},
            'Annual Physical': {'number': 1, 'unit': 'years'},
            'Cardiac Risk Assessment': {'number': 1, 'unit': 'years'},
            'DEXA Scan': {'number': 2, 'unit': 'years'}
        }
        
        fixed_count = 0
        
        for screening_type in screening_types:
            needs_fix = False
            
            # Check if frequency is missing
            has_structured_frequency = (
                screening_type.frequency_number and 
                screening_type.frequency_unit and
                screening_type.frequency_number > 0
            )
            
            has_default_frequency = (
                screening_type.default_frequency and 
                screening_type.default_frequency.strip() and
                screening_type.default_frequency.lower() not in ['', 'none', 'null']
            )
            
            if not has_structured_frequency and not has_default_frequency:
                needs_fix = True
            
            if needs_fix:
                # Try to find a default frequency for this screening type
                if screening_type.name in default_frequencies:
                    freq = default_frequencies[screening_type.name]
                    screening_type.frequency_number = freq['number']
                    screening_type.frequency_unit = freq['unit']
                    screening_type.default_frequency = f"Every {freq['number']} {freq['unit']}" if freq['number'] > 1 else f"Every {freq['unit'][:-1]}"
                    print(f"✅ Fixed {screening_type.name}: {screening_type.default_frequency}")
                else:
                    # Set a reasonable default - annual screening
                    screening_type.frequency_number = 1
                    screening_type.frequency_unit = 'years'
                    screening_type.default_frequency = "Annual"
                    print(f"✅ Fixed {screening_type.name}: Annual (default)")
                
                fixed_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n✅ Fixed {fixed_count} screening types with missing frequencies")
        
        # Report on screening types that now have frequencies
        print("\n📋 Current screening types with frequencies:")
        for screening_type in ScreeningType.query.filter_by(is_active=True).all():
            if screening_type.frequency_number and screening_type.frequency_unit:
                freq_display = f"Every {screening_type.frequency_number} {screening_type.frequency_unit}" if screening_type.frequency_number > 1 else f"Every {screening_type.frequency_unit[:-1]}"
            else:
                freq_display = screening_type.default_frequency or "Not set"
            print(f"  • {screening_type.name}: {freq_display}")

def validate_existing_screenings():
    """Check existing patient screenings for frequency issues"""
    
    with app.app_context():
        print("\n🔍 Validating existing patient screenings...")
        
        # Get all current screenings
        screenings = Screening.query.all()
        screening_types_used = set(s.screening_type for s in screenings)
        
        print(f"Found {len(screenings)} patient screenings using {len(screening_types_used)} different screening types")
        
        # Check each screening type used
        missing_frequency_types = []
        for screening_type_name in screening_types_used:
            screening_type = ScreeningType.query.filter_by(name=screening_type_name).first()
            
            if not screening_type:
                print(f"⚠️  Screening type '{screening_type_name}' not found in ScreeningType table")
                continue
                
            has_structured_frequency = (
                screening_type.frequency_number and 
                screening_type.frequency_unit and
                screening_type.frequency_number > 0
            )
            
            has_default_frequency = (
                screening_type.default_frequency and 
                screening_type.default_frequency.strip() and
                screening_type.default_frequency.lower() not in ['', 'none', 'null']
            )
            
            if not has_structured_frequency and not has_default_frequency:
                missing_frequency_types.append(screening_type_name)
        
        if missing_frequency_types:
            print(f"\n❌ Found {len(missing_frequency_types)} screening types without frequencies:")
            for name in missing_frequency_types:
                patient_count = Screening.query.filter_by(screening_type=name).count()
                print(f"  • {name} (used by {patient_count} patients)")
        else:
            print("\n✅ All screening types in use have proper frequency definitions")

if __name__ == "__main__":
    print("🔧 Starting screening frequency fix...")
    fix_missing_frequencies()
    validate_existing_screenings()
    print("\n✅ Screening frequency fix completed!")
