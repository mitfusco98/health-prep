"""
Direct Appointment Add Script

This script bypasses SQLAlchemy completely and adds an appointment directly
using raw SQL. Run this script directly to test database connectivity.
"""

import os
import sys
import psycopg2
from datetime import datetime, time
from psycopg2.extras import DictCursor


def add_appointment_direct():
    """Add an appointment directly to the database using raw SQL."""
    # Get database connection string from environment
    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        print("Error: DATABASE_URL environment variable not set.")
        return False

    print(f"Using database URL: {db_url}")

    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=DictCursor)

        # First get a valid patient ID using parameterized query
        cursor.execute(
            "SELECT id FROM patient ORDER BY id LIMIT %(limit)s", {"limit": 1}
        )
        patient_row = cursor.fetchone()

        if not patient_row:
            print("Error: No patients found in database.")
            return False

        patient_id = patient_row["id"]
        appointment_date = datetime.now().date()
        appointment_time = time(hour=9, minute=30)
        note = "Direct test appointment via raw SQL"

        # Insert the appointment using parameterized query
        cursor.execute(
            """
            INSERT INTO appointment 
            (patient_id, appointment_date, appointment_time, note, created_at, updated_at)
            VALUES (%(patient_id)s, %(appointment_date)s, %(appointment_time)s, %(note)s, %(created_at)s, %(updated_at)s)
            RETURNING id
            """,
            {
                "patient_id": patient_id,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "note": note,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )

        # Get the new appointment ID
        appointment_id = cursor.fetchone()[0]

        # Commit the transaction
        conn.commit()

        # Verify the appointment was created
        cursor.execute("SELECT * FROM appointment WHERE id = %s", (appointment_id,))
        new_appt = cursor.fetchone()

        print(f"Successfully created appointment with ID: {appointment_id}")
        print(f"Patient ID: {new_appt['patient_id']}")
        print(f"Date: {new_appt['appointment_date']}")
        print(f"Time: {new_appt['appointment_time']}")
        print(f"Note: {new_appt['note']}")

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM appointment")
        count = cursor.fetchone()[0]
        print(f"Total appointments in database: {count}")

        # Close connection
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"Error: {str(e)}")
        return False


if __name__ == "__main__":
    success = add_appointment_direct()
    if success:
        print("Script ran successfully!")
    else:
        print("Script failed!")
        sys.exit(1)
