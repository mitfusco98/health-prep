"""
Routes for EHR integration functionality
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from app import app, db, limiter
from models import Patient, EHRConnection, EHRImportHistory
import json
import logging
from datetime import datetime

from ehr_integration import (
    ehr_service, 
    fhir_service, 
    EHRConnectionConfig, 
    EHRVendor
)

# Configure logging
logger = logging.getLogger(__name__)


@app.route('/ehr')
def ehr_integration():
    """EHR integration main page - configure connections and import data"""
    # Get all configured connections
    connections = EHRConnection.query.all()
    
    # Format connection data for the template
    connection_data = []
    for conn in connections:
        connection_data.append({
            'id': conn.id,
            'name': conn.name,
            'vendor': conn.vendor,
            'base_url': conn.base_url
        })
    
    # Get import history
    import_history = EHRImportHistory.query.order_by(EHRImportHistory.import_date.desc()).limit(10).all()
    
    return render_template('ehr_integration.html', 
                         connections=connection_data,
                         import_history=import_history)


@app.route('/ehr/connections/add', methods=['POST'])
def add_ehr_connection():
    """Add a new EHR connection configuration"""
    try:
        name = request.form.get('name')
        vendor = request.form.get('vendor')
        base_url = request.form.get('base_url')
        auth_type = request.form.get('auth_type')
        
        # Validate required fields
        if not name or not vendor or not base_url or not auth_type:
            flash('Please fill out all required fields.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Check if connection name already exists
        existing_connection = EHRConnection.query.filter_by(name=name).first()
        if existing_connection:
            flash(f'A connection named "{name}" already exists.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Create new connection in database
        connection = EHRConnection(
            name=name,
            vendor=vendor,
            base_url=base_url,
            auth_type=auth_type
        )
        
        # Handle authentication details based on type
        if auth_type == 'api_key':
            api_key = request.form.get('api_key')
            use_auth_header = request.form.get('use_auth_header') == 'true'
            
            # Validate API key format and ensure it's not a service/admin key
            if api_key and validate_api_key_security(api_key):
                connection.api_key = api_key
                connection.use_auth_header = use_auth_header
            else:
                flash('Invalid API key format or service-level key detected. Use public/anon keys only.', 'danger')
                return redirect(url_for('ehr_integration'))
            
        elif auth_type == 'oauth':
            client_id = request.form.get('client_id')
            client_secret = request.form.get('client_secret')
            
            # Validate OAuth credentials
            if client_id and client_secret and validate_oauth_credentials(client_id, client_secret):
                connection.client_id = client_id
                connection.client_secret = client_secret
            else:
                flash('Invalid OAuth credentials format.', 'danger')
                return redirect(url_for('ehr_integration'))
        
        # Save to database
        db.session.add(connection)
        db.session.commit()
        
        # Add to service
        configure_connection_in_service(connection)
        
        flash(f'Connection "{name}" added successfully.', 'success')
        return redirect(url_for('ehr_integration'))
        
    except Exception as e:
        logger.error(f"Error adding EHR connection: {str(e)}")
        db.session.rollback()
        flash(f'Error adding connection: {str(e)}', 'danger')
        return redirect(url_for('ehr_integration'))


@app.route('/ehr/connections/remove', methods=['POST'])
def remove_ehr_connection():
    """Remove an EHR connection configuration"""
    try:
        connection_name = request.form.get('connection_name')
        
        if not connection_name:
            flash('Connection name is required.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Get connection from database
        connection = EHRConnection.query.filter_by(name=connection_name).first()
        
        if not connection:
            flash(f'Connection "{connection_name}" not found.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Remove connection
        db.session.delete(connection)
        db.session.commit()
        
        # Remove from service
        if connection_name in ehr_service.connections:
            ehr_service.remove_connection(connection_name)
        
        flash(f'Connection "{connection_name}" removed successfully.', 'success')
        return redirect(url_for('ehr_integration'))
        
    except Exception as e:
        logger.error(f"Error removing EHR connection: {str(e)}")
        db.session.rollback()
        flash(f'Error removing connection: {str(e)}', 'danger')
        return redirect(url_for('ehr_integration'))


@app.route('/ehr/connections/test', methods=['POST'])
def test_ehr_connection():
    """Test an EHR connection"""
    try:
        connection_name = request.form.get('connection_name')
        
        if not connection_name:
            flash('Connection name is required.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Get connection from database and configure service
        connection = EHRConnection.query.filter_by(name=connection_name).first()
        
        if not connection:
            flash(f'Connection "{connection_name}" not found.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Ensure connection is configured in service
        configure_connection_in_service(connection)
        
        # Test connection by making a simple API request
        # This will just check if the server is available and responding
        # and if authentication is working
        result = ehr_service.make_api_request(
            connection_name=connection.name,
            endpoint="metadata",  # FHIR server capability statement
            method="GET"
        )
        
        if result:
            flash(f'Connection "{connection_name}" tested successfully!', 'success')
        else:
            flash(f'Connection test failed. Please check your configuration and try again.', 'danger')
            
        return redirect(url_for('ehr_integration'))
        
    except Exception as e:
        logger.error(f"Error testing EHR connection: {str(e)}")
        flash(f'Error testing connection: {str(e)}', 'danger')
        return redirect(url_for('ehr_integration'))


@app.route('/ehr/search', methods=['GET', 'POST'])
@limiter.limit("30 per minute")  # Protect against automated scraping
def search_ehr_patients():
    """Search for patients in an EHR system"""
    if request.method == 'GET':
        # Just show the search form
        connections = EHRConnection.query.all()
        connection_names = [conn.name for conn in connections]
        
        return render_template('ehr_search_results.html',
                             connection_name="",
                             patients=[],
                             available_connections=connection_names)
    
    # Handle search request
    try:
        connection_name = request.form.get('connection_name')
        family_name = request.form.get('family_name')
        given_name = request.form.get('given_name')
        birthdate = request.form.get('birthdate')
        identifier = request.form.get('identifier')
        
        if not connection_name:
            flash('Please select an EHR connection.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Get connection from database
        connection = EHRConnection.query.filter_by(name=connection_name).first()
        
        if not connection:
            flash(f'Connection "{connection_name}" not found.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Ensure connection is configured in service
        configure_connection_in_service(connection)
        
        # Perform search
        patients = fhir_service.search_patients(
            connection_name=connection.name,
            family_name=family_name,
            given_name=given_name,
            birthdate=birthdate,
            identifier=identifier
        )
        
        # Get all connection names for the dropdown
        connections = EHRConnection.query.all()
        connection_names = [conn.name for conn in connections]
        
        return render_template('ehr_search_results.html',
                             connection_name=connection.name,
                             patients=patients or [],
                             available_connections=connection_names)
        
    except Exception as e:
        logger.error(f"Error searching EHR patients: {str(e)}")
        flash(f'Error searching patients: {str(e)}', 'danger')
        return redirect(url_for('ehr_integration'))


@app.route('/ehr/import', methods=['POST'])
def import_ehr_patient():
    """Import a patient and their data from an EHR system"""
    try:
        connection_name = request.form.get('connection_name')
        patient_id = request.form.get('patient_id')
        
        import_patient_data = request.form.get('import_patient') == 'true'
        import_conditions = request.form.get('import_conditions') == 'true'
        import_vitals = request.form.get('import_vitals') == 'true'
        import_documents = request.form.get('import_documents') == 'true'
        
        if not connection_name or not patient_id:
            flash('Connection name and patient ID are required.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Get connection from database
        connection = EHRConnection.query.filter_by(name=connection_name).first()
        
        if not connection:
            flash(f'Connection "{connection_name}" not found.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Ensure connection is configured in service
        configure_connection_in_service(connection)
        
        # Create import history record
        import_history = EHRImportHistory(
            connection_id=connection.id,
            ehr_patient_id=patient_id,
            imported_data_types=','.join(filter(None, [
                'patient' if import_patient_data else None,
                'conditions' if import_conditions else None,
                'vitals' if import_vitals else None,
                'documents' if import_documents else None
            ]))
        )
        
        # Get patient data from EHR
        fhir_patient_data = fhir_service.get_patient(
            connection_name=connection.name,
            patient_id=patient_id
        )
        
        if not fhir_patient_data:
            import_history.success = False
            import_history.error_message = f"Patient with ID {patient_id} not found in EHR system."
            db.session.add(import_history)
            db.session.commit()
            
            flash(f'Patient with ID {patient_id} not found in EHR system.', 'danger')
            return redirect(url_for('ehr_integration'))
        
        # Extract patient name for history record
        name = fhir_patient_data.get('name', [{}])[0]
        patient_name = f"{name.get('given', [''])[0] if name.get('given') else ''} {name.get('family', '')}"
        import_history.patient_name = patient_name.strip()
        
        # Initialize count of imported items
        imported_items = 0
        
        # Import patient demographics if requested
        patient = None
        if import_patient_data:
            patient = fhir_service.import_patient(
                connection_name=connection.name,
                fhir_patient=fhir_patient_data
            )
            
            if patient:
                import_history.patient_id = patient.id
                imported_items += 1
            else:
                import_history.success = False
                import_history.error_message = "Failed to import patient demographics."
                db.session.add(import_history)
                db.session.commit()
                
                flash('Failed to import patient demographics.', 'danger')
                return redirect(url_for('ehr_integration'))
        
        # Import conditions if requested
        if import_conditions and patient:
            conditions = fhir_service.get_conditions(
                connection_name=connection.name,
                patient_id=patient_id
            )
            
            if conditions:
                condition_count = fhir_service.import_conditions(
                    connection_name=connection.name,
                    patient=patient,
                    fhir_conditions=conditions
                )
                imported_items += condition_count
        
        # Import vital signs if requested
        if import_vitals and patient:
            observations = fhir_service.get_observations(
                connection_name=connection.name,
                patient_id=patient_id,
                category="vital-signs"
            )
            
            if observations:
                vitals_count = fhir_service.import_vital_signs(
                    connection_name=connection.name,
                    patient=patient,
                    fhir_observations=observations
                )
                imported_items += vitals_count
        
        # Import documents if requested
        if import_documents and patient:
            documents = fhir_service.get_documents(
                connection_name=connection.name,
                patient_id=patient_id
            )
            
            if documents:
                document_count = fhir_service.import_documents(
                    connection_name=connection.name,
                    patient=patient,
                    fhir_documents=documents
                )
                imported_items += document_count
        
        # Update import history
        import_history.imported_items = imported_items
        db.session.add(import_history)
        db.session.commit()
        
        # Redirect to patient page if we imported a patient
        if patient:
            flash(f'Successfully imported {imported_items} items for {patient.full_name}.', 'success')
            return redirect(url_for('patient_detail', patient_id=patient.id))
        else:
            flash(f'Successfully imported {imported_items} items.', 'success')
            return redirect(url_for('ehr_integration'))
        
    except Exception as e:
        logger.error(f"Error importing EHR patient: {str(e)}")
        db.session.rollback()
        flash(f'Error importing patient: {str(e)}', 'danger')
        return redirect(url_for('ehr_integration'))


def validate_api_key_security(api_key):
    """Validate that API key is not a service or admin-level key"""
    if not api_key:
        return False
    
    # Check for dangerous patterns that indicate service/admin keys
    dangerous_patterns = [
        'service_role', 'admin', 'root', 'super', 'master', 'secret',
        'sk_', 'rk_', 'service_', 'admin_', 'eyJ', 'bearer_'
    ]
    
    api_key_lower = api_key.lower()
    for pattern in dangerous_patterns:
        if pattern in api_key_lower:
            logger.warning(f"Dangerous API key pattern detected: {pattern}")
            return False
    
    # Check for overly permissive key lengths (service keys are often longer)
    if len(api_key) > 200:
        logger.warning(f"Suspicious API key length: {len(api_key)}")
        return False
    
    return True

def validate_oauth_credentials(client_id, client_secret):
    """Validate OAuth credentials are appropriate for client-side use"""
    if not client_id or not client_secret:
        return False
    
    # Check for service-level OAuth patterns
    dangerous_patterns = ['service', 'admin', 'root', 'confidential']
    
    for pattern in dangerous_patterns:
        if pattern in client_id.lower() or pattern in client_secret.lower():
            logger.warning(f"Service-level OAuth credential detected: {pattern}")
            return False
    
    return True

def mask_sensitive_data(value, mask_char='*', show_chars=4):
    """Mask sensitive data for logging/display"""
    if not value or len(value) <= show_chars:
        return mask_char * 8
    
    return value[:show_chars] + mask_char * (len(value) - show_chars)

def configure_connection_in_service(connection_db):
    """Configure an EHR connection in the service from database model"""
    # Map vendor string to enum
    vendor_map = {
        'Generic FHIR': EHRVendor.GENERIC_FHIR,
        'Epic': EHRVendor.EPIC,
        'Cerner': EHRVendor.CERNER,
        'Allscripts': EHRVendor.ALLSCRIPTS,
        'AthenaHealth': EHRVendor.ATHENAHEALTH,
        'eClinicalWorks': EHRVendor.ECLINICALWORKS,
        'NextGen': EHRVendor.NEXTGEN
    }
    
    vendor = vendor_map.get(connection_db.vendor, EHRVendor.GENERIC_FHIR)
    
    # Create connection config
    config = EHRConnectionConfig(
        name=connection_db.name,
        base_url=connection_db.base_url,
        vendor=vendor,
        use_auth_header=connection_db.use_auth_header
    )
    
    # Add authentication details based on type
    if connection_db.auth_type == 'api_key' and connection_db.api_key:
        config.api_key = connection_db.api_key
    elif connection_db.auth_type == 'oauth':
        config.client_id = connection_db.client_id
        config.client_secret = connection_db.client_secret
    
    # Add to service
    ehr_service.add_connection(config)
    
    return config


# Import all database connections on startup
def import_connections_on_startup():
    """Import all database connections into the EHR service on application startup"""
    with app.app_context():
        connections = EHRConnection.query.all()
        
        for connection in connections:
            try:
                configure_connection_in_service(connection)
                logger.info(f"Imported EHR connection: {connection.name}")
            except Exception as e:
                logger.error(f"Error importing EHR connection {connection.name}: {str(e)}")