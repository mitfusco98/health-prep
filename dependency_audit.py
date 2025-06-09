
#!/usr/bin/env python3
"""
Analyze Python dependencies for unused packages
"""

import ast
import glob
import os
from typing import Set, Dict, List

def find_imports_in_file(file_path: str) -> Set[str]:
    """Find all imports in a Python file"""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get top-level package name
                    package = alias.name.split('.')[0]
                    imports.add(package)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get top-level package name
                    package = node.module.split('.')[0]
                    imports.add(package)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    
    return imports

def analyze_dependencies():
    """Analyze which dependencies are actually used"""
    
    # Dependencies from pyproject.toml
    declared_deps = {
        'email_validator': 'email-validator>=2.2.0',
        'flask_login': 'flask-login>=0.6.3', 
        'flask': 'flask>=3.1.0',
        'flask_sqlalchemy': 'flask-sqlalchemy>=3.1.1',
        'gunicorn': 'gunicorn>=23.0.0',
        'psycopg2': 'psycopg2-binary>=2.9.10',
        'pandas': 'pandas>=2.2.3',
        'flask_wtf': 'flask-wtf>=1.2.2',
        'trafilatura': 'trafilatura>=2.0.0',
        'openai': 'openai>=1.76.2',
        'requests': 'requests>=2.32.3',
        'docx': 'python-docx>=1.1.2',
        'sqlalchemy': 'sqlalchemy>=2.0.40',
        'werkzeug': 'werkzeug>=3.1.3',
        'wtforms': 'wtforms>=3.2.1',
        'flask_limiter': 'flask-limiter>=3.12',
        'magic': 'python-magic',
        'jwt': 'pyjwt>=2.10.1',
        'pydantic': 'pydantic>=2.11.4',
        'flask_dance': 'flask-dance>=7.1.0',
        'oauthlib': 'oauthlib>=3.2.2',
        'flask_jwt_extended': 'flask-jwt-extended>=4.7.1',
        'flask_compress': 'flask-compress>=1.17',
        'redis': 'redis>=6.2.0'
    }
    
    # Map package names to import names
    package_mapping = {
        'email_validator': 'email_validator',
        'flask_login': 'flask_login',
        'flask': 'flask',
        'flask_sqlalchemy': 'flask_sqlalchemy',
        'gunicorn': 'gunicorn',
        'psycopg2': 'psycopg2',
        'pandas': 'pandas',
        'flask_wtf': 'flask_wtf',
        'trafilatura': 'trafilatura',
        'openai': 'openai',
        'requests': 'requests',
        'docx': 'docx',
        'sqlalchemy': 'sqlalchemy',
        'werkzeug': 'werkzeug',
        'wtforms': 'wtforms',
        'flask_limiter': 'flask_limiter',
        'magic': 'magic',
        'jwt': 'jwt',
        'pydantic': 'pydantic',
        'flask_dance': 'flask_dance',
        'oauthlib': 'oauthlib',
        'flask_jwt_extended': 'flask_jwt_extended',
        'flask_compress': 'flask_compress',
        'redis': 'redis'
    }
    
    # Find all imports across codebase
    all_imports = set()
    python_files = glob.glob("*.py")
    
    for py_file in python_files:
        imports = find_imports_in_file(py_file)
        all_imports.update(imports)
    
    print("=== DEPENDENCY AUDIT REPORT ===\n")
    
    # Check which declared dependencies are used
    used_packages = []
    unused_packages = []
    
    for package, import_name in package_mapping.items():
        if import_name in all_imports:
            used_packages.append(package)
        else:
            unused_packages.append(package)
    
    print("✅ Used Dependencies:")
    for pkg in sorted(used_packages):
        print(f"  - {declared_deps.get(pkg, pkg)}")
    
    print(f"\n❌ Potentially Unused Dependencies ({len(unused_packages)}):")
    for pkg in sorted(unused_packages):
        print(f"  - {declared_deps.get(pkg, pkg)}")
    
    print(f"\n📊 Summary:")
    print(f"  Total declared: {len(declared_deps)}")
    print(f"  Used: {len(used_packages)}")
    print(f"  Unused: {len(unused_packages)}")
    print(f"  Potential savings: {(len(unused_packages)/len(declared_deps)*100):.1f}%")
    
    # Specific recommendations
    print(f"\n🔧 Specific Recommendations:")
    
    critical_unused = []
    if 'trafilatura' in unused_packages:
        critical_unused.append('trafilatura - web scraping library')
    if 'openai' in unused_packages:
        critical_unused.append('openai - AI/LLM integration')
    if 'pandas' in unused_packages:
        critical_unused.append('pandas - data analysis (large dependency)')
    if 'flask_dance' in unused_packages:
        critical_unused.append('flask-dance - OAuth integration')
    if 'redis' in unused_packages:
        critical_unused.append('redis - caching/sessions')
    if 'docx' in unused_packages:
        critical_unused.append('docx - duplicate of python-docx')
    
    if critical_unused:
        print("  High-impact removals:")
        for item in critical_unused:
            print(f"    - {item}")
    
    return unused_packages

if __name__ == "__main__":
    analyze_dependencies()
