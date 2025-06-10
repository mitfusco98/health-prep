"""
Update the appointment table schema to add the status column
"""

from app import app, db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_status_column():
    """Add the status column to the appointment table"""
    try:
        with app.app_context():
            # Check if the column already exists
            conn = db.engine.connect()
            result = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='appointment' AND column_name='status'"
                )
            )
            columns = result.fetchall()

            if not columns:
                logger.info("Adding 'status' column to appointment table...")
                conn.execute(
                    text(
                        "ALTER TABLE appointment ADD COLUMN status VARCHAR(20) DEFAULT 'waiting'"
                    )
                )
                conn.commit()
                logger.info("Column 'status' added successfully")
            else:
                logger.info("Column 'status' already exists")

            conn.close()
    except Exception as e:
        logger.error(f"Error updating appointment table: {str(e)}")
        raise


if __name__ == "__main__":
    add_status_column()
    logger.info("Schema update completed")
