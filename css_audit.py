
#!/usr/bin/env python3
"""
CSS Audit Script - Analyze unused styles and duplicated utility usage
"""

import os
import re
import glob
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple

def extract_css_rules(css_file_path: str) -> Dict[str, List[str]]:
    """Extract CSS rules and their properties from a CSS file"""
    rules = {}
    
    try:
        with open(css_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Find CSS rules
        rule_pattern = r'([^{}]+)\s*\{([^{}]+)\}'
        matches = re.findall(rule_pattern, content)
        
        for selector, properties in matches:
            selector = selector.strip()
            prop_list = []
            
            # Parse properties
            for prop in properties.split(';'):
                prop = prop.strip()
                if prop:
                    prop_list.append(prop)
            
            rules[selector] = prop_list
    
    except Exception as e:
        print(f"Error reading {css_file_path}: {e}")
    
    return rules

def find_class_usage_in_templates(template_dir: str) -> Set[str]:
    """Find all CSS classes used in HTML templates"""
    used_classes = set()
    
    # Get all HTML files
    html_files = glob.glob(os.path.join(template_dir, "*.html"))
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find class attributes
            class_pattern = r'class=["\']([^"\']+)["\']'
            matches = re.findall(class_pattern, content)
            
            for match in matches:
                # Split multiple classes
                classes = match.split()
                used_classes.update(classes)
        
        except Exception as e:
            print(f"Error reading {html_file}: {e}")
    
    return used_classes

def find_class_usage_in_js(js_dir: str) -> Set[str]:
    """Find CSS classes referenced in JavaScript files"""
    used_classes = set()
    
    js_files = glob.glob(os.path.join(js_dir, "*.js"))
    
    for js_file in js_files:
        try:
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find class references in JavaScript
            patterns = [
                r'addClass\(["\']([^"\']+)["\']',
                r'removeClass\(["\']([^"\']+)["\']',
                r'hasClass\(["\']([^"\']+)["\']',
                r'classList\.add\(["\']([^"\']+)["\']',
                r'classList\.remove\(["\']([^"\']+)["\']',
                r'classList\.contains\(["\']([^"\']+)["\']',
                r'className\s*=\s*["\']([^"\']+)["\']',
                r'getElementsByClassName\(["\']([^"\']+)["\']',
                r'querySelector\(["\']\.([^"\']+)["\']',
                r'querySelectorAll\(["\']\.([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    classes = match.split()
                    used_classes.update(classes)
        
        except Exception as e:
            print(f"Error reading {js_file}: {e}")
    
    return used_classes

def extract_css_classes_from_rules(css_rules: Dict[str, List[str]]) -> Set[str]:
    """Extract class names from CSS selectors"""
    classes = set()
    
    for selector in css_rules.keys():
        # Find class selectors (starting with .)
        class_matches = re.findall(r'\.([a-zA-Z][a-zA-Z0-9_-]*)', selector)
        classes.update(class_matches)
    
    return classes

def find_duplicate_properties(css_rules: Dict[str, List[str]]) -> List[Tuple[str, str, List[str]]]:
    """Find selectors with duplicate properties"""
    property_groups = defaultdict(list)
    
    for selector, properties in css_rules.items():
        prop_set = frozenset(properties)
        if len(properties) > 1:  # Only check selectors with multiple properties
            property_groups[prop_set].append(selector)
    
    duplicates = []
    for prop_set, selectors in property_groups.items():
        if len(selectors) > 1:
            duplicates.append((list(prop_set), selectors))
    
    return duplicates

def analyze_property_usage(css_rules: Dict[str, List[str]]) -> Dict[str, int]:
    """Count usage of CSS properties"""
    property_counter = Counter()
    
    for properties in css_rules.values():
        for prop in properties:
            # Extract property name (before colon)
            prop_name = prop.split(':')[0].strip()
            property_counter[prop_name] += 1
    
    return dict(property_counter)

def main():
    print("🔍 CSS Audit Report")
    print("=" * 50)
    
    # Analyze CSS files
    css_files = ['static/css/custom.css', 'static/css/button-fix.css']
    all_css_rules = {}
    
    print("\n📄 CSS Files Analysis:")
    for css_file in css_files:
        if os.path.exists(css_file):
            rules = extract_css_rules(css_file)
            all_css_rules[css_file] = rules
            print(f"  {css_file}: {len(rules)} rules found")
        else:
            print(f"  {css_file}: File not found")
    
    # Find used classes in templates and JS
    template_classes = find_class_usage_in_templates('templates')
    js_classes = find_class_usage_in_js('static/js')
    all_used_classes = template_classes | js_classes
    
    print(f"\n🎯 Class Usage Analysis:")
    print(f"  Classes found in templates: {len(template_classes)}")
    print(f"  Classes found in JavaScript: {len(js_classes)}")
    print(f"  Total unique classes used: {len(all_used_classes)}")
    
    # Extract CSS classes from all rules
    all_css_classes = set()
    for css_file, rules in all_css_rules.items():
        css_classes = extract_css_classes_from_rules(rules)
        all_css_classes.update(css_classes)
        print(f"  Classes defined in {css_file}: {len(css_classes)}")
    
    # Find unused CSS classes
    unused_classes = all_css_classes - all_used_classes
    
    print(f"\n❌ Unused CSS Classes ({len(unused_classes)}):")
    if unused_classes:
        for css_class in sorted(unused_classes):
            print(f"  .{css_class}")
    else:
        print("  No unused classes found!")
    
    # Find classes used but not defined
    undefined_classes = all_used_classes - all_css_classes
    print(f"\n⚠️  Classes Used But Not Defined ({len(undefined_classes)}):")
    if undefined_classes:
        for css_class in sorted(undefined_classes):
            print(f"  .{css_class} (likely Bootstrap/external)")
    else:
        print("  All used classes are defined!")
    
    # Analyze duplicates
    print(f"\n🔄 Duplicate Analysis:")
    for css_file, rules in all_css_rules.items():
        duplicates = find_duplicate_properties(rules)
        if duplicates:
            print(f"  {css_file} - Potential duplicates found:")
            for properties, selectors in duplicates:
                print(f"    Selectors: {', '.join(selectors)}")
                print(f"    Shared properties: {len(properties)}")
        else:
            print(f"  {css_file} - No obvious duplicates")
    
    # Property usage analysis
    print(f"\n📊 Property Usage Statistics:")
    all_properties = {}
    for css_file, rules in all_css_rules.items():
        props = analyze_property_usage(rules)
        all_properties[css_file] = props
        
        print(f"  {css_file}:")
        sorted_props = sorted(props.items(), key=lambda x: x[1], reverse=True)
        for prop, count in sorted_props[:5]:  # Top 5 most used
            print(f"    {prop}: {count} times")
    
    # Specific issues found
    print(f"\n🔧 Specific Issues Found:")
    
    # Check for !important overuse
    important_count = 0
    for css_file, rules in all_css_rules.items():
        for selector, properties in rules.items():
            for prop in properties:
                if '!important' in prop:
                    important_count += 1
    
    if important_count > 0:
        print(f"  ⚠️  {important_count} properties use !important (consider refactoring)")
    
    # Check for overly specific selectors
    complex_selectors = []
    for css_file, rules in all_css_rules.items():
        for selector in rules.keys():
            if len(selector.split()) > 3:  # More than 3 parts
                complex_selectors.append((css_file, selector))
    
    if complex_selectors:
        print(f"  ⚠️  {len(complex_selectors)} overly complex selectors found")
        for css_file, selector in complex_selectors[:3]:  # Show first 3
            print(f"    {css_file}: {selector}")
    
    print(f"\n✅ Audit Complete!")

if __name__ == "__main__":
    main()
