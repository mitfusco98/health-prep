#!/usr/bin/env python3
"""
Migration script to help transition to unified configuration system
Run this to identify files that need updating
"""

import os
import re
import glob
from typing import List, Dict, Tuple


def find_hardcoded_constants(file_path: str) -> List[Tuple[int, str]]:
    """Find hardcoded constants that should be moved to config"""
    constants_to_find = [
        r"PAGINATION_PER_PAGE\s*=\s*\d+",
        r"MAX_FILE_SIZE\s*=\s*\d+",
        r"SESSION_TIMEOUT\s*=\s*\d+",
        r"timedelta\(hours=\d+\)",
        r"pool_size\s*=\s*\d+",
        r"pool_timeout\s*=\s*\d+",
        r"WTF_CSRF_TIME_LIMIT\s*=\s*\d+",
        r"MAX_CONTENT_LENGTH\s*=\s*\d+",
    ]

    found_constants = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            for pattern in constants_to_find:
                if re.search(pattern, line):
                    found_constants.append((line_num, line.strip()))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return found_constants


def find_env_var_usage(file_path: str) -> List[Tuple[int, str]]:
    """Find direct environment variable usage"""
    env_patterns = [
        r'os\.environ\.get\([\'"][A-Z_]+[\'"]',
        r'os\.getenv\([\'"][A-Z_]+[\'"]',
    ]

    found_env_vars = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            for pattern in env_patterns:
                matches = re.findall(pattern, line)
                if matches:
                    found_env_vars.append((line_num, line.strip()))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return found_env_vars


def analyze_file(file_path: str) -> Dict:
    """Analyze a file for configuration issues"""
    return {
        "constants": find_hardcoded_constants(file_path),
        "env_vars": find_env_var_usage(file_path),
    }


def main():
    print("Unified Configuration Migration Analysis")
    print("=" * 50)

    # Find Python files to analyze
    python_files = []
    for pattern in ["*.py", "templates/*.html", "static/js/*.js"]:
        python_files.extend(glob.glob(pattern))

    # Exclude certain files
    exclude_files = [
        "migrate_to_unified_config.py",
        "config.py",
        "env_validator.py",  # Will be replaced
    ]

    python_files = [f for f in python_files if os.path.basename(f) not in exclude_files]

    total_issues = 0

    for file_path in sorted(python_files):
        if file_path.endswith(".py"):
            analysis = analyze_file(file_path)

            if analysis["constants"] or analysis["env_vars"]:
                print(f"\n📄 {file_path}")
                total_issues += 1

                if analysis["constants"]:
                    print("  🔧 Hardcoded constants found:")
                    for line_num, line in analysis["constants"]:
                        print(f"    Line {line_num}: {line}")

                if analysis["env_vars"]:
                    print("  🌍 Direct environment variable usage:")
                    for line_num, line in analysis["env_vars"]:
                        print(f"    Line {line_num}: {line}")

    if total_issues == 0:
        print("\n✅ No configuration issues found!")
    else:
        print(f"\n📊 Summary: {total_issues} files need attention")
        print("\nNext steps:")
        print("1. Update imports to use 'from config import get_config'")
        print("2. Replace hardcoded constants with config values")
        print("3. Replace direct os.environ.get() calls with config properties")
        print("4. Update JavaScript files to use AppConfig")
        print("5. Test thoroughly to ensure all functionality works")


if __name__ == "__main__":
    main()
