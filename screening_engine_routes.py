"""
Screening Engine Routes - API endpoints for the screening recommendation engine
"""

from flask import request, jsonify, render_template, flash, redirect, url_for
from datetime import datetime
import json

from app import app
from screening_engine import ScreeningEngine, run_screening_engine_for_patient, run_screening_engine_for_all_patients
from models import Patient, ScreeningType, Condition, Screening, db


@app.route("/api/screening-engine/evaluate/<int:patient_id>", methods=["POST"])
def api_evaluate_patient_screening(patient_id):
    """
    API endpoint to evaluate screening recommendations for a specific patient
    """
    try:
        result = run_screening_engine_for_patient(patient_id)
        
        return jsonify({
            'success': True,
            'data': result,
            'message': f"Generated {result['recommendations_count']} recommendations, created {result['created_count']} new screenings"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error evaluating patient screening recommendations'
        }), 500


@app.route("/api/screening-engine/evaluate-all", methods=["POST"])
def api_evaluate_all_patients_screening():
    """
    API endpoint to evaluate screening recommendations for all patients
    """
    try:
        result = run_screening_engine_for_all_patients()
        
        return jsonify({
            'success': True,
            'data': result,
            'message': f"Evaluated {result['total_patients_evaluated']} patients, "
                      f"generated {result['total_recommendations']} recommendations, "
                      f"created {result['total_created']} new screenings"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error evaluating screening recommendations for all patients'
        }), 500


@app.route("/screening-engine")
def screening_engine_dashboard():
    """
    Dashboard for the screening recommendation engine
    """
    # Get statistics
    total_patients = Patient.query.count()
    total_screening_types = ScreeningType.query.filter_by(is_active=True).count()
    screening_types_with_triggers = len([
        st for st in ScreeningType.query.filter_by(is_active=True).all()
        if st.get_trigger_conditions()
    ])
    total_conditions = Condition.query.filter_by(is_active=True).count()
    total_screenings = Screening.query.count()
    
    # Get recent screening recommendations (created in last 7 days)
    from datetime import datetime, timedelta
    recent_date = datetime.now() - timedelta(days=7)
    recent_screenings = Screening.query.filter(
        Screening.created_at >= recent_date
    ).order_by(Screening.created_at.desc()).limit(10).all()
    
    # Get screening types with trigger conditions for display
    screening_types_with_triggers_list = [
        {
            'id': st.id,
            'name': st.name,
            'trigger_conditions': st.get_trigger_conditions(),
            'condition_count': len(st.get_trigger_conditions())
        }
        for st in ScreeningType.query.filter_by(is_active=True).all()
        if st.get_trigger_conditions()
    ]
    
    return render_template(
        'screening_engine_dashboard.html',
        total_patients=total_patients,
        total_screening_types=total_screening_types,
        screening_types_with_triggers=screening_types_with_triggers,
        total_conditions=total_conditions,
        total_screenings=total_screenings,
        recent_screenings=recent_screenings,
        screening_types_with_triggers_list=screening_types_with_triggers_list
    )


@app.route("/screening-engine/run", methods=["POST"])
def run_screening_engine():
    """
    Manual trigger to run the screening engine for all patients
    """
    try:
        patient_id = request.form.get('patient_id')
        
        if patient_id:
            # Run for specific patient
            result = run_screening_engine_for_patient(int(patient_id))
            flash(
                f"Screening engine completed for patient {patient_id}. "
                f"Generated {result['recommendations_count']} recommendations, "
                f"created {result['created_count']} new screenings.",
                "success"
            )
        else:
            # Run for all patients
            result = run_screening_engine_for_all_patients()
            flash(
                f"Screening engine completed. Evaluated {result['total_patients_evaluated']} patients, "
                f"generated {result['total_recommendations']} recommendations, "
                f"created {result['total_created']} new screenings.",
                "success"
            )
        
    except Exception as e:
        flash(f"Error running screening engine: {str(e)}", "danger")
    
    return redirect(url_for('screening_engine_dashboard'))


@app.route("/api/screening-engine/test-condition-matching", methods=["POST"])
def api_test_condition_matching():
    """
    Test endpoint to check which screening types would be triggered by a condition
    """
    try:
        data = request.get_json()
        condition_code = data.get('condition_code')
        condition_name = data.get('condition_name') 
        condition_system = data.get('condition_system')
        
        if not condition_code and not condition_name:
            return jsonify({
                'success': False,
                'message': 'Either condition_code or condition_name is required'
            }), 400
        
        # Create a temporary condition object for testing
        test_condition = type('TestCondition', (), {
            'code': condition_code,
            'name': condition_name
        })()
        
        engine = ScreeningEngine()
        screening_types = ScreeningType.query.filter_by(is_active=True).all()
        screening_types_with_triggers = [
            st for st in screening_types 
            if st.get_trigger_conditions()
        ]
        
        matching_screenings = engine._find_matching_screenings(
            test_condition, screening_types_with_triggers
        )
        
        results = [
            {
                'id': st.id,
                'name': st.name,
                'trigger_conditions': st.get_trigger_conditions()
            }
            for st in matching_screenings
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'test_condition': {
                    'code': condition_code,
                    'name': condition_name,
                    'system': condition_system
                },
                'matching_screenings': results,
                'match_count': len(results)
            },
            'message': f"Found {len(results)} matching screening types"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error testing condition matching'
        }), 500


@app.route("/api/screening-engine/patient-conditions/<int:patient_id>")
def api_get_patient_conditions(patient_id):
    """
    Get patient conditions and potential screening matches
    """
    try:
        patient = Patient.query.get_or_404(patient_id)
        conditions = Condition.query.filter_by(
            patient_id=patient_id,
            is_active=True
        ).all()
        
        engine = ScreeningEngine()
        condition_analysis = []
        
        for condition in conditions:
            screening_types = ScreeningType.query.filter_by(is_active=True).all()
            screening_types_with_triggers = [
                st for st in screening_types 
                if st.get_trigger_conditions()
            ]
            
            matching_screenings = engine._find_matching_screenings(
                condition, screening_types_with_triggers
            )
            
            condition_analysis.append({
                'condition': {
                    'id': condition.id,
                    'name': condition.name,
                    'code': condition.code,
                    'diagnosed_date': condition.diagnosed_date.isoformat() if condition.diagnosed_date else None,
                    'is_active': condition.is_active
                },
                'matching_screenings': [
                    {
                        'id': st.id,
                        'name': st.name,
                        'frequency': st.formatted_frequency
                    }
                    for st in matching_screenings
                ],
                'match_count': len(matching_screenings)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'patient': {
                    'id': patient.id,
                    'name': f"{patient.first_name} {patient.last_name}"
                },
                'conditions_analysis': condition_analysis,
                'total_conditions': len(conditions),
                'total_potential_screenings': sum(ca['match_count'] for ca in condition_analysis)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error analyzing patient conditions'
        }), 500