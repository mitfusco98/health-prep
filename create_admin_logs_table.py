
"""
Script to create the admin_logs table in the database.
"""
from app import app, db
from models import AdminLog
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_logs_table():
    """Create the admin_logs table"""
    try:
        with app.app_context():
            # Create the table
            db.create_all()
            logger.info("admin_logs table created successfully")
            
            # Verify the table exists
            from sqlalchemy import text
            result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name = 'admin_logs'"))
            if result.fetchone():
                logger.info("admin_logs table verified in database")
            else:
                logger.error("admin_logs table not found after creation")
                
    except Exception as e:
        logger.error(f"Error creating admin_logs table: {str(e)}")
        raise

if __name__ == "__main__":
    create_admin_logs_table()
    logger.info("Database update completed")
