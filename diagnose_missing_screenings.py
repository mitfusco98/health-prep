#!/usr/bin/env python3
"""
Diagnostic script to identify why patients are missing expected screenings
"""

from app import app, db
from models import Patient, ScreeningType, Screening
from automated_screening_engine import ScreeningStatusEngine
from organized.utils.helper_screening_rules import apply_screening_rules

def diagnose_patient_screenings(patient_name_or_id):
    """
    Comprehensive diagnosis of why a patient might be missing screenings

    Args:
        patient_name_or_id: Patient name (string) or ID (int)
    """
    with app.app_context():
        # Find patient
        if isinstance(patient_name_or_id, str):
            # Try to find patient by name or ID
            if patient_name_or_id.isdigit():
                patient = Patient.query.get(int(patient_name_or_id))
            else:
                # Search by first name, last name, or concatenated full name
                from sqlalchemy import func
                patient = Patient.query.filter(
                    db.or_(
                        Patient.first_name.ilike(f"%{patient_name_or_id}%"),
                        Patient.last_name.ilike(f"%{patient_name_or_id}%"),
                        func.concat(Patient.first_name, ' ', Patient.last_name).ilike(f"%{patient_name_or_id}%")
                    )
                ).first()
        else:
            patient = Patient.query.get(patient_name_or_id)

        if not patient:
            print(f"❌ Patient '{patient_name_or_id}' not found")
            return

        print(f"\n🔍 SCREENING DIAGNOSIS FOR: {patient.full_name}")
        print(f"   Age: {patient.age}, Gender: {patient.sex}")
        print("=" * 60)

        # 1. Check current screenings
        current_screenings = Screening.query.filter_by(patient_id=patient.id).all()
        print(f"\n📋 CURRENT SCREENINGS ({len(current_screenings)}):")
        if current_screenings:
            for screening in current_screenings:
                print(f"   • {screening.screening_type} - {screening.status}")
        else:
            print("   ❌ No screenings found")

        # 2. Check all screening types and eligibility
        all_screening_types = ScreeningType.query.filter_by(is_active=True).all()
        print(f"\n🎯 SCREENING TYPE ELIGIBILITY ({len(all_screening_types)} total):")

        engine = ScreeningStatusEngine()
        eligible_count = 0
        ineligible_reasons = []

        for screening_type in all_screening_types:
            # Check frequency validity
            has_valid_freq = engine._has_valid_frequency(screening_type)

            # Check demographic eligibility
            is_eligible = engine._patient_qualifies_for_screening(patient, screening_type)

            if is_eligible and has_valid_freq:
                eligible_count += 1
                print(f"   ✅ {screening_type.name}")
                print(f"      Age range: {screening_type.min_age}-{screening_type.max_age}")
                print(f"      Gender: {screening_type.gender_specific or 'Any'}")
                print(f"      Frequency: {screening_type.frequency_number} {screening_type.frequency_unit}")
            else:
                reasons = []
                if not has_valid_freq:
                    reasons.append("No valid frequency")
                if screening_type.min_age and patient.age < screening_type.min_age:
                    reasons.append(f"Too young (min: {screening_type.min_age})")
                if screening_type.max_age and patient.age > screening_type.max_age:
                    reasons.append(f"Too old (max: {screening_type.max_age})")
                if screening_type.gender_specific and patient.sex.lower() != screening_type.gender_specific.lower():
                    reasons.append(f"Gender mismatch (needs: {screening_type.gender_specific})")

                reason_str = ", ".join(reasons)
                print(f"   ❌ {screening_type.name} - {reason_str}")
                ineligible_reasons.append((screening_type.name, reason_str))

        print(f"\n📊 ELIGIBILITY SUMMARY:")
        print(f"   Eligible: {eligible_count}")
        print(f"   Ineligible: {len(all_screening_types) - eligible_count}")

        # 3. Test automated screening engine
        print(f"\n🤖 AUTOMATED SCREENING ENGINE TEST:")
        try:
            generated_screenings = engine.generate_patient_screenings(patient.id)
            print(f"   Generated: {len(generated_screenings)} screenings")

            for screening in generated_screenings:
                print(f"   • {screening['screening_type']}: {screening['status']}")
                print(f"     Due: {screening['due_date']}")
                print(f"     Frequency: {screening['frequency']}")
                print(f"     Matching docs: {screening['matching_documents']}")
        except Exception as e:
            print(f"   ❌ Engine error: {str(e)}")

        # 4. Test helper screening rules
        print(f"\n📏 HELPER SCREENING RULES TEST:")
        try:
            # Get patient conditions
            conditions = patient.conditions
            condition_names = [c.name.lower() for c in conditions]
            print(f"   Patient conditions: {condition_names}")

            # Apply screening rules
            recommendations = apply_screening_rules(patient, condition_names)
            print(f"   Rule-based recommendations: {len(recommendations)}")

            for rec in recommendations[:5]:  # Show first 5
                print(f"   • {rec['type']}: {rec['priority']} priority")
                print(f"     Due: {rec['due_date']}")
                print(f"     Frequency: {rec['frequency']}")
        except Exception as e:
            print(f"   ❌ Rules error: {str(e)}")

        # 5. Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if eligible_count == 0:
            print("   • Check screening type age/gender requirements")
            print("   • Verify screening type frequencies are properly configured")
        elif len(current_screenings) == 0:
            print("   • Run automated screening generation")
            print("   • Check if screening engine is being called after patient creation")
        else:
            print("   • Patient seems to have appropriate screenings")

