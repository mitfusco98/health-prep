#!/usr/bin/env python3
"""
More thorough analysis of potentially unused files
"""

import os
import ast
import glob
from typing import Set, Dict, List


def find_all_imports(file_path: str) -> Set[str]:
    """Find all import statements in a Python file"""
    imports = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return imports


def find_template_includes(file_path: str) -> Set[str]:
    """Find template includes/extends in HTML files"""
    includes = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Look for Jinja2 includes/extends
            import re

            patterns = [
                r'{% extends [\'"]([^\'"]+)[\'"] %}',
                r'{% include [\'"]([^\'"]+)[\'"] %}',
                r'{% import [\'"]([^\'"]+)[\'"]',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                includes.update(matches)
    except Exception as e:
        print(f"Error reading template {file_path}: {e}")

    return includes


def analyze_file_usage():
    """Analyze which files are actually used"""

    # Get all Python files
    python_files = glob.glob("*.py")
    template_files = glob.glob("templates/*.html")

    # Find all imports across all files
    all_imports = set()
    file_imports = {}

    for py_file in python_files:
        imports = find_all_imports(py_file)
        file_imports[py_file] = imports
        all_imports.update(imports)

    # Find template usage
    template_usage = set()
    for template_file in template_files:
        includes = find_template_includes(template_file)
        template_usage.update(includes)

    # Check which Python files are imported
    python_modules = {f.replace(".py", "") for f in python_files}
    imported_modules = {imp for imp in all_imports if imp in python_modules}

    # Files that appear unused (not imported by other files)
    potentially_unused = python_modules - imported_modules

    # Remove obvious main files and utility scripts that wouldn't be imported
    main_files = {"main", "app"}
    utility_scripts = {
        "add_default_screening_types",
        "add_test_patients",
        "analyze_unused_files",
        "change_admin_password",
        "create_admin_user",
        "create_admin_logs_table",
        "fix_admin_logs",
        "migrate_to_unified_config",
        "setup_secrets",
        "test_api_external",
        "direct_appointment_add",
        "fix_db",
        "optimize_db_queries",
        "secure_admin",
        "update_appointment_schema",
        "update_checklist_settings",
        "update_document_binary",
        "update_document_schema",
        "remove_screening_type_unique_constraint",
    }
    potentially_unused = potentially_unused - main_files - utility_scripts

    return {
        "all_files": python_files,
        "imported_modules": sorted(imported_modules),
        "potentially_unused": sorted(potentially_unused),
        "file_imports": file_imports,
        "template_usage": sorted(template_usage),
    }


def check_string_references(filename: str) -> List[str]:
    """Check if filename is referenced as a string in any file"""
    references = []
    for py_file in glob.glob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                if filename in content:
                    references.append(py_file)
        except Exception:
            pass
    return references


def main():
    print("Analyzing file usage...")
    analysis = analyze_file_usage()

    print(f"\n📊 Analysis Results:")
    print(f"Total Python files: {len(analysis['all_files'])}")
    print(f"Imported modules: {len(analysis['imported_modules'])}")
    print(f"Potentially unused: {len(analysis['potentially_unused'])}")

    print(f"\n✅ Files that ARE imported by other files:")
    for module in analysis["imported_modules"]:
        print(f"  - {module}.py")

    print(f"\n❓ Files that may be unused (not imported):")
    for module in analysis["potentially_unused"]:
        filename = f"{module}.py"
        if os.path.exists(filename):
            # Check for string references
            string_refs = check_string_references(module)
            if string_refs:
                print(
                    f"  - {filename} (but referenced as string in: {', '.join(string_refs)})"
                )
            else:
                print(f"  - {filename}")

    print(f"\n📄 Template includes found:")
    for template in analysis["template_usage"]:
        print(f"  - {template}")


if __name__ == "__main__":
    main()
