"""
Admin Log Cleanup Script
Automatically removes admin log entries older than 10 days
"""

from datetime import datetime, timedelta
from models import AdminLog, db
import logging

logger = logging.getLogger(__name__)

def cleanup_old_admin_logs(days_to_keep=10):
    """
    Remove admin log entries older than the specified number of days
    
    Args:
        days_to_keep: Number of days of logs to retain (default: 10)
    
    Returns:
        int: Number of records deleted
    """
    try:
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Find old records
        old_logs = AdminLog.query.filter(AdminLog.timestamp < cutoff_date)
        count_to_delete = old_logs.count()
        
        if count_to_delete > 0:
            # Delete old records
            old_logs.delete()
            db.session.commit()
            
            logger.info(f"Cleaned up {count_to_delete} admin log entries older than {days_to_keep} days")
            return count_to_delete
        else:
            logger.info(f"No admin log entries older than {days_to_keep} days found")
            return 0
            
    except Exception as e:
        logger.error(f"Error during admin log cleanup: {str(e)}")
        db.session.rollback()
        return 0

def get_admin_log_stats():
    """Get statistics about admin logs"""
    try:
        total_logs = AdminLog.query.count()
        
        # Get logs by age
        today = datetime.now()
        logs_last_24h = AdminLog.query.filter(
            AdminLog.timestamp >= today - timedelta(hours=24)
        ).count()
        
        logs_last_7_days = AdminLog.query.filter(
            AdminLog.timestamp >= today - timedelta(days=7)
        ).count()
        
        oldest_log = AdminLog.query.order_by(AdminLog.timestamp.asc()).first()
        newest_log = AdminLog.query.order_by(AdminLog.timestamp.desc()).first()
        
        return {
            'total_logs': total_logs,
            'logs_last_24h': logs_last_24h,
            'logs_last_7_days': logs_last_7_days,
            'oldest_log_date': oldest_log.timestamp if oldest_log else None,
            'newest_log_date': newest_log.timestamp if newest_log else None
        }
        
    except Exception as e:
        logger.error(f"Error getting admin log stats: {str(e)}")
        return None

if __name__ == '__main__':
    # Run cleanup when script is executed directly
    from app import app
    
    with app.app_context():
        print("Admin Log Cleanup Starting...")
        
        # Show current stats
        stats = get_admin_log_stats()
        if stats:
            print(f"Current admin log statistics:")
            print(f"  Total logs: {stats['total_logs']}")
            print(f"  Last 24 hours: {stats['logs_last_24h']}")
            print(f"  Last 7 days: {stats['logs_last_7_days']}")
            if stats['oldest_log_date']:
                print(f"  Oldest log: {stats['oldest_log_date']}")
        
        # Perform cleanup
        deleted_count = cleanup_old_admin_logs(10)
        print(f"Cleanup completed. Deleted {deleted_count} old log entries.")
        
        # Show updated stats
        updated_stats = get_admin_log_stats()
        if updated_stats:
            print(f"Updated total logs: {updated_stats['total_logs']}")