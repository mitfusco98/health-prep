
"""
Utilities for log aggregation and machine parsing support.
Provides helpers for common log analysis patterns.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from structured_logger import structured_logger

class LogAggregationHelper:
    """Helper class for log aggregation and analysis"""
    
    @staticmethod
    def create_metric_log(metric_name: str, metric_value: float, unit: str = 'count', 
                         tags: Optional[Dict[str, str]] = None, **kwargs):
        """Create a standardized metric log entry for monitoring systems"""
        structured_logger.info(
            f"Metric: {metric_name}",
            event_category='metric',
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=unit,
            metric_tags=tags or {},
            **kwargs
        )
    
    @staticmethod
    def create_business_kpi_log(kpi_name: str, value: Any, period: str = 'realtime', **kwargs):
        """Create standardized business KPI logs"""
        structured_logger.business_event(
            'kpi_measurement',
            f"KPI {kpi_name}: {value}",
            kpi_name=kpi_name,
            kpi_value=value,
            measurement_period=period,
            measurement_timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    @staticmethod
    def create_error_trend_log(error_type: str, error_count: int, time_window: str, **kwargs):
        """Create logs for error trend analysis"""
        structured_logger.error(
            f"Error trend: {error_type}",
            event_category='error_trend',
            error_type=error_type,
            error_count=error_count,
            time_window=time_window,
            trend_timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    @staticmethod
    def create_user_journey_log(step: str, user_id: str, session_id: str, 
                               duration_ms: Optional[float] = None, **kwargs):
        """Create standardized user journey logs for analytics"""
        log_data = {
            'event_category': 'user_journey',
            'journey_step': step,
            'user_id': user_id,
            'session_id': session_id,
            'step_timestamp': datetime.utcnow().isoformat()
        }
        
        if duration_ms is not None:
            log_data['step_duration_ms'] = duration_ms
        
        log_data.update(kwargs)
        
        structured_logger.business_event(
            'user_journey_step',
            f"User journey: {step}",
            **log_data
        )

class LogSearchPatterns:
    """Common regex patterns for log parsing and analysis"""
    
    # Performance patterns
    SLOW_QUERY_PATTERN = re.compile(r'"duration_ms":\s*([0-9]+\.?[0-9]*)')
    ERROR_RATE_PATTERN = re.compile(r'"level":\s*"ERROR"')
    
    # Security patterns
    LOGIN_ATTEMPT_PATTERN = re.compile(r'"security_event_type":\s*"([^"]*login[^"]*)"')
    IP_ADDRESS_PATTERN = re.compile(r'"ip_address":\s*"([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})"')
    
    # Business patterns
    PATIENT_ACCESS_PATTERN = re.compile(r'"patient_id":\s*"?([0-9]+)"?')
    API_ENDPOINT_PATTERN = re.compile(r'"path":\s*"([^"]*)"')

def setup_log_rotation_config():
    """Configure log rotation for production log aggregation"""
    import logging.handlers
    import os
    
    # Create logs directory if it doesn't exist
    log_dir = '/tmp/healthprep_logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure rotating file handler for structured logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=f'{log_dir}/healthprep_structured.log',
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    
    # Use our JSON formatter
    from app import JSONFormatter
    file_handler.setFormatter(JSONFormatter())
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    structured_logger.info(
        "Log rotation configured for machine parsing",
        event_category='system',
        log_directory=log_dir,
        max_file_size_mb=50,
        backup_count=10
    )

# Example usage functions for common monitoring scenarios
def log_database_connection_pool_metrics(active_connections: int, pool_size: int):
    """Log database connection pool metrics"""
    LogAggregationHelper.create_metric_log(
        'db_connection_pool_active',
        active_connections,
        unit='connections',
        tags={'pool': 'main', 'database': 'healthcare'}
    )
    
    LogAggregationHelper.create_metric_log(
        'db_connection_pool_utilization',
        (active_connections / pool_size) * 100,
        unit='percent',
        tags={'pool': 'main', 'database': 'healthcare'}
    )

def log_api_response_time_percentiles(endpoint: str, p50: float, p95: float, p99: float):
    """Log API response time percentiles for monitoring"""
    for percentile, value in [('p50', p50), ('p95', p95), ('p99', p99)]:
        LogAggregationHelper.create_metric_log(
            f'api_response_time_{percentile}',
            value,
            unit='milliseconds',
            tags={'endpoint': endpoint, 'percentile': percentile}
        )

def log_patient_data_access_summary(period_minutes: int = 60):
    """Log patient data access summary for compliance reporting"""
    # This would typically aggregate from your existing logs
    LogAggregationHelper.create_business_kpi_log(
        'patient_data_access_rate',
        'aggregated_from_logs',  # In practice, calculate from log data
        period=f'{period_minutes}min',
        compliance_category='data_access',
        aggregation_window=period_minutes
    )
