from app import db
import psycopg2
import os

# Get database connection details from environment
DB_URL = os.environ.get("DATABASE_URL")

try:
    # Parse the DB URL to get connection parameters
    if DB_URL:
        # Extract connection params
        db_parts = DB_URL.split("//")[1].split("@")
        credentials = db_parts[0].split(":")
        host_port = db_parts[1].split("/")[0].split(":")
        db_name = db_parts[1].split("/")[1].split("?")[0]
        
        username = credentials[0]
        password = credentials[1]
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else "5432"
        
        # Direct connection to terminate all sessions
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            dbname=db_name
        )
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            # Terminate all other connections
            cursor.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid()
            """, (db_name,))
            
            print("All database connections terminated!")
            
            # Check if there are any active transactions
            cursor.execute("SELECT * FROM pg_stat_activity WHERE state = 'active'")
            active_connections = cursor.fetchall()
            print(f"Active connections: {len(active_connections)}")
            
            # Add the document_name column to the medical_document table if it doesn't exist
            print("Checking if document_name column exists in medical_document table...")
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'medical_document' AND column_name = 'document_name'")
            if not cursor.fetchone():
                print("document_name column doesn't exist. Adding it now...")
                cursor.execute("ALTER TABLE medical_document ADD COLUMN document_name VARCHAR(255)")
                print("document_name column added successfully!")
                
                # Update existing records to set document_name from filename
                print("Updating existing records to set document_name from filename...")
                cursor.execute("UPDATE medical_document SET document_name = filename WHERE document_name IS NULL AND filename IS NOT NULL")
                print(f"Updated {cursor.rowcount} records with document names from filenames.")
            else:
                print("document_name column already exists.")
                
            # Make sure all records have a document_name
            cursor.execute("""
                UPDATE medical_document 
                SET document_name = CONCAT('Document ID ', id) 
                WHERE document_name IS NULL
            """)
            print(f"Updated {cursor.rowcount} records with default document names.")
            
        conn.close()
        print("Database connection pool refreshed")
    
except Exception as e:
    print(f"Error: {str(e)}")

print("Database reset process complete.")
