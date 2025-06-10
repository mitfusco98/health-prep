#!/usr/bin/env python3
"""
Script to fix existing admin log entries that have missing or malformed data
"""

from app import app, db
from models import AdminLog, User
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def fix_admin_logs():
    """Fix existing admin logs with missing or malformed data"""
    try:
        with app.app_context():
            print("Starting admin log cleanup and fix...")

            # Get all admin logs
            logs = AdminLog.query.all()
            fixed_count = 0

            for log in logs:
                needs_update = False

                # Fix missing user information
                if log.user_id and not log.user:
                    try:
                        user = User.query.get(log.user_id)
                        if user:
                            # Update event details to include username if missing
                            try:
                                details = log.event_details_dict
                                if details and "username" not in details:
                                    details["username"] = user.username
                                    log.event_details = json.dumps(details)
                                    needs_update = True
                            except:
                                pass
                    except Exception as e:
                        logger.error(
                            f"Error fixing user info for log {log.id}: {str(e)}"
                        )

                # Fix malformed event_details
                if log.event_details:
                    try:
                        # Try to parse and reformat as proper JSON
                        details = log.event_details_dict
                        if details and "parsed" in details and not details["parsed"]:
                            # This indicates it failed to parse properly
                            # Try to extract what we can
                            raw_data = details.get("raw", "")

                            # Create a basic structure
                            new_details = {
                                "event_type": log.event_type,
                                "timestamp": (
                                    log.timestamp.isoformat()
                                    if log.timestamp
                                    else datetime.now().isoformat()
                                ),
                                "ip_address": log.ip_address or "Unknown",
                                "user_agent": log.user_agent or "Unknown",
                                "original_data": raw_data,
                            }

                            # Try to extract route information from raw data
                            if "route" in raw_data:
                                import re

                                route_match = re.search(
                                    r"'route':\s*'([^']*)'", raw_data
                                )
                                if route_match:
                                    new_details["route"] = route_match.group(1)

                            if "method" in raw_data:
                                method_match = re.search(
                                    r"'method':\s*'([^']*)'", raw_data
                                )
                                if method_match:
                                    new_details["method"] = method_match.group(1)

                            log.event_details = json.dumps(new_details)
                            needs_update = True

                    except Exception as e:
                        logger.error(
                            f"Error fixing event details for log {log.id}: {str(e)}"
                        )

                # Add missing IP address if possible
                if not log.ip_address:
                    try:
                        details = log.event_details_dict
                        if details and "ip_address" in details:
                            log.ip_address = details["ip_address"]
                            needs_update = True
                    except:
                        pass

                # Add missing user agent if possible
                if not log.user_agent:
                    try:
                        details = log.event_details_dict
                        if details and "user_agent" in details:
                            log.user_agent = details["user_agent"]
                            needs_update = True
                    except:
                        pass

                if needs_update:
                    fixed_count += 1

            # Commit all changes
            db.session.commit()
            print(f"Fixed {fixed_count} admin log entries")

            # Show summary of current logs
            total_logs = AdminLog.query.count()
            logs_with_users = AdminLog.query.filter(
                AdminLog.user_id.isnot(None)
            ).count()
            logs_with_details = AdminLog.query.filter(
                AdminLog.event_details.isnot(None)
            ).count()

            print(f"Summary:")
            print(f"  Total logs: {total_logs}")
            print(f"  Logs with users: {logs_with_users}")
            print(f"  Logs with details: {logs_with_details}")

    except Exception as e:
        logger.error(f"Error fixing admin logs: {str(e)}")
        db.session.rollback()
        raise


if __name__ == "__main__":
    fix_admin_logs()
