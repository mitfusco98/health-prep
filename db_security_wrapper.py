
"""
Secure database wrapper that enforces parameterized queries
"""

import logging
from sqlalchemy import text
from app import db
from sql_security import SQLSecurityValidator

logger = logging.getLogger(__name__)

class SecureDBWrapper:
    """
    Wrapper class that ensures all database operations use parameterized queries
    """
    
    @staticmethod
    def execute_query(query, parameters=None):
        """
        Execute a parameterized query with security validation
        
        Args:
            query: SQL query string with named parameters (:param_name)
            parameters: Dictionary of parameters
            
        Returns:
            Query result
            
        Raises:
            ValueError: If security validation fails
            Exception: If query execution fails
        """
        # Validate query for dangerous patterns
        if not SQLSecurityValidator.validate_input(query):
            raise ValueError("Query contains potentially dangerous SQL patterns")
        
        # Validate all parameters
        if parameters:
            for key, value in parameters.items():
                if not SQLSecurityValidator.validate_input(str(value)):
                    raise ValueError(f"Parameter '{key}' contains potentially dangerous patterns")
        
        try:
            result = db.session.execute(text(query), parameters or {})
            logger.debug(f"Executed secure query with {len(parameters or {})} parameters")
            return result
        except Exception as e:
            logger.error(f"Secure query execution failed: {str(e)}")
            raise
    
    @staticmethod
    def select_one(query, parameters=None):
        """
        Execute a SELECT query and return one result
        """
        result = SecureDBWrapper.execute_query(query, parameters)
        return result.fetchone()
    
    @staticmethod
    def select_all(query, parameters=None):
        """
        Execute a SELECT query and return all results
        """
        result = SecureDBWrapper.execute_query(query, parameters)
        return result.fetchall()
    
    @staticmethod
    def insert(table, data):
        """
        Insert data into a table using parameterized query
        
        Args:
            table: Table name
            data: Dictionary of column->value pairs
        """
        if not data:
            raise ValueError("No data provided for insert")
        
        # Validate table name (should be alphanumeric and underscore only)
        if not table.replace('_', '').isalnum():
            raise ValueError("Invalid table name")
        
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        
        return SecureDBWrapper.execute_query(query, data)
    
    @staticmethod
    def update(table, data, where_clause, where_params):
        """
        Update data in a table using parameterized query
        
        Args:
            table: Table name
            data: Dictionary of column->value pairs to update
            where_clause: WHERE clause with named parameters
            where_params: Parameters for WHERE clause
        """
        if not data:
            raise ValueError("No data provided for update")
        
        # Validate table name
        if not table.replace('_', '').isalnum():
            raise ValueError("Invalid table name")
        
        set_clauses = [f"{col} = :{col}" for col in data.keys()]
        
        query = f"""
            UPDATE {table} 
            SET {', '.join(set_clauses)}
            WHERE {where_clause}
        """
        
        # Combine data and where parameters
        all_params = {**data, **where_params}
        
        return SecureDBWrapper.execute_query(query, all_params)
    
    @staticmethod
    def delete(table, where_clause, where_params):
        """
        Delete data from a table using parameterized query
        
        Args:
            table: Table name
            where_clause: WHERE clause with named parameters
            where_params: Parameters for WHERE clause
        """
        # Validate table name
        if not table.replace('_', '').isalnum():
            raise ValueError("Invalid table name")
        
        query = f"DELETE FROM {table} WHERE {where_clause}"
        
        return SecureDBWrapper.execute_query(query, where_params)


# Convenience functions for common operations
def get_patient_by_id(patient_id):
    """Get patient by ID using secure parameterized query"""
    return SecureDBWrapper.select_one(
        "SELECT * FROM patient WHERE id = :patient_id",
        {"patient_id": patient_id}
    )

def get_appointments_by_date(appointment_date):
    """Get appointments by date using secure parameterized query"""
    return SecureDBWrapper.select_all(
        "SELECT * FROM appointment WHERE DATE(appointment_date) = DATE(:appointment_date) ORDER BY appointment_time",
        {"appointment_date": appointment_date}
    )

def search_patients_by_name(search_term, limit=50):
    """Search patients by name using secure parameterized query"""
    escaped_term = search_term.replace('%', '\\%').replace('_', '\\_')
    return SecureDBWrapper.select_all("""
        SELECT * FROM patient 
        WHERE first_name ILIKE :search_pattern 
           OR last_name ILIKE :search_pattern 
           OR CONCAT(first_name, ' ', last_name) ILIKE :search_pattern
        ORDER BY last_name, first_name
        LIMIT :limit
    """, {
        "search_pattern": f"%{escaped_term}%",
        "limit": limit
    })

def get_patient_conditions(patient_id):
    """Get active conditions for a patient using secure parameterized query"""
    return SecureDBWrapper.select_all(
        "SELECT * FROM condition WHERE patient_id = :patient_id AND is_active = :is_active ORDER BY diagnosed_date DESC",
        {"patient_id": patient_id, "is_active": True}
    )

def get_patient_vitals(patient_id, limit=10):
    """Get recent vitals for a patient using secure parameterized query"""
    return SecureDBWrapper.select_all(
        "SELECT * FROM vital WHERE patient_id = :patient_id ORDER BY date DESC LIMIT :limit",
        {"patient_id": patient_id, "limit": limit}
    )
