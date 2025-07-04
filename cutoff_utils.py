"""
Utility functions for handling cutoff dates in prep sheet generation
"""

from datetime import datetime, timedelta
from models import ChecklistSettings, Appointment
from app import db

def get_cutoff_date_for_patient(patient_id, data_type=None):
    """
    Get the cutoff date for a specific patient based on checklist settings.
    
    Args:
        patient_id: The patient ID
        data_type: The type of medical data ('labs', 'imaging', 'consults', 'hospital')
    
    Returns:
        datetime: The cutoff date for filtering medical data
    """
    # Get checklist settings
    settings = ChecklistSettings.query.first()
    
    # If general cutoff_months is set and greater than 0, use that
    if settings and settings.cutoff_months and settings.cutoff_months > 0:
        cutoff_date = datetime.now() - timedelta(days=settings.cutoff_months * 30)
        return cutoff_date
    
    # If specific data type cutoff is set and no general cutoff, use specific cutoff
    if settings and data_type:
        cutoff_months = None
        if data_type == 'labs' and settings.labs_cutoff_months and settings.labs_cutoff_months > 0:
            cutoff_months = settings.labs_cutoff_months
        elif data_type == 'imaging' and settings.imaging_cutoff_months and settings.imaging_cutoff_months > 0:
            cutoff_months = settings.imaging_cutoff_months
        elif data_type == 'consults' and settings.consults_cutoff_months and settings.consults_cutoff_months > 0:
            cutoff_months = settings.consults_cutoff_months
        elif data_type == 'hospital' and settings.hospital_cutoff_months and settings.hospital_cutoff_months > 0:
            cutoff_months = settings.hospital_cutoff_months
        
        if cutoff_months and cutoff_months > 0:
            cutoff_date = datetime.now() - timedelta(days=cutoff_months * 30)
            return cutoff_date
    
    # Fallback: Use last appointment date for the specific patient (excluding today's appointments)
    today = datetime.now().date()
    last_appointment = db.session.query(Appointment)\
        .filter(Appointment.patient_id == patient_id)\
        .filter(Appointment.appointment_date < today)\
        .order_by(Appointment.appointment_date.desc())\
        .first()
    
    if last_appointment and last_appointment.appointment_date:
        # Convert date to datetime at start of day
        return datetime.combine(last_appointment.appointment_date, datetime.min.time())
    
    # Final fallback: Use 6 months ago if no past appointments found
    return datetime.now() - timedelta(days=180)

def filter_medical_data_by_cutoff(data_list, patient_id, data_type, date_field='date'):
    """
    Filter a list of medical data objects by the appropriate cutoff date.
    
    Args:
        data_list: List of medical data objects
        patient_id: The patient ID
        data_type: The type of medical data ('labs', 'imaging', 'consults', 'hospital')
        date_field: The name of the date field in the data objects
    
    Returns:
        list: Filtered list of medical data objects
    """
    cutoff_date = get_cutoff_date_for_patient(patient_id, data_type)
    
    filtered_data = []
    for item in data_list:
        # Get the date value from the object
        if hasattr(item, date_field):
            item_date = getattr(item, date_field)
            
            # Convert date to datetime if necessary
            if item_date and hasattr(item_date, 'date'):
                # It's already a datetime object
                item_datetime = item_date
            elif item_date:
                # It's a date object, convert to datetime
                item_datetime = datetime.combine(item_date, datetime.min.time())
            else:
                # No date, skip this item
                continue
            
            # Include item if it's newer than the cutoff date
            if item_datetime >= cutoff_date:
                filtered_data.append(item)
    
    return filtered_data

def get_cutoff_info_for_patient(patient_id):
    """
    Get information about the cutoff settings being used for a patient.
    
    Args:
        patient_id: The patient ID
    
    Returns:
        dict: Information about cutoff settings
    """
    settings = ChecklistSettings.query.first()
    info = {
        'has_general_cutoff': bool(settings and settings.cutoff_months),
        'general_cutoff_months': settings.cutoff_months if settings else None,
        'specific_cutoffs': {},
        'using_appointment_fallback': False,
        'last_appointment_date': None
    }
    
    if settings:
        info['specific_cutoffs'] = {
            'labs': settings.labs_cutoff_months,
            'imaging': settings.imaging_cutoff_months,
            'consults': settings.consults_cutoff_months,
            'hospital': settings.hospital_cutoff_months
        }
    
    # Check if we're using appointment fallback (when cutoff_months is None, 0, or not set)
    if not (settings and settings.cutoff_months and settings.cutoff_months > 0):
        # Exclude today's appointments when finding the last appointment
        today = datetime.now().date()
        last_appointment = db.session.query(Appointment)\
            .filter(Appointment.patient_id == patient_id)\
            .filter(Appointment.appointment_date < today)\
            .order_by(Appointment.appointment_date.desc())\
            .first()
        
        if last_appointment:
            info['using_appointment_fallback'] = True
            info['last_appointment_date'] = last_appointment.appointment_date.strftime('%Y-%m-%d')
    
    return info