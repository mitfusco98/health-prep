import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class AsyncDatabaseManager:
    def __init__(self, database_url):
        self.engine = create_async_engine(
            database_url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    @asynccontextmanager
    async def get_session(self):
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()

    async def execute_query(self, query, params=None):
        """Execute a raw SQL query asynchronously"""
        async with self.engine.begin() as conn:
            result = await conn.execute(query, params or {})
            return result.fetchall()

    async def get_patient_count(self):
        """Non-blocking patient count"""
        query = "SELECT COUNT(*) FROM patient"
        result = await self.execute_query(query)
        return result[0][0] if result else 0

    async def get_today_appointments_count(self):
        """Non-blocking today's appointments count"""
        query = "SELECT COUNT(*) FROM appointment WHERE appointment_date = CURRENT_DATE"
        result = await self.execute_query(query)
        return result[0][0] if result else 0

    async def get_recent_documents_count(self, days=7):
        """Non-blocking recent documents count"""
        query = """
        SELECT COUNT(*) FROM medical_document 
        WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
        """
        result = await self.execute_query(query, {"days": days})
        return result[0][0] if result else 0

    async def search_patients_async(self, search_term, limit=20):
        """Non-blocking patient search"""
        query = """
        SELECT id, first_name, last_name, mrn, date_of_birth, phone, email
        FROM patient 
        WHERE first_name ILIKE %s OR last_name ILIKE %s OR mrn ILIKE %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        search_pattern = f"%{search_term}%"
        result = await self.execute_query(
            query, [search_pattern, search_pattern, search_pattern, limit]
        )
        return [dict(row) for row in result]

    async def close(self):
        """Close the async engine"""
        await self.engine.dispose()


# Global async database manager
async_db = None


def init_async_db(database_url):
    """Initialize async database manager"""
    global async_db
    async_db = AsyncDatabaseManager(database_url)
    return async_db
