from flask import render_template, request, jsonify, redirect, url_for, flash
from app import app, db
from models import Patient, Condition, Vital
from forms import PatientForm, ConditionForm, VitalForm
from comprehensive_logging import log_patient_operation, log_data_modification