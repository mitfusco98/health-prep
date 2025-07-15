
#!/usr/bin/env python3
"""
Fix missing frequency data in existing screening records
"""

from app import app, db
from models import Screening, ScreeningType

def fix_screening_frequencies():
    """Fix missing frequency data in existing screenings"""
    
    with app.app_context():
        print("🔧 Starting screening frequency data fix...")
        
        # Get all screenings without frequency data
        screenings_without_frequency = Screening.query.filter(
            (Screening.frequency == None) | (Screening.frequency == '') | (Screening.frequency == 'Not set')
        ).all()
        
        print(f"📋 Found {len(screenings_without_frequency)} screenings without frequency data")
        
        fixed_count = 0
        
        for screening in screenings_without_frequency:
            # Get the screening type
            screening_type = ScreeningType.query.filter_by(name=screening.screening_type).first()
            
            if screening_type:
                # Use formatted frequency first, then default frequency
                if screening_type.formatted_frequency:
                    screening.frequency = screening_type.formatted_frequency
                    print(f"  ✓ Fixed {screening.screening_type} for patient {screening.patient_id}: {screening.frequency}")
                    fixed_count += 1
                elif screening_type.default_frequency:
                    screening.frequency = screening_type.default_frequency
                    print(f"  ✓ Fixed {screening.screening_type} for patient {screening.patient_id}: {screening.frequency}")
                    fixed_count += 1
                else:
                    print(f"  ⚠️ No frequency defined for screening type: {screening.screening_type}")
            else:
                print(f"  ❌ Screening type not found: {screening.screening_type}")
        
        # Commit all changes
        if fixed_count > 0:
            try:
                db.session.commit()
                print(f"✅ Successfully fixed {fixed_count} screening frequency records")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error committing changes: {e}")
        else:
            print("ℹ️ No frequency data needed fixing")
        
        print("✅ Screening frequency fix completed!")

if __name__ == "__main__":
    fix_screening_frequencies()
