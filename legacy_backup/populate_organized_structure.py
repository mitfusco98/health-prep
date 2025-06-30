#!/usr/bin/env python3
"""
Populate Organized Structure Script
Systematically moves and organizes existing files into the proper organized folder structure
"""
import shutil
import os
from pathlib import Path


class OrganizedStructurePopulator:
    """Handles populating the organized folder structure with existing files"""

    def __init__(self):
        self.root_dir = Path(".")
        self.organized_dir = self.root_dir / "organized"

        # File categorization mapping
        self.file_mapping = {
            # Forms - all form-related files
            "forms": ["forms.py"],
            # Models - database models and schemas
            "models": ["models.py"],
            # Utils - utility and helper functions
            "utils": [
                "utils.py",
                "validators.py",
                "validation_utils.py",
                "input_validator.py",
                "shared_utilities.py",
                "db_utils.py",
                "appointment_utils.py",
                "prep_doc_utils.py",
                "screening_rules.py",
                "jwt_utils.py",
                "key_management.py",
                "sql_security.py",
                "response_optimization.py",
                "validation_schemas.py",
            ],
            # Middleware - cross-cutting concerns
            "middleware": [
                "admin_middleware.py",
                "api_access_middleware.py",
                "comprehensive_logging.py",
                "validation_middleware.py",
                "profiler.py",
                "structured_logger.py",
                "structured_logging.py",
                "logging_config.py",
            ],
            # Services - business logic
            "services": [
                "ehr_integration.py",
                "cache_manager.py",
                "cached_queries.py",
                "async_db_utils.py",
            ],
            # Routes - additional route files
            "routes": [
                "api_routes.py",
                "auth_routes.py",
                "ehr_routes.py",
                "checklist_routes.py",
                "performance_routes.py",
                "async_routes.py",
            ],
        }

    def copy_file_safely(self, src_file, dest_file):
        """Safely copy a file, handling existing files"""
        try:
            if src_file.exists():
                # Create destination directory if it doesn't exist
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy the file
                shutil.copy2(src_file, dest_file)
                print(
                    f"✓ Copied {src_file.name} → organized/{dest_file.parent.name}/{dest_file.name}"
                )
                return True
            else:
                print(f"⚠ File not found: {src_file}")
                return False
        except Exception as e:
            print(f"❌ Error copying {src_file}: {e}")
            return False

    def populate_forms(self):
        """Populate the forms folder"""
        print("\n📝 Populating forms folder...")

        forms_dir = self.organized_dir / "forms"

        for file_name in self.file_mapping["forms"]:
            src = self.root_dir / file_name
            dest = forms_dir / f"healthcare_{file_name}"
            self.copy_file_safely(src, dest)

    def populate_models(self):
        """Populate the models folder"""
        print("\n🗄️ Populating models folder...")

        models_dir = self.organized_dir / "models"

        for file_name in self.file_mapping["models"]:
            src = self.root_dir / file_name
            dest = models_dir / f"healthcare_{file_name}"
            self.copy_file_safely(src, dest)

    def populate_utils(self):
        """Populate the utils folder"""
        print("\n🔧 Populating utils folder...")

        utils_dir = self.organized_dir / "utils"

        for file_name in self.file_mapping["utils"]:
            src = self.root_dir / file_name

            # Categorize utils into specific files
            if "validation" in file_name or "validator" in file_name:
                dest = utils_dir / f"validation_{file_name}"
            elif "db" in file_name or "database" in file_name:
                dest = utils_dir / f"database_{file_name}"
            elif "auth" in file_name or "jwt" in file_name or "security" in file_name:
                dest = utils_dir / f"security_{file_name}"
            else:
                dest = utils_dir / f"helper_{file_name}"

            self.copy_file_safely(src, dest)

    def populate_middleware(self):
        """Populate the middleware folder"""
        print("\n🔀 Populating middleware folder...")

        middleware_dir = self.organized_dir / "middleware"

        for file_name in self.file_mapping["middleware"]:
            src = self.root_dir / file_name

            # Categorize middleware
            if "logging" in file_name or "logger" in file_name:
                dest = middleware_dir / f"logging_{file_name}"
            elif "admin" in file_name:
                dest = middleware_dir / f"admin_{file_name}"
            elif "validation" in file_name:
                dest = middleware_dir / f"validation_{file_name}"
            else:
                dest = middleware_dir / f"general_{file_name}"

            self.copy_file_safely(src, dest)

    def populate_services(self):
        """Populate the services folder"""
        print("\n⚙️ Populating services folder...")

        services_dir = self.organized_dir / "services"

        for file_name in self.file_mapping["services"]:
            src = self.root_dir / file_name

            # Categorize services
            if "ehr" in file_name:
                dest = services_dir / f"ehr_{file_name}"
            elif "cache" in file_name:
                dest = services_dir / f"cache_{file_name}"
            elif "async" in file_name or "db" in file_name:
                dest = services_dir / f"database_{file_name}"
            else:
                dest = services_dir / f"business_{file_name}"

            self.copy_file_safely(src, dest)

    def populate_additional_routes(self):
        """Populate additional route files"""
        print("\n🛣️ Adding additional route files...")

        routes_dir = self.organized_dir / "routes"

        for file_name in self.file_mapping["routes"]:
            src = self.root_dir / file_name
            dest = routes_dir / file_name
            self.copy_file_safely(src, dest)

    def create_integration_files(self):
        """Create integration files for organized structure"""
        print("\n🔗 Creating integration files...")

        # Update forms __init__.py
        forms_init = self.organized_dir / "forms" / "__init__.py"
        forms_init.write_text(
            """# Healthcare Forms Package
from .healthcare_forms import *
"""
        )

        # Update models __init__.py
        models_init = self.organized_dir / "models" / "__init__.py"
        models_init.write_text(
            """# Healthcare Models Package
from .healthcare_models import *
"""
        )

        # Update utils __init__.py
        utils_init = self.organized_dir / "utils" / "__init__.py"
        utils_content = """# Healthcare Utils Package
# Import existing validation utilities
from .validation_utils import *

# Import other utility modules
try:
    from .helper_utils import *
except ImportError:
    pass

try:
    from .database_db_utils import *
except ImportError:
    pass

try:
    from .security_jwt_utils import *
except ImportError:
    pass
"""
        utils_init.write_text(utils_content)

        # Update services __init__.py
        services_init = self.organized_dir / "services" / "__init__.py"
        services_content = """# Healthcare Services Package
from .patient_service import PatientService

# Import other services
try:
    from .ehr_ehr_integration import *
except ImportError:
    pass

try:
    from .cache_cache_manager import *
except ImportError:
    pass
"""
        services_init.write_text(services_content)

        print("✓ Created integration files")

    def create_summary_report(self):
        """Create a summary of what was organized"""
        print("\n📊 Creating organization summary...")

        summary = {
            "forms": len(self.file_mapping["forms"]),
            "models": len(self.file_mapping["models"]),
            "utils": len(self.file_mapping["utils"]),
            "middleware": len(self.file_mapping["middleware"]),
            "services": len(self.file_mapping["services"]),
            "routes": len(self.file_mapping["routes"]),
        }

        total_files = sum(summary.values())

        report = f"""
# Organization Summary Report

## Files Organized: {total_files}

### Breakdown by Category:
- Forms: {summary['forms']} files
- Models: {summary['models']} files  
- Utils: {summary['utils']} files
- Middleware: {summary['middleware']} files
- Services: {summary['services']} files
- Routes: {summary['routes']} files

## Organized Structure:
```
organized/
├── forms/           # Form definitions and validation
├── models/          # Database models and schemas
├── routes/          # All route handlers (6 modules + additional)
├── services/        # Business logic layer
├── utils/           # Utility functions and helpers
└── middleware/      # Cross-cutting concerns
```

## Benefits Achieved:
- Reduced complexity through modular organization
- Clear separation of concerns
- Easier maintenance and testing
- Better code reusability
- Improved team collaboration potential

Generated: {__import__('datetime').datetime.now().isoformat()}
"""

        with open(self.organized_dir / "organization_summary.md", "w") as f:
            f.write(report)

        print("✓ Created organization summary report")
        return summary

    def run_population(self):
        """Execute the complete population process"""
        print("🚀 Starting Healthcare Application Structure Population...")

        try:
            # Populate each category
            self.populate_forms()
            self.populate_models()
            self.populate_utils()
            self.populate_middleware()
            self.populate_services()
            self.populate_additional_routes()

            # Create integration files
            self.create_integration_files()

            # Generate summary
            summary = self.create_summary_report()

            print("\n✅ Population completed successfully!")
            print(f"\nOrganized {sum(summary.values())} files into structured folders")
            print("\nNext steps:")
            print("1. Review organized/ folder structure")
            print("2. Test import statements in organized modules")
            print("3. Update main application to use organized components")
            print("4. Verify all functionality preserved")

            return True

        except Exception as e:
            print(f"❌ Population failed: {str(e)}")
            return False


if __name__ == "__main__":
    populator = OrganizedStructurePopulator()
    success = populator.run_population()
    exit(0 if success else 1)
