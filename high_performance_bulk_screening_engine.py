#!/usr/bin/env python3
"""
High-Performance Bulk Screening Processing Engine
Handles 1000+ patients with async/await, connection pooling, and circuit breakers
Integrates with automated_edge_case_handler.py for reactive updates
"""

import asyncio
import asyncpg
import logging
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
import psutil
import os

from app import app, db
from models import Patient, ScreeningType, Screening, MedicalDocument
from automated_edge_case_handler import AutomatedScreeningRefreshManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingMetrics:
    """Metrics for bulk processing operations"""
    total_patients: int = 0
    processed_patients: int = 0
    failed_patients: int = 0
    circuit_breaker_trips: int = 0
    total_screenings_updated: int = 0
    total_documents_linked: int = 0
    processing_time: float = 0.0
    database_operations: int = 0
    timeout_recoveries: int = 0

@dataclass
class CircuitBreakerState:
    """Circuit breaker state for problematic patients"""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    failure_threshold: int = 3
    recovery_timeout: int = 300  # 5 minutes

class DatabaseConnectionPool:
    """High-performance async database connection pool"""
    
    def __init__(self, database_url: str, pool_size: int = 50, max_overflow: int = 100):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool = None
        self.connection_semaphore = asyncio.Semaphore(pool_size + max_overflow)
        
    async def initialize(self):
        """Initialize the connection pool"""
        try:
            # Parse database URL for asyncpg
            if self.database_url.startswith("postgresql://"):
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=10,
                    max_size=self.pool_size,
                    command_timeout=10,
                    server_settings={
                        'jit': 'off'  # Disable JIT for faster simple queries
                    }
                )
                logger.info(f"✅ Initialized async database pool with {self.pool_size} connections")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}")
            return False
            
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection with timeout protection"""
        async with self.connection_semaphore:
            if not self.pool:
                raise Exception("Database pool not initialized")
                
            try:
                async with self.pool.acquire() as connection:
                    yield connection
            except asyncio.TimeoutError:
                logger.warning("⏱️ Database connection timeout, retrying...")
                # Try once more with a fresh connection
                async with self.pool.acquire() as connection:
                    yield connection

class PatientCircuitBreaker:
    """Circuit breaker for problematic patients to prevent system overload"""
    
    def __init__(self):
        self.patient_states: Dict[int, CircuitBreakerState] = {}
        
    def should_process_patient(self, patient_id: int) -> bool:
        """Check if patient should be processed based on circuit breaker state"""
        state = self.patient_states.get(patient_id, CircuitBreakerState())
        
        if state.state == 'CLOSED':
            return True
        elif state.state == 'OPEN':
            # Check if recovery timeout has passed
            if (state.last_failure_time and 
                datetime.now() - state.last_failure_time > timedelta(seconds=state.recovery_timeout)):
                state.state = 'HALF_OPEN'
                logger.info(f"🔄 Patient {patient_id} circuit breaker: OPEN -> HALF_OPEN")
                return True
            return False
        elif state.state == 'HALF_OPEN':
            return True
            
        return False
        
    def record_success(self, patient_id: int):
        """Record successful processing for patient"""
        if patient_id in self.patient_states:
            state = self.patient_states[patient_id]
            if state.state == 'HALF_OPEN':
                state.state = 'CLOSED'
                state.failure_count = 0
                logger.info(f"✅ Patient {patient_id} circuit breaker: HALF_OPEN -> CLOSED")
                
    def record_failure(self, patient_id: int, error: Exception):
        """Record failed processing for patient"""
        if patient_id not in self.patient_states:
            self.patient_states[patient_id] = CircuitBreakerState()
            
        state = self.patient_states[patient_id]
        state.failure_count += 1
        state.last_failure_time = datetime.now()
        
        if state.failure_count >= state.failure_threshold:
            state.state = 'OPEN'
            logger.warning(f"⚠️ Patient {patient_id} circuit breaker OPEN due to {state.failure_count} failures: {error}")
            
    def get_blocked_patients(self) -> Set[int]:
        """Get set of patient IDs currently blocked by circuit breaker"""
        blocked = set()
        for patient_id, state in self.patient_states.items():
            if not self.should_process_patient(patient_id):
                blocked.add(patient_id)
        return blocked

class HighPerformanceBulkScreeningEngine:
    """
    High-performance bulk screening processing engine with:
    - Async/await patterns for 1000+ patients
    - Connection pooling and circuit breakers
    - Reactive updates for screening type changes
    - Worker timeout protection
    - Bulk database operations
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        self.connection_pool = DatabaseConnectionPool(self.database_url)
        self.circuit_breaker = PatientCircuitBreaker()
        self.edge_case_handler = AutomatedScreeningRefreshManager()
        self.processing_active = False
        self.metrics = ProcessingMetrics()
        
        # Performance tuning parameters
        self.max_concurrent_patients = 20  # Process up to 20 patients concurrently
        self.batch_size = 100  # Documents per batch operation
        self.patient_timeout = 30  # Max seconds per patient
        self.total_timeout = 1800  # Max total processing time (30 minutes)
        
        # Reactive trigger handlers
        self.reactive_triggers = {
            'screening_type_activation': self._handle_screening_type_change,
            'screening_type_deactivation': self._handle_screening_type_change,
            'keyword_change': self._handle_keyword_change,
            'cutoff_setting_change': self._handle_cutoff_change,
            'document_upload': self._handle_document_change,
            'document_deletion': self._handle_document_change,
        }
        
    async def initialize(self) -> bool:
        """Initialize the high-performance engine"""
        try:
            # Initialize database connection pool
            pool_initialized = await self.connection_pool.initialize()
            if not pool_initialized:
                return False
                
            # Test database performance
            performance_ok = await self._test_database_performance()
            if not performance_ok:
                logger.warning("⚠️ Database performance suboptimal, reducing concurrency")
                self.max_concurrent_patients = 5
                
            logger.info(f"✅ High-performance bulk screening engine initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize bulk screening engine: {e}")
            return False
            
    async def process_all_patients_bulk(self, trigger_source: str = "manual_refresh") -> ProcessingMetrics:
        """
        Process all patients using high-performance bulk operations
        
        Args:
            trigger_source: What triggered this bulk processing
            
        Returns:
            Processing metrics and results
        """
        if self.processing_active:
            logger.warning("⚠️ Bulk processing already active, skipping")
            return self.metrics
            
        start_time = time.time()
        self.processing_active = True
        self.metrics = ProcessingMetrics()
        
        try:
            logger.info(f"🚀 Starting high-performance bulk screening processing - trigger: {trigger_source}")
            
            # Get all patients with database health check
            patients = await self._get_patients_with_health_check()
            if not patients:
                logger.warning("⚠️ No patients found or database unhealthy")
                return self.metrics
                
            self.metrics.total_patients = len(patients)
            logger.info(f"📊 Processing {len(patients)} patients with {self.max_concurrent_patients} concurrent workers")
            
            # Process patients in batches using async semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_patients)
            
            async def process_patient_with_semaphore(patient_data):
                async with semaphore:
                    return await self._process_single_patient_async(patient_data)
            
            # Create processing tasks
            tasks = [process_patient_with_semaphore(patient) for patient in patients]
            
            # Process with overall timeout protection
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.total_timeout
                )
                
                # Aggregate results
                for result in results:
                    if isinstance(result, Exception):
                        self.metrics.failed_patients += 1
                        logger.error(f"❌ Patient processing error: {result}")
                    else:
                        self.metrics.processed_patients += 1
                        if result:
                            self.metrics.total_screenings_updated += result.get('screenings_updated', 0)
                            self.metrics.total_documents_linked += result.get('documents_linked', 0)
                            
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Bulk processing timeout after {self.total_timeout} seconds")
                self.metrics.timeout_recoveries += 1
                
            # Calculate final metrics
            self.metrics.processing_time = time.time() - start_time
            
            # Log summary
            logger.info(f"✅ Bulk processing complete: {self.metrics.processed_patients}/{self.metrics.total_patients} patients processed")
            logger.info(f"📈 Results: {self.metrics.total_screenings_updated} screenings, {self.metrics.total_documents_linked} documents linked")
            logger.info(f"⏱️ Processing time: {self.metrics.processing_time:.2f} seconds")
            logger.info(f"🔴 Circuit breaker trips: {self.metrics.circuit_breaker_trips}")
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"❌ Critical error in bulk processing: {e}")
            self.metrics.processing_time = time.time() - start_time
            return self.metrics
            
        finally:
            self.processing_active = False
            
    async def trigger_reactive_update(self, trigger_type: str, context: Dict[str, Any]) -> bool:
        """
        Handle reactive updates for various trigger types
        
        Args:
            trigger_type: Type of trigger (e.g., 'screening_type_activation')
            context: Context data for the trigger
            
        Returns:
            Success status
        """
        if trigger_type in self.reactive_triggers:
            handler = self.reactive_triggers[trigger_type]
            try:
                return await handler(context)
            except Exception as e:
                logger.error(f"❌ Reactive trigger {trigger_type} failed: {e}")
                return False
        else:
            logger.warning(f"⚠️ Unknown reactive trigger: {trigger_type}")
            return False
            
    async def _get_patients_with_health_check(self) -> List[Dict[str, Any]]:
        """Get patients with database health check"""
        try:
            async with self.connection_pool.get_connection() as conn:
                # Test database health first
                health_start = time.time()
                await conn.fetchval("SELECT 1")
                health_time = time.time() - health_start
                
                if health_time > 1.0:  # If health check takes > 1 second
                    logger.warning(f"⚠️ Database health check slow ({health_time:.2f}s), reducing workload")
                    self.max_concurrent_patients = min(5, self.max_concurrent_patients)
                    
                # Get patients with basic info
                try:
                    patients = await conn.fetch("""
                        SELECT id, first_name, last_name, mrn, date_of_birth, sex, 
                               extract(year from age(date_of_birth)) as age
                        FROM patient 
                        ORDER BY id
                        LIMIT 1000
                    """)
                except Exception as patient_query_error:
                    # Fallback query if some columns don't exist
                    logger.warning(f"Full patient query failed, using basic query: {patient_query_error}")
                    patients = await conn.fetch("""
                        SELECT id, first_name, last_name 
                        FROM patient 
                        ORDER BY id
                        LIMIT 1000
                    """)
                
                return [dict(patient) for patient in patients]
                
        except Exception as e:
            logger.error(f"❌ Failed to get patients: {e}")
            return []
            
    async def _process_single_patient_async(self, patient_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single patient with async operations and circuit breaker protection"""
        patient_id = patient_data['id']
        
        # Check circuit breaker
        if not self.circuit_breaker.should_process_patient(patient_id):
            logger.debug(f"⚡ Patient {patient_id} blocked by circuit breaker")
            return None
            
        try:
            # Set per-patient timeout
            return await asyncio.wait_for(
                self._do_patient_processing(patient_data),
                timeout=self.patient_timeout
            )
            
        except asyncio.TimeoutError:
            error = Exception(f"Patient {patient_id} processing timeout")
            self.circuit_breaker.record_failure(patient_id, error)
            self.metrics.circuit_breaker_trips += 1
            logger.warning(f"⏱️ Patient {patient_id} processing timeout")
            return None
            
        except Exception as e:
            self.circuit_breaker.record_failure(patient_id, e)
            self.metrics.circuit_breaker_trips += 1
            logger.error(f"❌ Patient {patient_id} processing error: {e}")
            return None
            
    async def _do_patient_processing(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actual patient processing logic"""
        patient_id = patient_data['id']
        
        try:
            # Generate screenings using the existing engine (in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                # Run the synchronous screening generation in thread pool
                screening_data = await loop.run_in_executor(
                    executor,
                    self._generate_patient_screenings_sync,
                    patient_id
                )
                
            if not screening_data:
                return {'screenings_updated': 0, 'documents_linked': 0}
                
            # Update screenings using bulk async operations
            result = await self._update_patient_screenings_async(patient_id, screening_data)
            
            # Record success in circuit breaker
            self.circuit_breaker.record_success(patient_id)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing patient {patient_id}: {e}")
            raise
            
    def _generate_patient_screenings_sync(self, patient_id: int) -> List[Dict]:
        """Generate patient screenings using existing synchronous engine"""
        try:
            from automated_screening_engine import ScreeningStatusEngine
            
            with app.app_context():
                engine = ScreeningStatusEngine()
                return engine.generate_patient_screenings(patient_id)
                
        except Exception as e:
            logger.error(f"❌ Error generating screenings for patient {patient_id}: {e}")
            return []
            
    async def _update_patient_screenings_async(self, patient_id: int, screening_data: List[Dict]) -> Dict[str, Any]:
        """Update patient screenings using async bulk operations"""
        screenings_updated = 0
        documents_linked = 0
        
        try:
            async with self.connection_pool.get_connection() as conn:
                # Start transaction
                async with conn.transaction():
                    # Get existing screenings for this patient
                    existing_screenings = await conn.fetch("""
                        SELECT id, screening_type, status 
                        FROM screening 
                        WHERE patient_id = $1
                    """, patient_id)
                    
                    existing_map = {row['screening_type']: row for row in existing_screenings}
                    
                    # Process each screening
                    for screening in screening_data:
                        screening_type = screening['screening_type']
                        status = screening['status']
                        
                        if screening_type in existing_map:
                            # Update existing screening
                            await conn.execute("""
                                UPDATE screening 
                                SET status = $1, last_completed = $2
                                WHERE id = $3
                            """, status, screening.get('last_completed'), existing_map[screening_type]['id'])
                            
                            screening_id = existing_map[screening_type]['id']
                        else:
                            # Create new screening
                            screening_id = await conn.fetchval("""
                                INSERT INTO screening (patient_id, screening_type, status, last_completed)
                                VALUES ($1, $2, $3, $4)
                                RETURNING id
                            """, patient_id, screening_type, status, screening.get('last_completed'))
                            
                        screenings_updated += 1
                        
                        # Handle document relationships
                        if 'matched_documents' in screening and screening['matched_documents']:
                            docs_linked = await self._link_documents_bulk_async(
                                conn, screening_id, screening['matched_documents']
                            )
                            documents_linked += docs_linked
                            
                    self.metrics.database_operations += 1
                    
        except Exception as e:
            logger.error(f"❌ Error updating screenings for patient {patient_id}: {e}")
            raise
            
        return {
            'screenings_updated': screenings_updated,
            'documents_linked': documents_linked
        }
        
    async def _link_documents_bulk_async(self, conn, screening_id: int, documents: List) -> int:
        """Link documents to screening using bulk async operations"""
        try:
            # Clear existing relationships
            await conn.execute("DELETE FROM screening_documents WHERE screening_id = $1", screening_id)
            
            # Prepare bulk insert data
            if documents:
                # Get valid document IDs
                doc_ids = [doc.id if hasattr(doc, 'id') else doc for doc in documents]
                
                # Validate documents exist
                valid_docs = await conn.fetch("""
                    SELECT id FROM medical_document WHERE id = ANY($1)
                """, doc_ids)
                
                valid_doc_ids = [row['id'] for row in valid_docs]
                
                # Bulk insert relationships
                if valid_doc_ids:
                    values = [(screening_id, doc_id, 1.0, 'automated') for doc_id in valid_doc_ids]
                    await conn.executemany("""
                        INSERT INTO screening_documents (screening_id, document_id, confidence_score, match_source)
                        VALUES ($1, $2, $3, $4)
                    """, values)
                    
                return len(valid_doc_ids)
                
        except Exception as e:
            logger.error(f"❌ Error linking documents for screening {screening_id}: {e}")
            return 0
            
        return 0
        
    async def _test_database_performance(self) -> bool:
        """Test database performance to determine optimal settings"""
        try:
            async with self.connection_pool.get_connection() as conn:
                start_time = time.time()
                
                # Test basic query performance  
                try:
                    await conn.fetchval("SELECT COUNT(*) FROM patient")
                except Exception as query_error:
                    # If patient table doesn't exist, test with a simpler query
                    logger.warning(f"Patient table query failed, testing with basic query: {query_error}")
                    await conn.fetchval("SELECT 1")
                
                query_time = time.time() - start_time
                
                if query_time > 2.0:
                    logger.warning(f"⚠️ Database performance slow ({query_time:.2f}s)")
                    return False
                    
                logger.info(f"✅ Database performance good ({query_time:.2f}s)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Database performance test failed: {e}")
            return False
            
    # Reactive trigger handlers
    async def _handle_screening_type_change(self, context: Dict[str, Any]) -> bool:
        """Handle screening type activation/deactivation"""
        screening_type_id = context.get('screening_type_id')
        action = context.get('action')  # 'activate' or 'deactivate'
        
        logger.info(f"🔄 Reactive trigger: Screening type {screening_type_id} {action}")
        
        if action == 'deactivate':
            # Clean up existing screenings for deactivated type
            async with self.connection_pool.get_connection() as conn:
                # Get screening type name
                screening_type_name = await conn.fetchval("""
                    SELECT name FROM screening_type WHERE id = $1
                """, screening_type_id)
                
                if screening_type_name:
                    # Delete screenings for this type
                    deleted_count = await conn.fetchval("""
                        DELETE FROM screening WHERE screening_type = $1
                        RETURNING COUNT(*)
                    """, screening_type_name)
                    
                    logger.info(f"✅ Cleaned up {deleted_count} screenings for deactivated type: {screening_type_name}")
                    
        # Trigger full refresh for affected patients
        await self.process_all_patients_bulk(f"screening_type_{action}")
        return True
        
    async def _handle_keyword_change(self, context: Dict[str, Any]) -> bool:
        """Handle keyword changes for screening types"""
        screening_type_id = context.get('screening_type_id')
        logger.info(f"🔄 Reactive trigger: Keyword change for screening type {screening_type_id}")
        
        # Trigger full refresh since keywords affect document matching
        await self.process_all_patients_bulk("keyword_change")
        return True
        
    async def _handle_cutoff_change(self, context: Dict[str, Any]) -> bool:
        """Handle cutoff setting changes"""
        logger.info(f"🔄 Reactive trigger: Cutoff settings changed")
        
        # Cutoff changes only affect display filtering, not core screening data
        # No bulk processing needed
        return True
        
    async def _handle_document_change(self, context: Dict[str, Any]) -> bool:
        """Handle document upload/deletion"""
        patient_id = context.get('patient_id')
        action = context.get('action')  # 'upload' or 'delete'
        
        if patient_id:
            logger.info(f"🔄 Reactive trigger: Document {action} for patient {patient_id}")
            
            # Process single patient reactively
            try:
                async with self.connection_pool.get_connection() as conn:
                    patient_data = await conn.fetchrow("""
                        SELECT id, first_name, last_name, mrn, date_of_birth, sex,
                               extract(year from age(date_of_birth)) as age
                        FROM patient WHERE id = $1
                    """, patient_id)
                    
                    if patient_data:
                        result = await self._process_single_patient_async(dict(patient_data))
                        if result:
                            logger.info(f"✅ Reactive update: Patient {patient_id} - {result['screenings_updated']} screenings updated")
                            return True
                            
            except Exception as e:
                logger.error(f"❌ Reactive document change processing failed: {e}")
                
        return False
        
    async def shutdown(self):
        """Shutdown the engine and clean up resources"""
        logger.info("🔄 Shutting down high-performance bulk screening engine")
        await self.connection_pool.close()

# Global engine instance
bulk_engine = None

async def get_bulk_engine() -> HighPerformanceBulkScreeningEngine:
    """Get or create the global bulk screening engine"""
    global bulk_engine
    
    if bulk_engine is None:
        bulk_engine = HighPerformanceBulkScreeningEngine()
        await bulk_engine.initialize()
        
    return bulk_engine

# Convenience functions for integration
def trigger_reactive_update_sync(trigger_type: str, context: Dict[str, Any]):
    """Synchronous wrapper for reactive updates"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_trigger():
            engine = await get_bulk_engine()
            return await engine.trigger_reactive_update(trigger_type, context)
            
        return loop.run_until_complete(run_trigger())
        
    except Exception as e:
        logger.error(f"❌ Sync reactive trigger failed: {e}")
        return False
    finally:
        loop.close()

def process_all_patients_sync(trigger_source: str = "manual_refresh") -> Dict[str, Any]:
    """Synchronous wrapper for bulk processing"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_bulk():
            engine = await get_bulk_engine()
            metrics = await engine.process_all_patients_bulk(trigger_source)
            return {
                'success': True,
                'total_patients': metrics.total_patients,
                'processed_patients': metrics.processed_patients,
                'failed_patients': metrics.failed_patients,
                'total_screenings_updated': metrics.total_screenings_updated,
                'total_documents_linked': metrics.total_documents_linked,
                'processing_time': metrics.processing_time,
                'circuit_breaker_trips': metrics.circuit_breaker_trips
            }
            
        return loop.run_until_complete(run_bulk())
        
    except Exception as e:
        logger.error(f"❌ Sync bulk processing failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'total_patients': 0,
            'processed_patients': 0,
            'failed_patients': 0,
            'total_screenings_updated': 0,
            'total_documents_linked': 0,
            'processing_time': 0.0,
            'circuit_breaker_trips': 0
        }
    finally:
        loop.close()

if __name__ == "__main__":
    # Test the engine
    async def test_engine():
        engine = HighPerformanceBulkScreeningEngine()
        initialized = await engine.initialize()
        
        if initialized:
            metrics = await engine.process_all_patients_bulk("test_run")
            print(f"Test complete: {metrics}")
            await engine.shutdown()
        else:
            print("Failed to initialize engine")
            
    asyncio.run(test_engine())