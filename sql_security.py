
"""
SQL Security utilities for preventing SQL injection attacks
"""

import logging
import re
from sqlalchemy import text
from app import db

logger = logging.getLogger(__name__)

class SQLSecurityValidator:
    """
    Validates and sanitizes SQL queries to prevent injection attacks
    """
    
    # Dangerous SQL patterns that should never appear in user input
    DANGEROUS_PATTERNS = [
        r'(union\s+select)', r'(drop\s+table)', r'(delete\s+from)',
        r'(insert\s+into)', r'(update\s+\w+\s+set)', r'(exec\s*\()',
        r'(script\s*>)', r'(javascript:)', r'(vbscript:)',
        r'(onload\s*=)', r'(onerror\s*=)', r'(\bor\b\s+1\s*=\s*1)',
        r'(\band\b\s+1\s*=\s*1)', r'(;\s*drop)', r'(;\s*delete)',
        r'(;\s*insert)', r'(;\s*update)', r'(--\s*)', r'(/\*.*?\*/)',
        r'(xp_cmdshell)', r'(sp_executesql)', r'(eval\s*\()',
        r'(<iframe)', r'(<object)', r'(<embed)', r'(<form)',
        r'(data:text/html)', r'(data:application)', r'(\bvoid\s*\()'
    ]
    
    @classmethod
    def validate_input(cls, value):
        """
        Validate user input for SQL injection patterns
        
        Args:
            value: Input value to validate
            
        Returns:
            bool: True if safe, False if dangerous patterns detected
        """
        if not value:
            return True
            
        value_str = str(value).lower()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value_str, re.IGNORECASE | re.DOTALL):
                logger.warning(f"Dangerous SQL pattern detected: {pattern} in input: {value_str[:100]}")
                return False
                
        return True
    
    @classmethod
    def sanitize_input(cls, value):
        """
        Sanitize input by removing dangerous patterns
        
        Args:
            value: Input value to sanitize
            
        Returns:
            str: Sanitized value
        """
        if not value:
            return value
            
        sanitized = str(value)
        
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            
        return sanitized


def execute_safe_query(query, parameters=None):
    """
    Execute a parameterized query safely
    
    Args:
        query: SQL query string with parameter placeholders
        parameters: Dictionary of parameters for the query
        
    Returns:
        Result of the query execution
        
    Raises:
        ValueError: If dangerous patterns are detected in the query
    """
    if not SQLSecurityValidator.validate_input(query):
        raise ValueError("Potentially dangerous SQL patterns detected in query")
    
    if parameters:
        for key, value in parameters.items():
            if not SQLSecurityValidator.validate_input(value):
                raise ValueError(f"Potentially dangerous SQL patterns detected in parameter {key}")
    
    try:
        return db.session.execute(text(query), parameters or {})
    except Exception as e:
        logger.error(f"Error executing safe query: {str(e)}")
        raise


def safe_like_search(column, search_term):
    """
    Create a safe LIKE search condition
    
    Args:
        column: Column object for the search
        search_term: Search term to use
        
    Returns:
        SQLAlchemy condition object
    """
    if not SQLSecurityValidator.validate_input(search_term):
        logger.warning(f"Dangerous patterns in search term: {search_term}")
        return column.like('%')  # Return a safe default
    
    # Escape special characters in LIKE patterns
    escaped_term = search_term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return column.like(f'%{escaped_term}%')


class ParameterizedQueryBuilder:
    """
    Helper class for building parameterized queries
    """
    
    def __init__(self):
        self.query_parts = []
        self.parameters = {}
        self.param_counter = 0
    
    def add_where_condition(self, condition, value):
        """
        Add a WHERE condition with a parameterized value
        
        Args:
            condition: SQL condition string with placeholder
            value: Value for the parameter
        """
        param_name = f"param_{self.param_counter}"
        self.param_counter += 1
        
        if not SQLSecurityValidator.validate_input(value):
            raise ValueError(f"Dangerous patterns detected in value: {value}")
        
        self.query_parts.append(condition.replace('?', f":{param_name}"))
        self.parameters[param_name] = value
    
    def build_query(self, base_query):
        """
        Build the complete parameterized query
        
        Args:
            base_query: Base SQL query string
            
        Returns:
            tuple: (complete_query, parameters)
        """
        if self.query_parts:
            where_clause = " AND ".join(self.query_parts)
            complete_query = f"{base_query} WHERE {where_clause}"
        else:
            complete_query = base_query
        
        return complete_query, self.parameters


# Example usage functions
def get_patient_by_mrn_safe(mrn):
    """
    Safely retrieve a patient by MRN using parameterized query
    
    Args:
        mrn: Medical Record Number
        
    Returns:
        Patient object or None
    """
    if not SQLSecurityValidator.validate_input(mrn):
        logger.warning(f"Invalid MRN format detected: {mrn}")
        return None
    
    try:
        result = execute_safe_query(
            "SELECT * FROM patient WHERE mrn = :mrn LIMIT 1",
            {"mrn": mrn}
        )
        return result.fetchone()
    except Exception as e:
        logger.error(f"Error retrieving patient by MRN: {str(e)}")
        return None


def search_patients_safe(search_term, limit=50):
    """
    Safely search patients using parameterized queries
    
    Args:
        search_term: Search term for name or MRN
        limit: Maximum number of results
        
    Returns:
        List of patient records
    """
    if not SQLSecurityValidator.validate_input(search_term):
        logger.warning(f"Invalid search term detected: {search_term}")
        return []
    
    try:
        # Escape special characters for LIKE search
        escaped_term = search_term.replace('%', '\\%').replace('_', '\\_')
        
        result = execute_safe_query("""
            SELECT * FROM patient 
            WHERE first_name ILIKE :search_pattern 
               OR last_name ILIKE :search_pattern 
               OR mrn ILIKE :search_pattern
               OR CONCAT(first_name, ' ', last_name) ILIKE :search_pattern
            ORDER BY last_name, first_name
            LIMIT :limit
        """, {
            "search_pattern": f"%{escaped_term}%",
            "limit": limit
        })
        
        return result.fetchall()
    except Exception as e:
        logger.error(f"Error searching patients: {str(e)}")
        return []


def audit_sql_queries():
    """
    Audit recent SQL queries for potential security issues
    This is a placeholder for a more comprehensive auditing system
    """
    logger.info("SQL security audit initiated")
    
    # In a real implementation, this would analyze query logs
    # and look for patterns that might indicate SQL injection attempts
    
    return {
        "status": "completed",
        "queries_audited": 0,
        "suspicious_patterns": 0,
        "recommendations": [
            "Continue using parameterized queries",
            "Validate all user inputs",
            "Monitor query logs for unusual patterns"
        ]
    }
