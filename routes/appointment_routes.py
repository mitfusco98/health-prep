
from flask import render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, date, time
from app import app, db
from models import Appointment, Patient
from forms import AppointmentForm
from comprehensive_logging import log_data_modification

@app.route('/appointments')
def appointment_list():
    today = date.today()
    appointments = Appointment.query.filter_by(appointment_date=today).all()
    return render_template('appointment_list.html', appointments=appointments)

@app.route('/add_appointment', methods=['GET', 'POST'])
@log_data_modification('appointment')
def add_appointment():
    form = AppointmentForm()
    if form.validate_on_submit():
        appointment = Appointment(
            patient_id=form.patient_id.data,
            appointment_date=form.appointment_date.data,
            appointment_time=form.appointment_time.data,
            note=form.note.data
        )
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment added successfully', 'success')
        return redirect(url_for('appointment_list'))
    return render_template('appointment_form.html', form=form)

@app.route('/edit_appointment/<int:id>', methods=['GET', 'POST'])
@log_data_modification('appointment')
def edit_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    form = AppointmentForm(obj=appointment)
    if form.validate_on_submit():
        form.populate_obj(appointment)
        db.session.commit()
        flash('Appointment updated successfully', 'success')
        return redirect(url_for('appointment_list'))
    return render_template('appointment_form.html', form=form, appointment=appointment)

@app.route('/delete_appointment/<int:id>', methods=['POST'])
@log_data_modification('appointment')
def delete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment deleted successfully', 'success')
    return redirect(url_for('appointment_list'))