def fix_missing_screenings_for_patient(patient_id):
    """Generate missing screenings for a specific patient"""
    with app.app_context():
        engine = ScreeningStatusEngine()
        generated = engine.generate_patient_screenings(patient_id)

        print(f"Generated {len(generated)} screenings for patient {patient_id}")

        # Create screening records
        for screening_data in generated:
            existing = Screening.query.filter_by(
                patient_id=patient_id,
                screening_type=screening_data['screening_type']
            ).first()

            if not existing:
                new_screening = Screening(
                    patient_id=patient_id,
                    screening_type=screening_data['screening_type'],
                    status=screening_data['status'],
                    due_date=screening_data['due_date'],
                    last_completed=screening_data['last_completed'],
                    frequency=screening_data['frequency'],
                    notes=screening_data['notes']
                )
                db.session.add(new_screening)

        db.session.commit()
        print("✅ Screening records created/updated")

def fix_all_missing_screenings():
    """Generate missing screenings for all patients"""
    with app.app_context():
        patients = Patient.query.all()
        engine = ScreeningStatusEngine()

        for patient in patients:
            print(f"Processing {patient.full_name}...")
            generated = engine.generate_patient_screenings(patient.id)

            for screening_data in generated:
                existing = Screening.query.filter_by(
                    patient_id=patient.id,
                    screening_type=screening_data['screening_type']
                ).first()

                if not existing:
                    new_screening = Screening(
                        patient_id=patient.id,
                        screening_type=screening_data['screening_type'],
                        status=screening_data['status'],
                        due_date=screening_data['due_date'],
                        last_completed=screening_data['last_completed'],
                        frequency=screening_data['frequency'],
                        notes=screening_data['notes']
                    )
                    db.session.add(new_screening)

        db.session.commit()
        print("✅ All patient screenings updated")

def diagnose_all_patients():
    """
    Run screening diagnosis for all patients in the database
    """
    with app.app_context():
        patients = Patient.query.all()
        print(f"\n🔍 SCREENING DIAGNOSIS FOR ALL PATIENTS ({len(patients)} total)")
        print("=" * 80)
        
        summary_stats = {
            'total_patients': len(patients),
            'patients_with_screenings': 0,
            'patients_without_screenings': 0,
            'total_eligible_screenings': 0,
            'patients_by_eligibility': {}
        }
        
        for i, patient in enumerate(patients, 1):
            print(f"\n[{i}/{len(patients)}] 👤 {patient.full_name} (Age: {patient.age}, Gender: {patient.sex})")
            
            # Check current screenings
            current_screenings = Screening.query.filter_by(patient_id=patient.id).all()
            has_screenings = len(current_screenings) > 0
            
            if has_screenings:
                summary_stats['patients_with_screenings'] += 1
                print(f"   📋 Current screenings: {len(current_screenings)}")
            else:
                summary_stats['patients_without_screenings'] += 1
                print(f"   📋 Current screenings: 0")
            
            # Check eligibility for all screening types
            all_screening_types = ScreeningType.query.filter_by(is_active=True).all()
            engine = ScreeningStatusEngine()
            eligible_count = 0
            eligible_types = []
            
            for screening_type in all_screening_types:
                has_valid_freq = engine._has_valid_frequency(screening_type)
                is_eligible = engine._patient_qualifies_for_screening(patient, screening_type)
                
                if is_eligible and has_valid_freq:
                    eligible_count += 1
                    eligible_types.append(screening_type.name)
            
            summary_stats['total_eligible_screenings'] += eligible_count
            eligibility_key = f"{eligible_count}_eligible"
            summary_stats['patients_by_eligibility'][eligibility_key] = summary_stats['patients_by_eligibility'].get(eligibility_key, 0) + 1
            
            if eligible_count > 0:
                print(f"   ✅ Eligible for {eligible_count} screenings: {', '.join(eligible_types[:3])}{'...' if len(eligible_types) > 3 else ''}")
            else:
                print(f"   ❌ Eligible for 0 screenings")
                
        # Print summary
        print(f"\n" + "="*80)
        print(f"📊 OVERALL SUMMARY")
        print(f"   Total patients: {summary_stats['total_patients']}")
        print(f"   Patients with screenings: {summary_stats['patients_with_screenings']}")
        print(f"   Patients without screenings: {summary_stats['patients_without_screenings']}")
        print(f"   Average eligible screenings per patient: {summary_stats['total_eligible_screenings'] / summary_stats['total_patients']:.1f}")
        
        print(f"\n📈 ELIGIBILITY BREAKDOWN:")
        for eligibility, count in sorted(summary_stats['patients_by_eligibility'].items()):
            eligible_num = eligibility.split('_')[0]
            print(f"   {count} patients eligible for {eligible_num} screenings")

if __name__ == "__main__":
    # Run diagnosis for all patients
    diagnose_all_patients()
    
    print("\n" + "="*60)
    print("To diagnose a specific patient:")
    print("diagnose_patient_screenings('Patient Name')")
    print("\nTo generate missing screenings:")
    print("fix_missing_screenings_for_patient(patient_id)")
    print("fix_all_missing_screenings()")