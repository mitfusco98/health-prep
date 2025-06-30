
#!/usr/bin/env python3
"""
Optimize PostgreSQL metadata query performance
"""

from app import app, db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def optimize_postgres_metadata():
    """Optimize PostgreSQL system catalog queries"""
    
    with app.app_context():
        try:
            # Check if we're using PostgreSQL
            if not str(db.engine.url).startswith('postgresql'):
                print("Not using PostgreSQL - skipping metadata optimization")
                return
                
            # These indexes may already exist but won't hurt to ensure they're there
            postgres_optimizations = [
                # Optimize table existence checks
                "CREATE INDEX IF NOT EXISTS pg_class_relname_idx ON pg_catalog.pg_class(relname);",
                "CREATE INDEX IF NOT EXISTS pg_class_relkind_idx ON pg_catalog.pg_class(relkind);",
                # Update table statistics to help query planner
                "ANALYZE pg_catalog.pg_class;",
                "ANALYZE pg_catalog.pg_namespace;",
            ]
            
            for optimization in postgres_optimizations:
                try:
                    print(f"Executing: {optimization}")
                    db.session.execute(text(optimization))
                    db.session.commit()
                except Exception as e:
                    print(f"Warning - could not execute {optimization}: {str(e)}")
                    db.session.rollback()
                    continue
                    
            print("✓ PostgreSQL metadata optimization completed!")
            
        except Exception as e:
            print(f"❌ Error optimizing PostgreSQL metadata: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    optimize_postgres_metadata()
