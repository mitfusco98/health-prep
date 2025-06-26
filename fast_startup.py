
#!/usr/bin/env python3
"""
Fast Startup Optimization
Reduces application boot time by deferring non-critical operations
"""

import os
import time
import logging

# Set minimal logging during startup
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def optimize_startup():
    """Apply startup optimizations"""
    
    # Set environment variables for fastest startup
    os.environ.setdefault("FLASK_ENV", "development")
    os.environ.setdefault("LOG_LEVEL", "WARNING")  # Reduce logging overhead
    
    # Disable some features during startup
    os.environ.setdefault("SKIP_DB_INIT", "1")
    os.environ.setdefault("SKIP_ROUTE_LOADING", "1")
    os.environ.setdefault("MINIMAL_STARTUP", "1")
    
    start_time = time.time()
    
    try:
        # Import app with optimizations
        from app import app
        
        boot_time = time.time() - start_time
        print(f"✅ Fast startup completed in {boot_time:.2f} seconds")
        
        return app
        
    except Exception as e:
        boot_time = time.time() - start_time
        print(f"❌ Startup failed after {boot_time:.2f} seconds: {e}")
        raise

if __name__ == "__main__":
    app = optimize_startup()
    print("🚀 Application ready for requests")
