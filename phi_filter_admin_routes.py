"""
PHI Filter Administration Routes
Provides admin interface for configuring PHI filtering settings
"""

from flask import render_template, request, flash, redirect, url_for, jsonify
from app import app, db
from phi_filter import phi_filter, PHIFilterConfig
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@app.route('/admin/phi-filter-settings')
def phi_filter_settings():
    """PHI filter configuration page"""
    try:
        # Get current filter statistics and configuration
        filter_stats = phi_filter.get_filter_statistics()
        
        return render_template('admin/phi_filter_settings.html', 
                             stats=filter_stats['stats'],
                             config=filter_stats['config'])
    
    except Exception as e:
        logger.error(f"PHI filter settings page error: {e}")
        flash(f"Error loading PHI filter settings: {str(e)}", "error")
        return redirect(url_for('index'))


@app.route('/admin/phi-filter-settings/update', methods=['POST'])
def update_phi_filter_settings():
    """Update PHI filter configuration"""
    try:
        # Get form data
        ssn_filtering = request.form.get('filter_ssn') == 'on'
        phone_filtering = request.form.get('filter_phone') == 'on'
        date_filtering = request.form.get('filter_dates') == 'on'
        address_filtering = request.form.get('filter_addresses') == 'on'
        name_filtering = request.form.get('filter_names') == 'on'
        mrn_filtering = request.form.get('filter_mrn') == 'on'
        insurance_filtering = request.form.get('filter_insurance') == 'on'
        
        # Update PHI filter configuration
        phi_filter.config.filter_ssn = ssn_filtering
        phi_filter.config.filter_phone = phone_filtering
        phi_filter.config.filter_dates = date_filtering
        phi_filter.config.filter_addresses = address_filtering
        phi_filter.config.filter_names = name_filtering
        phi_filter.config.filter_mrn = mrn_filtering
        phi_filter.config.filter_insurance = insurance_filtering
        
        # Update OCR processor configuration
        from ocr_document_processor import ocr_processor
        if hasattr(ocr_processor, 'phi_filter'):
            ocr_processor.phi_filter = phi_filter
        
        flash("PHI filter settings updated successfully", "success")
        logger.info("PHI filter configuration updated by admin")
        
        return redirect(url_for('phi_filter_settings'))
        
    except Exception as e:
        logger.error(f"PHI filter settings update error: {e}")
        flash(f"Error updating PHI filter settings: {str(e)}", "error")
        return redirect(url_for('phi_filter_settings'))


@app.route('/admin/phi-filter-test', methods=['POST'])
def test_phi_filter():
    """Test PHI filtering with sample text"""
    try:
        test_text = request.json.get('text', '')
        
        if not test_text:
            return jsonify({'error': 'No text provided for testing'}), 400
        
        # Apply PHI filtering
        result = phi_filter.filter_text(test_text)
        
        return jsonify({
            'success': True,
            'original_text': result['original_text'],
            'filtered_text': result['filtered_text'],
            'phi_count': result['phi_count'],
            'phi_detected': result['phi_detected'],
            'filter_applied': result['filter_applied']
        })
        
    except Exception as e:
        logger.error(f"PHI filter test error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/phi-filter-statistics/reset', methods=['POST'])
def reset_phi_filter_statistics():
    """Reset PHI filter statistics"""
    try:
        phi_filter.reset_statistics()
        flash("PHI filter statistics reset successfully", "success")
        logger.info("PHI filter statistics reset by admin")
        
        return redirect(url_for('phi_filter_settings'))
        
    except Exception as e:
        logger.error(f"PHI filter statistics reset error: {e}")
        flash(f"Error resetting PHI filter statistics: {str(e)}", "error")
        return redirect(url_for('phi_filter_settings'))


@app.route('/admin/phi-filter-export-config')
def export_phi_filter_config():
    """Export PHI filter configuration as JSON"""
    try:
        config_data = {
            'phi_filter_config': {
                'filter_ssn': phi_filter.config.filter_ssn,
                'filter_phone': phi_filter.config.filter_phone,
                'filter_dates': phi_filter.config.filter_dates,
                'filter_addresses': phi_filter.config.filter_addresses,
                'filter_names': phi_filter.config.filter_names,
                'filter_mrn': phi_filter.config.filter_mrn,
                'filter_insurance': phi_filter.config.filter_insurance,
                'redaction_token': phi_filter.config.redaction_token,
                'date_token': phi_filter.config.date_token,
                'name_token': phi_filter.config.name_token,
                'phone_token': phi_filter.config.phone_token,
                'address_token': phi_filter.config.address_token,
                'id_token': phi_filter.config.id_token
            },
            'export_timestamp': datetime.now().isoformat()
        }
        
        return jsonify(config_data)
        
    except Exception as e:
        logger.error(f"PHI filter config export error: {e}")
        return jsonify({'error': str(e)}), 500