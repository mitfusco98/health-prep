#!/usr/bin/env python3
"""
Minimal working healthcare app to replace the complex broken one
"""

from flask import Flask, render_template, session, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
import os
import time
from datetime import datetime

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "healthcare-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///healthcare.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['PERMANENT_SESSION_LIFETIME'] = 600  # 10 minutes

# Initialize database
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date)
    sex = db.Column(db.String(10))
    mrn = db.Column(db.String(20), unique=True)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    insurance = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time)
    note = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    patient = db.relationship('Patient', backref='appointments')

# Login decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
@app.route('/home')
@login_required
def index():
    """Home page with basic dashboard"""
    try:
        patient_count = Patient.query.count()
        today = datetime.now().date()
        today_appointments = Appointment.query.filter_by(appointment_date=today).all()
        recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()

        return render_template('simple_index.html',
                             patient_count=patient_count,
                             today_appointments=today_appointments,
                             recent_patients=recent_patients,
                             current_date=today)
    except Exception as e:
        return f"<h1>Healthcare App</h1><p>Database not ready: {e}</p><p><a href='/setup'>Setup Database</a></p>"

@app.route('/patients')
@login_required
def patient_list():
    """Patient list"""
    try:
        patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
        return render_template('simple_patients.html', patients=patients)
    except Exception as e:
        return f"<h1>Patients</h1><p>Error: {e}</p><p><a href='/'>Home</a></p>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                session['last_activity'] = time.time()
                session.permanent = True
                flash('Login successful', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            flash(f'Login error: {e}', 'error')

    return render_template('simple_login.html')

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/setup')
def setup():
    """Setup database and create admin user"""
    try:
        db.create_all()

        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

        return "<h1>Setup Complete!</h1><p>Admin user: admin/admin123</p><p><a href='/login'>Login</a></p>"
    except Exception as e:
        return f"<h1>Setup Error</h1><p>{e}</p>"

# Create simple templates
def create_templates():
    """Create basic template files"""
    templates_dir = 'templates'
    os.makedirs(templates_dir, exist_ok=True)

    # Simple base template
    with open(f'{templates_dir}/simple_base.html', 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Healthcare App</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .nav { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
        .nav a { margin-right: 20px; text-decoration: none; }
        .alert { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    {% if session.user_id %}
    <div class="nav">
        <a href="/">Home</a>
        <a href="/patients">Patients</a>
        <span style="float: right;">
            Welcome {{ session.username }} | <a href="/logout">Logout</a>
        </span>
    </div>
    {% endif %}

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
</body>
</html>""")

    # Login template
    with open(f'{templates_dir}/simple_login.html', 'w') as f:
        f.write("""{% extends "simple_base.html" %}
{% block content %}
<h2>Login</h2>
<form method="post">
    <p>
        <label>Username:</label><br>
        <input name="username" value="admin" required>
    </p>
    <p>
        <label>Password:</label><br>
        <input name="password" type="password" value="admin123" required>
    </p>
    <p><input type="submit" value="Login"></p>
</form>
<p><small>Default: admin/admin123</small></p>
{% endblock %}""")

    # Index template
    with open(f'{templates_dir}/simple_index.html', 'w') as f:
        f.write("""{% extends "simple_base.html" %}
{% block content %}
<h1>Healthcare Dashboard</h1>
<div style="display: flex; gap: 20px; margin: 20px 0;">
    <div style="border: 1px solid #ddd; padding: 20px; border-radius: 5px;">
        <h3>{{ patient_count }}</h3>
        <p>Total Patients</p>
    </div>
    <div style="border: 1px solid #ddd; padding: 20px; border-radius: 5px;">
        <h3>{{ today_appointments|length }}</h3>
        <p>Today's Appointments</p>
    </div>
</div>

<h3>Recent Patients</h3>
<table>
    <tr><th>Name</th><th>MRN</th><th>Added</th></tr>
    {% for patient in recent_patients %}
    <tr>
        <td>{{ patient.first_name }} {{ patient.last_name }}</td>
        <td>{{ patient.mrn or 'N/A' }}</td>
        <td>{{ patient.created_at.strftime('%Y-%m-%d') if patient.created_at else 'N/A' }}</td>
    </tr>
    {% endfor %}
</table>
{% endblock %}""")

    # Patients template
    with open(f'{templates_dir}/simple_patients.html', 'w') as f:
        f.write("""{% extends "simple_base.html" %}
{% block content %}
<h1>Patients</h1>
<table>
    <tr><th>Name</th><th>DOB</th><th>MRN</th><th>Phone</th></tr>
    {% for patient in patients %}
    <tr>
        <td>{{ patient.first_name }} {{ patient.last_name }}</td>
        <td>{{ patient.date_of_birth or 'N/A' }}</td>
        <td>{{ patient.mrn or 'N/A' }}</td>
        <td>{{ patient.phone or 'N/A' }}</td>
    </tr>
    {% endfor %}
</table>
{% endblock %}""")

# Simple middleware initialization at startup
try:
    # Any middleware initialization can go here
    print("Middleware initialized at startup")
except Exception as e:
    print(f"Warning: Some middleware failed to initialize: {e}")

# Initialize app
with app.app_context():
    create_templates()
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == '__main__':
    print("Starting minimal healthcare app...")
    app.run(host='0.0.0.0', port=5000, debug=False)