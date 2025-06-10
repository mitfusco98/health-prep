from datetime import datetime, timedelta

def apply_screening_rules(patient, condition_names):
    """
    Apply screening rules to a patient based on demographics and conditions.
    Returns a list of recommended screenings.
    
    Args:
        patient: Patient object with demographics
        condition_names: List of patient's condition names (lowercase)
        
    Returns:
        list: List of dictionaries with screening recommendations
    """
    recommendations = []
    today = datetime.now().date()
    
    # Age of patient
    age = patient.age
    sex = patient.sex.lower()
    
    # Breast Cancer Screening
    if sex == 'female' and age >= 40:
        if age >= 55:
            # Biennial mammograms for women 55+
            recommendations.append({
                'type': 'Mammogram',
                'due_date': today,
                'frequency': 'Every 2 years',
                'priority': 'High',
                'notes': 'Recommended biennial screening for women 55 and older'
            })
        else:
            # Annual mammograms for women 40-54
            recommendations.append({
                'type': 'Mammogram',
                'due_date': today,
                'frequency': 'Annual',
                'priority': 'High',
                'notes': 'Recommended annual screening for women 40-54'
            })
    
    # Colorectal Cancer Screening
    if age >= 45 and age <= 75:
        recommendations.append({
            'type': 'Colorectal Cancer Screening',
            'due_date': today,
            'frequency': 'Every 10 years for colonoscopy',
            'priority': 'High',
            'notes': 'Options include: colonoscopy every 10 years, FIT test annually, or flexible sigmoidoscopy every 5 years'
        })
    
    # Cervical Cancer Screening
    if sex == 'female' and age >= 21 and age <= 65:
        if age < 30:
            recommendations.append({
                'type': 'Pap Test',
                'due_date': today,
                'frequency': 'Every 3 years',
                'priority': 'High',
                'notes': 'Recommended Pap test every 3 years for women 21-29'
            })
        else:
            recommendations.append({
                'type': 'Pap Test with HPV Test',
                'due_date': today,
                'frequency': 'Every 5 years',
                'priority': 'High',
                'notes': 'Recommended Pap and HPV co-testing every 5 years for women 30-65'
            })
    
    # Prostate Cancer Screening
    if sex == 'male' and age >= 50 and age <= 70:
        recommendations.append({
            'type': 'PSA Test',
            'due_date': today,
            'frequency': 'Discuss with provider',
            'priority': 'Medium',
            'notes': 'Consider PSA testing based on individual risk factors and after discussion of benefits and harms'
        })
    
    # Lipid Panel
    if age >= 40 or any(c in condition_names for c in ['diabetes', 'hypertension', 'heart disease', 'hyperlipidemia']):
        recommendations.append({
            'type': 'Lipid Panel',
            'due_date': today,
            'frequency': 'Annual',
            'priority': 'Medium',
            'notes': 'Recommended annually or more frequently based on risk factors'
        })
    
    # A1C for Diabetes
    if any(c in condition_names for c in ['diabetes', 'pre-diabetes', 'gestational diabetes']):
        frequency = 'Every 3 months' if 'diabetes' in condition_names else 'Every 6 months'
        recommendations.append({
            'type': 'A1C',
            'due_date': today,
            'frequency': frequency,
            'priority': 'High',
            'notes': 'Monitor glycemic control'
        })
    elif age >= 45 or any(c in condition_names for c in ['hypertension', 'obesity', 'pcos']):
        recommendations.append({
            'type': 'A1C',
            'due_date': today,
            'frequency': 'Annual',
            'priority': 'Medium',
            'notes': 'Screening for diabetes in higher risk individuals'
        })
    
    # Blood Pressure Screening
    recommendations.append({
        'type': 'Blood Pressure Check',
        'due_date': today,
        'frequency': 'Annual',
        'priority': 'Medium',
        'notes': 'Recommended for all adults'
    })
    
    # Bone Density Screening
    if (sex == 'female' and age >= 65) or any(c in condition_names for c in ['osteoporosis', 'osteopenia']):
        recommendations.append({
            'type': 'Bone Density Scan',
            'due_date': today,
            'frequency': 'Every 2 years',
            'priority': 'Medium',
            'notes': 'Recommended for women 65+ or those with risk factors'
        })
    
    # Lung Cancer Screening
    if age >= 50 and age <= 80 and any(c in condition_names for c in ['smoking', 'tobacco use']):
        recommendations.append({
            'type': 'Low-Dose CT Scan',
            'due_date': today,
            'frequency': 'Annual',
            'priority': 'High',
            'notes': 'Recommended for adults 50-80 with significant smoking history'
        })
    
    # Abdominal Aortic Aneurysm Screening
    if sex == 'male' and age >= 65 and 'smoking' in condition_names:
        recommendations.append({
            'type': 'Abdominal Ultrasound',
            'due_date': today,
            'frequency': 'Once',
            'priority': 'Medium',
            'notes': 'One-time screening for men 65-75 who have ever smoked'
        })
    
    # Skin Cancer Screening
    if any(c in condition_names for c in ['skin cancer', 'melanoma']):
        recommendations.append({
            'type': 'Skin Exam',
            'due_date': today,
            'frequency': 'Annual',
            'priority': 'Medium',
            'notes': 'Recommended annually for those with history of skin cancer'
        })
    
    # Hepatitis C Screening
    if age >= 18 and age <= 79:
        recommendations.append({
            'type': 'Hepatitis C Test',
            'due_date': today,
            'frequency': 'Once',
            'priority': 'Low',
            'notes': 'One-time screening for all adults born between 1945 and 1965'
        })
    
    # Depression Screening
    recommendations.append({
        'type': 'Depression Screening',
        'due_date': today,
        'frequency': 'Annual',
        'priority': 'Medium',
        'notes': 'Recommended for all adults'
    })
    
    # Immunizations
    recommendations.append({
        'type': 'Influenza Vaccine',
        'due_date': today,
        'frequency': 'Annual',
        'priority': 'Medium',
        'notes': 'Recommended annually for all adults'
    })
    
    if age >= 50:
        recommendations.append({
            'type': 'Shingles Vaccine',
            'due_date': today,
            'frequency': 'Once',
            'priority': 'Medium',
            'notes': 'Recommended for adults 50+'
        })
        
    if age >= 65:
        recommendations.append({
            'type': 'Pneumococcal Vaccine',
            'due_date': today,
            'frequency': 'Once',
            'priority': 'Medium',
            'notes': 'Recommended for adults 65+'
        })
    
    # Set appropriate due dates based on frequency
    for rec in recommendations:
        # If frequency is annual and we're creating a new recommendation
        if rec['frequency'] == 'Annual':
            rec['due_date'] = today
        elif rec['frequency'] == 'Every 3 months':
            rec['due_date'] = today + timedelta(days=91)
        elif rec['frequency'] == 'Every 6 months':
            rec['due_date'] = today + timedelta(days=182)
        elif rec['frequency'] == 'Every 2 years':
            rec['due_date'] = today.replace(year=today.year + 2)
        elif rec['frequency'] == 'Every 3 years':
            rec['due_date'] = today.replace(year=today.year + 3)
        elif rec['frequency'] == 'Every 5 years':
            rec['due_date'] = today.replace(year=today.year + 5)
        elif rec['frequency'] == 'Every 10 years':
            rec['due_date'] = today.replace(year=today.year + 10)
    
    return recommendations
