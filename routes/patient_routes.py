
from flask import render_template, request, jsonify, redirect, url_for, flash
from app import app, db
from models import Patient, Condition, Vital
from forms import PatientForm, ConditionForm, VitalForm
from comprehensive_logging import log_patient_operation, log_data_modification

@app.route('/patients')
def patient_list():
    patients = Patient.query.all()
    return render_template('patient_list.html', patients=patients)

@app.route('/patient/<int:id>')
@log_patient_operation('view')
def patient_detail(id):
    patient = Patient.query.get_or_404(id)
    return render_template('patient_detail.html', patient=patient)

@app.route('/edit_patient/<int:id>', methods=['GET', 'POST'])
@log_patient_operation('edit')
def edit_patient(id):
    patient = Patient.query.get_or_404(id)
    form = PatientForm(obj=patient)
    if form.validate_on_submit():
        form.populate_obj(patient)
        db.session.commit()
        flash('Patient updated successfully', 'success')
        return redirect(url_for('patient_detail', id=patient.id))
    return render_template('edit_patient.html', form=form, patient=patient)

@app.route('/delete_patient/<int:id>', methods=['POST'])
@log_patient_operation('delete')
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()
    flash('Patient deleted successfully', 'success')
    return redirect(url_for('patient_list'))

@app.route('/add_condition/<int:patient_id>', methods=['GET', 'POST'])
@log_data_modification('condition')
def add_condition(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = ConditionForm()
    if form.validate_on_submit():
        condition = Condition(
            name=form.name.data,
            patient_id=patient_id,
            date_of_diagnosis=form.date_of_diagnosis.data,
            note=form.note.data
        )
        db.session.add(condition)
        db.session.commit()
        flash('Condition added successfully', 'success')
        return redirect(url_for('patient_detail', id=patient_id))
    return render_template('add_condition.html', form=form, patient=patient)
