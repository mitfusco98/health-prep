#!/usr/bin/env python3
"""
Database Access Layer for High-Performance Screening Operations
Handles orphaned relationships, screening type changes, cutoff calculations,
bulk operations, transaction handling, and demographic filtering edge cases
"""

import logging
import asyncio
import asyncpg
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import os
from concurrent.futures import ThreadPoolExecutor
import threading

from app import db
from models import Patient, ScreeningType, Screening, MedicalDocument, Appointment

logger = logging.getLogger(__name__)

@dataclass
class CutoffCalculation:
    """Represents cutoff date calculations for screening filtering"""
    general_cutoff_months: Optional[int] = None
    labs_cutoff_months: Optional[int] = None
    imaging_cutoff_months: Optional[int] = None
    consults_cutoff_months: Optional[int] = None
    hospital_cutoff_months: Optional[int] = None
    screening_specific_cutoffs: Optional[Dict[str, int]] = None
    use_appointment_date: bool = False
    last_appointment_date: Optional[date] = None

@dataclass
class DemographicFilter:
    """Represents demographic filtering criteria"""
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    gender_specific: Optional[str] = None  # 'M', 'F', or None
    trigger_conditions: Optional[List[str]] = None

@dataclass
class BulkOperationResult:
    """Result of bulk database operations"""
    success: bool = False
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_deleted: int = 0
    errors: List[str] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class DatabaseAccessLayer:
    """
    High-performance database access layer with comprehensive edge case handling
    """
    
    def __init__(self, database_url: str = None, pool_size: int = 20, max_connections: int = 50):
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        self.pool_size = pool_size
        self.max_connections = max_connections
        self.pool = None
        self.connection_lock = threading.Lock()
        
        # Prepared statement cache
        self.prepared_statements = {}
        
        # Connection retry settings
        self.max_retries = 3
        self.retry_delay = 1.0
        
    async def initialize(self) -> bool:
        """Initialize the database access layer with connection pooling"""
        try:
            if self.database_url.startswith("postgresql://"):
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=5,
                    max_size=self.pool_size,
                    command_timeout=30,
                    server_settings={
                        'jit': 'off',
                        'work_mem': '256MB',
                        'effective_cache_size': '1GB'
                    }
                )
                logger.info(f"✅ Database access layer initialized with {self.pool_size} connections")
                return True
            else:
                logger.error("❌ Invalid database URL format")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize database access layer: {e}")
            return False
            
    async def close(self):
        """Close the database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Database access layer closed")
            
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection with retry logic"""
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    yield conn
                    return
            except Exception as e:
                logger.warning(f"⚠️ Database connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise
                    
    async def cleanup_orphaned_screening_documents(self) -> BulkOperationResult:
        """
        Clean up orphaned screening-document relationships
        Removes relationships where either the screening or document no longer exists
        """
        start_time = asyncio.get_event_loop().time()
        result = BulkOperationResult()
        
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    # Find orphaned relationships where screening doesn't exist
                    orphaned_screening_query = """
                        DELETE FROM screening_documents 
                        WHERE screening_id NOT IN (SELECT id FROM screening)
                        RETURNING screening_id, document_id
                    """
                    
                    orphaned_screening_rows = await conn.fetch(orphaned_screening_query)
                    screening_orphans = len(orphaned_screening_rows)
                    
                    # Find orphaned relationships where document doesn't exist
                    orphaned_document_query = """
                        DELETE FROM screening_documents 
                        WHERE document_id NOT IN (SELECT id FROM medical_document)
                        RETURNING screening_id, document_id
                    """
                    
                    orphaned_document_rows = await conn.fetch(orphaned_document_query)
                    document_orphans = len(orphaned_document_rows)
                    
                    # Log cleanup details
                    if screening_orphans > 0:
                        logger.info(f"🧹 Cleaned up {screening_orphans} orphaned screening relationships")
                    if document_orphans > 0:
                        logger.info(f"🧹 Cleaned up {document_orphans} orphaned document relationships")
                    
                    result.success = True
                    result.records_deleted = screening_orphans + document_orphans
                    result.processing_time = asyncio.get_event_loop().time() - start_time
                    
        except Exception as e:
            logger.error(f"❌ Error cleaning up orphaned relationships: {e}")
            result.errors.append(str(e))
            
        return result
        
    async def handle_screening_type_status_change(self, screening_type_id: int, 
                                                 new_status: bool) -> BulkOperationResult:
        """
        Handle screening type activation/deactivation with proper cascading
        
        Args:
            screening_type_id: ID of the screening type
            new_status: True for active, False for inactive
            
        Returns:
            BulkOperationResult with operation details
        """
        start_time = asyncio.get_event_loop().time()
        result = BulkOperationResult()
        
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    # Get screening type details
                    screening_type_data = await conn.fetchrow("""
                        SELECT id, name, is_active FROM screening_type WHERE id = $1
                    """, screening_type_id)
                    
                    if not screening_type_data:
                        result.errors.append(f"Screening type {screening_type_id} not found")
                        return result
                    
                    current_status = screening_type_data['is_active']
                    screening_type_name = screening_type_data['name']
                    
                    # Update screening type status
                    await conn.execute("""
                        UPDATE screening_type SET is_active = $1 WHERE id = $2
                    """, new_status, screening_type_id)
                    
                    result.records_updated += 1
                    
                    # Handle deactivation cascading
                    if new_status == False and current_status == True:
                        # Clean up existing screenings for this type
                        screening_cleanup_result = await conn.fetch("""
                            DELETE FROM screening 
                            WHERE screening_type = $1
                            RETURNING id, patient_id
                        """, screening_type_name)
                        
                        screening_count = len(screening_cleanup_result)
                        result.records_deleted += screening_count
                        
                        # Clean up document relationships for deleted screenings
                        if screening_count > 0:
                            screening_ids = [row['id'] for row in screening_cleanup_result]
                            
                            # Use prepared statement for bulk deletion
                            await conn.execute("""
                                DELETE FROM screening_documents 
                                WHERE screening_id = ANY($1)
                            """, screening_ids)
                            
                        logger.info(f"🔄 Deactivated '{screening_type_name}' and cleaned up {screening_count} screenings")
                        
                    elif new_status == True and current_status == False:
                        logger.info(f"🔄 Activated '{screening_type_name}' - will regenerate screenings on next refresh")
                        
                    result.success = True
                    result.processing_time = asyncio.get_event_loop().time() - start_time
                    
        except Exception as e:
            logger.error(f"❌ Error handling screening type status change: {e}")
            result.errors.append(str(e))
            
        return result
        
    async def calculate_cutoff_dates(self, patient_id: int, 
                                   cutoff_settings: CutoffCalculation) -> Dict[str, date]:
        """
        Calculate cutoff dates for different data types including 'to last appointment date' logic
        
        Args:
            patient_id: Patient ID
            cutoff_settings: Cutoff calculation parameters
            
        Returns:
            Dictionary mapping data types to their cutoff dates
        """
        cutoff_dates = {}
        reference_date = date.today()
        
        try:
            async with self.get_connection() as conn:
                # Get last appointment date if needed
                if cutoff_settings.use_appointment_date:
                    last_appointment = await conn.fetchrow("""
                        SELECT MAX(appointment_date) as last_date 
                        FROM appointment 
                        WHERE patient_id = $1 AND appointment_date <= CURRENT_DATE
                    """, patient_id)
                    
                    if last_appointment and last_appointment['last_date']:
                        reference_date = last_appointment['last_date']
                        cutoff_settings.last_appointment_date = reference_date
                        logger.debug(f"Using last appointment date {reference_date} for patient {patient_id}")
                
                # Calculate cutoff dates for different data types
                if cutoff_settings.general_cutoff_months:
                    cutoff_dates['general'] = reference_date - timedelta(days=cutoff_settings.general_cutoff_months * 30)
                
                if cutoff_settings.labs_cutoff_months:
                    cutoff_dates['labs'] = reference_date - timedelta(days=cutoff_settings.labs_cutoff_months * 30)
                
                if cutoff_settings.imaging_cutoff_months:
                    cutoff_dates['imaging'] = reference_date - timedelta(days=cutoff_settings.imaging_cutoff_months * 30)
                
                if cutoff_settings.consults_cutoff_months:
                    cutoff_dates['consults'] = reference_date - timedelta(days=cutoff_settings.consults_cutoff_months * 30)
                
                if cutoff_settings.hospital_cutoff_months:
                    cutoff_dates['hospital'] = reference_date - timedelta(days=cutoff_settings.hospital_cutoff_months * 30)
                
                # Handle screening-specific cutoffs
                if cutoff_settings.screening_specific_cutoffs:
                    for screening_type, months in cutoff_settings.screening_specific_cutoffs.items():
                        cutoff_dates[f'screening_{screening_type}'] = reference_date - timedelta(days=months * 30)
                
        except Exception as e:
            logger.error(f"❌ Error calculating cutoff dates: {e}")
            
        return cutoff_dates
        
    async def bulk_update_screening_documents(self, operations: List[Dict[str, Any]]) -> BulkOperationResult:
        """
        Perform bulk operations on screening_documents table using prepared statements
        
        Args:
            operations: List of operation dictionaries with keys:
                - operation: 'insert', 'update', or 'delete'
                - screening_id: Screening ID
                - document_id: Document ID
                - confidence_score: Confidence score (for insert/update)
                - match_source: Match source (for insert/update)
                
        Returns:
            BulkOperationResult with operation details
        """
        start_time = asyncio.get_event_loop().time()
        result = BulkOperationResult()
        
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    # Prepare statements if not already cached
                    if 'bulk_insert_screening_doc' not in self.prepared_statements:
                        self.prepared_statements['bulk_insert_screening_doc'] = await conn.prepare("""
                            INSERT INTO screening_documents (screening_id, document_id, confidence_score, match_source)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (screening_id, document_id) 
                            DO UPDATE SET confidence_score = $3, match_source = $4
                        """)
                    
                    if 'bulk_delete_screening_doc' not in self.prepared_statements:
                        self.prepared_statements['bulk_delete_screening_doc'] = await conn.prepare("""
                            DELETE FROM screening_documents 
                            WHERE screening_id = $1 AND document_id = $2
                        """)
                    
                    # Process operations by type
                    insert_ops = []
                    delete_ops = []
                    
                    for op in operations:
                        operation_type = op.get('operation')
                        
                        if operation_type == 'insert':
                            insert_ops.append((
                                op['screening_id'], 
                                op['document_id'], 
                                op.get('confidence_score', 1.0),
                                op.get('match_source', 'automated')
                            ))
                        elif operation_type == 'delete':
                            delete_ops.append((op['screening_id'], op['document_id']))
                    
                    # Execute bulk operations
                    if insert_ops:
                        await self.prepared_statements['bulk_insert_screening_doc'].executemany(insert_ops)
                        result.records_created += len(insert_ops)
                        
                    if delete_ops:
                        await self.prepared_statements['bulk_delete_screening_doc'].executemany(delete_ops)
                        result.records_deleted += len(delete_ops)
                    
                    result.success = True
                    result.records_processed = len(operations)
                    result.processing_time = asyncio.get_event_loop().time() - start_time
                    
                    logger.info(f"✅ Bulk screening documents operation: {result.records_created} created, {result.records_deleted} deleted")
                    
        except Exception as e:
            logger.error(f"❌ Error in bulk screening documents operation: {e}")
            result.errors.append(str(e))
            
        return result
        
    async def update_screening_with_documents(self, screening_id: int, 
                                            document_ids: List[int],
                                            confidence_scores: List[float] = None,
                                            match_sources: List[str] = None) -> BulkOperationResult:
        """
        Update screening with document relationships using proper transaction handling
        
        Args:
            screening_id: Screening ID
            document_ids: List of document IDs to link
            confidence_scores: Optional confidence scores for each document
            match_sources: Optional match sources for each document
            
        Returns:
            BulkOperationResult with operation details
        """
        start_time = asyncio.get_event_loop().time()
        result = BulkOperationResult()
        
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    # Clear existing relationships for this screening
                    await conn.execute("""
                        DELETE FROM screening_documents WHERE screening_id = $1
                    """, screening_id)
                    
                    # Validate that all documents exist
                    if document_ids:
                        valid_docs = await conn.fetch("""
                            SELECT id FROM medical_document WHERE id = ANY($1)
                        """, document_ids)
                        
                        valid_doc_ids = [row['id'] for row in valid_docs]
                        
                        if len(valid_doc_ids) != len(document_ids):
                            invalid_ids = set(document_ids) - set(valid_doc_ids)
                            logger.warning(f"⚠️ Invalid document IDs found: {invalid_ids}")
                            document_ids = valid_doc_ids
                        
                        # Prepare bulk insert data
                        if document_ids:
                            insert_data = []
                            for i, doc_id in enumerate(document_ids):
                                confidence = confidence_scores[i] if confidence_scores else 1.0
                                source = match_sources[i] if match_sources else 'automated'
                                insert_data.append((screening_id, doc_id, confidence, source))
                            
                            # Bulk insert new relationships
                            await conn.executemany("""
                                INSERT INTO screening_documents (screening_id, document_id, confidence_score, match_source)
                                VALUES ($1, $2, $3, $4)
                            """, insert_data)
                            
                            result.records_created = len(insert_data)
                    
                    result.success = True
                    result.records_processed = len(document_ids)
                    result.processing_time = asyncio.get_event_loop().time() - start_time
                    
        except Exception as e:
            logger.error(f"❌ Error updating screening with documents: {e}")
            result.errors.append(str(e))
            
        return result
        
    async def get_patients_with_demographic_filtering(self, 
                                                    demographic_filter: DemographicFilter,
                                                    limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get patients with comprehensive demographic filtering edge case handling
        
        Args:
            demographic_filter: Demographic filtering criteria
            limit: Maximum number of patients to return
            
        Returns:
            List of patient dictionaries matching the criteria
        """
        try:
            async with self.get_connection() as conn:
                # Build dynamic query based on demographic filters
                query_parts = ["SELECT id, first_name, last_name, mrn, date_of_birth, sex"]
                query_parts.append("FROM patient")
                
                where_conditions = []
                params = []
                param_count = 0
                
                # Age filtering with boundary handling
                if demographic_filter.min_age is not None:
                    param_count += 1
                    where_conditions.append(f"extract(year from age(date_of_birth)) >= ${param_count}")
                    params.append(demographic_filter.min_age)
                
                if demographic_filter.max_age is not None:
                    param_count += 1
                    where_conditions.append(f"extract(year from age(date_of_birth)) <= ${param_count}")
                    params.append(demographic_filter.max_age)
                
                # Gender-specific filtering
                if demographic_filter.gender_specific:
                    param_count += 1
                    where_conditions.append(f"sex = ${param_count}")
                    params.append(demographic_filter.gender_specific)
                
                # Trigger conditions filtering (if patient has specific conditions)
                if demographic_filter.trigger_conditions:
                    param_count += 1
                    where_conditions.append(f"""
                        id IN (
                            SELECT patient_id FROM condition 
                            WHERE condition_name = ANY(${param_count})
                        )
                    """)
                    params.append(demographic_filter.trigger_conditions)
                
                # Combine query parts
                if where_conditions:
                    query_parts.append("WHERE " + " AND ".join(where_conditions))
                
                query_parts.append("ORDER BY id")
                query_parts.append(f"LIMIT {limit}")
                
                query = " ".join(query_parts)
                
                # Execute query
                rows = await conn.fetch(query, *params)
                
                # Convert to dictionaries and handle edge cases
                patients = []
                for row in rows:
                    patient_dict = dict(row)
                    
                    # Handle missing birth date edge case
                    if patient_dict.get('date_of_birth'):
                        age = (date.today() - patient_dict['date_of_birth']).days // 365
                        patient_dict['calculated_age'] = age
                    else:
                        patient_dict['calculated_age'] = None
                        
                    # Handle missing or invalid sex values
                    if patient_dict.get('sex') not in ['M', 'F']:
                        patient_dict['sex'] = None
                        
                    patients.append(patient_dict)
                
                logger.info(f"✅ Found {len(patients)} patients matching demographic criteria")
                return patients
                
        except Exception as e:
            logger.error(f"❌ Error in demographic filtering: {e}")
            return []
            
    async def get_screening_documents_with_cutoff(self, screening_id: int,
                                                cutoff_dates: Dict[str, date]) -> List[Dict[str, Any]]:
        """
        Get screening documents filtered by cutoff dates
        
        Args:
            screening_id: Screening ID
            cutoff_dates: Dictionary of cutoff dates by data type
            
        Returns:
            List of document dictionaries within cutoff windows
        """
        try:
            async with self.get_connection() as conn:
                # Get documents linked to this screening
                documents = await conn.fetch("""
                    SELECT md.id, md.filename, md.document_type, md.document_date, md.created_at,
                           sd.confidence_score, sd.match_source
                    FROM screening_documents sd
                    JOIN medical_document md ON sd.document_id = md.id
                    WHERE sd.screening_id = $1
                    ORDER BY md.document_date DESC NULLS LAST, md.created_at DESC
                """, screening_id)
                
                # Filter documents by cutoff dates
                filtered_documents = []
                
                for doc in documents:
                    doc_dict = dict(doc)
                    
                    # Determine relevant cutoff date based on document type
                    document_date = doc_dict.get('document_date') or doc_dict.get('created_at')
                    if not document_date:
                        continue
                    
                    # Convert to date if it's a datetime
                    if isinstance(document_date, datetime):
                        document_date = document_date.date()
                    
                    # Check against appropriate cutoff
                    doc_type = doc_dict.get('document_type', '').lower()
                    
                    # Determine which cutoff to use
                    cutoff_date = None
                    if 'lab' in doc_type and 'labs' in cutoff_dates:
                        cutoff_date = cutoff_dates['labs']
                    elif 'imaging' in doc_type or 'radiology' in doc_type:
                        cutoff_date = cutoff_dates.get('imaging')
                    elif 'consult' in doc_type:
                        cutoff_date = cutoff_dates.get('consults')
                    elif 'hospital' in doc_type or 'inpatient' in doc_type:
                        cutoff_date = cutoff_dates.get('hospital')
                    else:
                        cutoff_date = cutoff_dates.get('general')
                    
                    # Include document if it's within cutoff or no cutoff applies
                    if cutoff_date is None or document_date >= cutoff_date:
                        filtered_documents.append(doc_dict)
                
                return filtered_documents
                
        except Exception as e:
            logger.error(f"❌ Error filtering documents by cutoff: {e}")
            return []
            
    async def concurrent_screening_refresh_lock(self, patient_id: int) -> asyncio.Lock:
        """
        Get a lock for concurrent screening refresh operations
        Prevents multiple refresh operations from interfering with each other
        
        Args:
            patient_id: Patient ID to lock
            
        Returns:
            Async lock for the patient
        """
        if not hasattr(self, '_patient_locks'):
            self._patient_locks = {}
            
        if patient_id not in self._patient_locks:
            self._patient_locks[patient_id] = asyncio.Lock()
            
        return self._patient_locks[patient_id]
        
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics for monitoring and optimization
        
        Returns:
            Dictionary with database performance metrics
        """
        try:
            async with self.get_connection() as conn:
                stats = {}
                
                # Get table row counts
                stats['patient_count'] = await conn.fetchval("SELECT COUNT(*) FROM patient")
                stats['screening_count'] = await conn.fetchval("SELECT COUNT(*) FROM screening")
                stats['document_count'] = await conn.fetchval("SELECT COUNT(*) FROM medical_document")
                stats['screening_document_relationships'] = await conn.fetchval("SELECT COUNT(*) FROM screening_documents")
                
                # Get orphaned relationship counts
                stats['orphaned_screening_relationships'] = await conn.fetchval("""
                    SELECT COUNT(*) FROM screening_documents 
                    WHERE screening_id NOT IN (SELECT id FROM screening)
                """)
                
                stats['orphaned_document_relationships'] = await conn.fetchval("""
                    SELECT COUNT(*) FROM screening_documents 
                    WHERE document_id NOT IN (SELECT id FROM medical_document)
                """)
                
                # Get screening type statistics
                stats['active_screening_types'] = await conn.fetchval("""
                    SELECT COUNT(*) FROM screening_type WHERE is_active = true
                """)
                
                stats['inactive_screening_types'] = await conn.fetchval("""
                    SELECT COUNT(*) FROM screening_type WHERE is_active = false
                """)
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}

# Global database access layer instance
db_access_layer = None

async def get_database_access_layer() -> DatabaseAccessLayer:
    """Get or create the global database access layer"""
    global db_access_layer
    
    if db_access_layer is None:
        db_access_layer = DatabaseAccessLayer()
        initialized = await db_access_layer.initialize()
        if not initialized:
            raise Exception("Failed to initialize database access layer")
            
    return db_access_layer

# Synchronous wrapper functions for integration with existing code
def cleanup_orphaned_relationships_sync() -> Dict[str, Any]:
    """Synchronous wrapper for orphaned relationship cleanup"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_cleanup():
            dal = await get_database_access_layer()
            result = await dal.cleanup_orphaned_screening_documents()
            return {
                'success': result.success,
                'records_deleted': result.records_deleted,
                'processing_time': result.processing_time,
                'errors': result.errors
            }
            
        return loop.run_until_complete(run_cleanup())
        
    except Exception as e:
        logger.error(f"❌ Sync orphaned cleanup failed: {e}")
        return {'success': False, 'records_deleted': 0, 'errors': [str(e)]}
    finally:
        loop.close()

def handle_screening_type_change_sync(screening_type_id: int, new_status: bool) -> Dict[str, Any]:
    """Synchronous wrapper for screening type status changes"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_status_change():
            dal = await get_database_access_layer()
            result = await dal.handle_screening_type_status_change(screening_type_id, new_status)
            return {
                'success': result.success,
                'records_updated': result.records_updated,
                'records_deleted': result.records_deleted,
                'processing_time': result.processing_time,
                'errors': result.errors
            }
            
        return loop.run_until_complete(run_status_change())
        
    except Exception as e:
        logger.error(f"❌ Sync screening type change failed: {e}")
        return {'success': False, 'records_updated': 0, 'errors': [str(e)]}
    finally:
        loop.close()

def get_database_stats_sync() -> Dict[str, Any]:
    """Synchronous wrapper for database statistics"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_stats():
            dal = await get_database_access_layer()
            return await dal.get_database_stats()
            
        return loop.run_until_complete(run_stats())
        
    except Exception as e:
        logger.error(f"❌ Sync database stats failed: {e}")
        return {}
    finally:
        loop.close()

if __name__ == "__main__":
    # Test the database access layer
    async def test_database_access_layer():
        dal = DatabaseAccessLayer()
        initialized = await dal.initialize()
        
        if initialized:
            # Test orphaned relationship cleanup
            cleanup_result = await dal.cleanup_orphaned_screening_documents()
            print(f"Cleanup result: {cleanup_result}")
            
            # Test database stats
            stats = await dal.get_database_stats()
            print(f"Database stats: {stats}")
            
            await dal.close()
        else:
            print("Failed to initialize database access layer")
    

            
    asyncio.run(test_database_access_layer())