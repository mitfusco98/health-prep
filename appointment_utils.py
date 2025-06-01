from datetime import datetime, timedelta, time
from app import db
from models import Appointment

# Appointment duration is now 15 minutes
DEFAULT_APPOINTMENT_DURATION = 15

def detect_appointment_conflicts(date, time_obj, duration_minutes=DEFAULT_APPOINTMENT_DURATION, appointment_id=None):
    """
    Detect conflicts with existing appointments
    
    Args:
        date: The date of the appointment
        time_obj: The time of the appointment (datetime.time object)
        duration_minutes: Duration of the appointment in minutes (default: 15)
        appointment_id: ID of the appointment being edited (to exclude from conflict check)
        
    Returns:
        list: List of conflicting appointments, empty if no conflicts
    """
    if not date or not time_obj:
        return []
    
    # Calculate the end time of this appointment
    start_dt = datetime.combine(date, time_obj)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    end_time = end_dt.time()
    
    # Query for appointments on the same day
    query = Appointment.query.filter(
        Appointment.appointment_date == date
    )
    
    # Exclude the current appointment if editing
    if appointment_id:
        query = query.filter(Appointment.id != appointment_id)
    
    # Get all appointments for the day
    day_appointments = query.all()
    
    # Check for time conflicts (15-minute appointments)
    conflicts = []
    for appt in day_appointments:
        # Calculate end time for existing appointment
        appt_start = datetime.combine(date, appt.appointment_time)
        appt_end = appt_start + timedelta(minutes=duration_minutes)
        
        # Check if appointments overlap
        # New appointment starts during existing appointment
        condition1 = (time_obj >= appt.appointment_time and time_obj < appt_end.time())
        # New appointment ends during existing appointment
        condition2 = (end_time > appt.appointment_time and end_time <= appt_end.time())
        # New appointment completely contains existing appointment
        condition3 = (time_obj <= appt.appointment_time and end_time >= appt_end.time())
        
        if condition1 or condition2 or condition3:
            conflicts.append(appt)
            
    return conflicts

def get_booked_time_slots(date, appointment_id=None, as_string=False):
    """
    Get all booked time slots for a given date
    
    Args:
        date: The date to check
        appointment_id: ID of an appointment to exclude (when editing)
        as_string: If True, return time slots as strings in format 'HH:MM'
        
    Returns:
        list: List of booked time slots (as datetime.time objects or strings)
    """
    # Query for appointments on the specified date
    query = Appointment.query.filter(
        Appointment.appointment_date == date
    )
    
    # Exclude the current appointment if editing
    if appointment_id:
        query = query.filter(Appointment.id != appointment_id)
    
    # Get all appointments for the day
    appointments = query.all()
    
    # Extract the time slots
    if as_string:
        # Return as 'HH:MM' strings
        return [appt.appointment_time.strftime('%H:%M') for appt in appointments]
    else:
        # Return as datetime.time objects
        return [appt.appointment_time for appt in appointments]

def get_available_time_slots(date, appointment_id=None):
    """
    Get all available 15-minute time slots between 8 AM and 4 PM for a given date
    
    Args:
        date: The date to check
        appointment_id: ID of an appointment to exclude (when editing)
        
    Returns:
        list: List of available time slots as strings in 'HH:MM' format
    """
    # Get booked time slots
    booked_slots = get_booked_time_slots(date, appointment_id, as_string=True)
    
    # Generate all possible time slots
    all_slots = []
    for hour in range(8, 16):  # 8 AM to 4 PM (16:00)
        for minute in [0, 15, 30, 45]:
            time_slot = f"{hour:02d}:{minute:02d}"
            all_slots.append(time_slot)
    
    # Filter out booked slots
    available_slots = [slot for slot in all_slots if slot not in booked_slots]
    
    return available_slots


def format_conflict_message(conflicts):
    """
    Format a user-friendly message about appointment conflicts
    
    Args:
        conflicts: List of conflicting Appointment objects
        
    Returns:
        str: Formatted message about conflicts
    """
    if not conflicts:
        return ""
    
    if len(conflicts) == 1:
        appt = conflicts[0]
        patient_name = appt.patient.full_name
        appt_time = appt.appointment_time.strftime('%I:%M %p')
        return f"This appointment conflicts with {patient_name}'s appointment at {appt_time}."
    else:
        conflict_times = [a.appointment_time.strftime('%I:%M %p') for a in conflicts]
        return f"This appointment conflicts with {len(conflicts)} existing appointments at: {', '.join(conflict_times)}."