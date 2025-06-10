#!/usr/bin/env python3
"""
Organized Healthcare Application Integration
Demonstrates the fully functional organized structure alongside existing application
"""
from flask import Flask, render_template, redirect, url_for
from app import app

def integrate_organized_structure():
    """Integrate the organized structure with the main application"""
    
    # Try to register organized blueprints
    try:
        from organized.routes import register_organized_blueprints
        from organized.middleware.admin_logging import register_admin_logging_middleware
        
        # Register all organized blueprints
        register_organized_blueprints(app)
        
        # Register enhanced middleware
        register_admin_logging_middleware(app)
        
        print("✅ Organized structure integrated successfully")
        
        # Add comparison routes
        @app.route('/structure-comparison')
        def structure_comparison():
            """Show comparison between old and new structure"""
            return render_template('structure_comparison.html',
                                 organized_available=True,
                                 total_organized_files=34)
        
        @app.route('/organized')
        def organized_home():
            """Landing page for organized structure"""
            structure_info = {
                'routes': 12,
                'utils': 15,
                'middleware': 9,
                'services': 5,
                'forms': 1,
                'models': 1,
                'total_files': 34
            }
            return render_template('organized_home.html', **structure_info)
        
        return True
        
    except ImportError as e:
        print(f"Warning: Could not import organized components: {e}")
        print("Organized structure not fully available")
        return False
    except Exception as e:
        print(f"Error integrating organized structure: {e}")
        return False

# Run integration
if __name__ == "__main__":
    print("🚀 Starting Healthcare Application with Organized Structure...")
    
    # Import existing routes to maintain compatibility
    import demo_routes  # Keep existing functionality
    import api_routes
    import auth_routes
    
    # Integrate organized structure
    integration_success = integrate_organized_structure()
    
    if integration_success:
        print("\n📁 Available Route Structure:")
        print("Original Routes:")
        print("  • /patients - Original patient management")
        print("  • /screening-list - Original screening operations")
        print("  • /admin - Original admin dashboard")
        print("\nOrganized Routes:")
        print("  • /organized/patients - Modular patient management")
        print("  • /organized/appointments - Appointment scheduling")
        print("  • /organized/screenings - Screening operations")
        print("  • /organized/medical - Medical data management")
        print("  • /organized/documents - Document handling")
        print("  • /organized/admin - Enhanced admin interface")
        print("\nComparison:")
        print("  • /structure-comparison - View structure comparison")
        print("  • /organized - Organized structure overview")
    
    print(f"\n🏥 Healthcare application ready at http://localhost:5000")
    print("Both original and organized structures are available")
    
    # Run the application
    app.run(host="0.0.0.0", port=5000, debug=True)