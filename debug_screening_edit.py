
#!/usr/bin/env python3
"""
Debug script for screening types edit functionality
Helps identify keyword duplication and form processing issues
"""

import requests
import json
import time
from bs4 import BeautifulSoup
import re

class ScreeningEditDebugger:
    def __init__(self, base_url="http://0.0.0.0:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_screening_types_list(self):
        """Test the screening types list page"""
        print("=" * 60)
        print("TESTING SCREENING TYPES LIST PAGE")
        print("=" * 60)
        
        try:
            response = self.session.get(f"{self.base_url}/screening-list?tab=types")
            print(f"Status Code: {response.status_code}")
            print(f"Response Length: {len(response.text)}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find screening types in the table
                screening_rows = soup.find_all('tr')[1:]  # Skip header
                print(f"Found {len(screening_rows)} screening type rows")
                
                for i, row in enumerate(screening_rows[:3]):  # Check first 3
                    cells = row.find_all('td')
                    if len(cells) > 0:
                        name_cell = cells[0]
                        screening_name = name_cell.find('strong')
                        if screening_name:
                            print(f"  Screening {i+1}: {screening_name.text.strip()}")
                            
                            # Look for keyword display
                            keyword_div = name_cell.find('div', class_='keyword-tags')
                            if keyword_div:
                                print(f"    Keywords div ID: {keyword_div.get('id', 'No ID')}")
                                print(f"    Keywords content: {keyword_div.text.strip()}")
                        
                        # Look for edit buttons
                        edit_btn = row.find('button', class_='edit-screening-btn')
                        if edit_btn:
                            screening_id = edit_btn.get('data-id')
                            print(f"    Edit button data-id: {screening_id}")
                            
            else:
                print(f"Error loading page: {response.text[:500]}")
                
        except Exception as e:
            print(f"Error testing screening types list: {e}")
    
    def test_keyword_api(self, screening_id):
        """Test the keyword API endpoint"""
        print("=" * 60)
        print(f"TESTING KEYWORD API FOR SCREENING {screening_id}")
        print("=" * 60)
        
        try:
            # Test GET keywords
            response = self.session.get(f"{self.base_url}/api/screening-keywords/{screening_id}")
            print(f"GET Status Code: {response.status_code}")
            print(f"GET Response: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    keywords = data.get('keywords', [])
                    print(f"Keywords count: {len(keywords)}")
                    print(f"Keywords: {keywords}")
                    
                    # Check for duplicates
                    unique_keywords = list(set([k.lower() for k in keywords if k]))
                    if len(keywords) != len(unique_keywords):
                        print(f"DUPLICATE DETECTION: {len(keywords)} total, {len(unique_keywords)} unique")
                        
                        # Show duplicates
                        seen = set()
                        duplicates = []
                        for keyword in keywords:
                            if keyword and keyword.lower() in seen:
                                duplicates.append(keyword)
                            elif keyword:
                                seen.add(keyword.lower())
                        print(f"Duplicate keywords: {duplicates}")
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    
        except Exception as e:
            print(f"Error testing keyword API: {e}")
    
    def test_edit_page_load(self, screening_id):
        """Test loading the edit page"""
        print("=" * 60)
        print(f"TESTING EDIT PAGE LOAD FOR SCREENING {screening_id}")
        print("=" * 60)
        
        try:
            response = self.session.get(f"{self.base_url}/screening-types/{screening_id}/edit")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check form elements
                form = soup.find('form')
                if form:
                    print(f"Form action: {form.get('action', 'No action')}")
                    print(f"Form method: {form.get('method', 'No method')}")
                
                # Check keyword-related elements
                keyword_input = soup.find('input', id='editKeywordInput')
                if keyword_input:
                    print("Found keyword input field")
                else:
                    print("WARNING: No keyword input field found")
                
                keyword_list = soup.find('div', id='editKeywordsList')
                if keyword_list:
                    print(f"Found keyword list container: {keyword_list.get('class', [])}")
                    print(f"Initial keyword list content: {keyword_list.text.strip()[:100]}")
                else:
                    print("WARNING: No keyword list container found")
                
                keyword_data = soup.find('input', id='editKeywordsData')
                if keyword_data:
                    print(f"Found hidden keyword data field")
                    print(f"Initial value: {keyword_data.get('value', 'No value')}")
                else:
                    print("WARNING: No hidden keyword data field found")
                
                # Check for JavaScript
                scripts = soup.find_all('script')
                js_content = ""
                for script in scripts:
                    if script.string:
                        js_content += script.string
                
                if 'KeywordManager' in js_content:
                    print("Found KeywordManager in JavaScript")
                else:
                    print("WARNING: KeywordManager not found in JavaScript")
                
                if 'setKeywords' in js_content:
                    print("Found setKeywords function in JavaScript")
                else:
                    print("WARNING: setKeywords function not found")
                    
            else:
                print(f"Error loading edit page: {response.text[:500]}")
                
        except Exception as e:
            print(f"Error testing edit page load: {e}")
    
    def test_keyword_javascript_flow(self, screening_id):
        """Test the JavaScript keyword flow by examining the page source"""
        print("=" * 60)
        print(f"TESTING JAVASCRIPT KEYWORD FLOW FOR SCREENING {screening_id}")
        print("=" * 60)
        
        try:
            response = self.session.get(f"{self.base_url}/screening-types/{screening_id}/edit")
            if response.status_code == 200:
                # Extract JavaScript content
                soup = BeautifulSoup(response.text, 'html.parser')
                scripts = soup.find_all('script')
                
                for i, script in enumerate(scripts):
                    if script.string and 'KeywordManager' in script.string:
                        js_content = script.string
                        print(f"JavaScript Block {i+1}:")
                        
                        # Look for key functions
                        functions = ['setKeywords', 'renderKeywords', 'addKeyword', 'removeKeyword']
                        for func in functions:
                            if func in js_content:
                                # Extract function definition
                                pattern = rf'{func}\s*\([^)]*\)\s*{{[^}}]*}}'
                                matches = re.findall(pattern, js_content, re.DOTALL)
                                if matches:
                                    print(f"  Found {func} function:")
                                    print(f"    Length: {len(matches[0])} characters")
                                    # Show first few lines
                                    lines = matches[0].split('\n')[:5]
                                    for line in lines:
                                        print(f"    {line.strip()}")
                                    print("    ...")
                        
                        # Look for fetch calls
                        fetch_pattern = r'fetch\s*\([^)]*\)'
                        fetch_calls = re.findall(fetch_pattern, js_content)
                        print(f"  Found {len(fetch_calls)} fetch calls")
                        for call in fetch_calls:
                            print(f"    {call}")
                            
        except Exception as e:
            print(f"Error testing JavaScript flow: {e}")
    
    def test_form_submission_simulation(self, screening_id):
        """Simulate form submission to test keyword processing"""
        print("=" * 60)
        print(f"TESTING FORM SUBMISSION SIMULATION FOR SCREENING {screening_id}")
        print("=" * 60)
        
        try:
            # First get the edit page to extract CSRF token
            response = self.session.get(f"{self.base_url}/screening-types/{screening_id}/edit")
            if response.status_code != 200:
                print(f"Failed to load edit page: {response.status_code}")
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = None
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
                print(f"Found CSRF token: {csrf_token[:20]}...")
            else:
                print("WARNING: No CSRF token found")
            
            # Get current form values
            name_input = soup.find('input', {'name': 'name'})
            current_name = name_input.get('value', '') if name_input else ''
            
            # Test form data with duplicate keywords
            test_keywords = ['test1', 'test2', 'test1', 'test3', 'test2']  # Intentional duplicates
            form_data = {
                'name': current_name or 'Test Screening',
                'keywords': json.dumps(test_keywords),
                'frequency_number': '1',
                'frequency_unit': 'years',
                'is_active': 'y'
            }
            
            if csrf_token:
                form_data['csrf_token'] = csrf_token
            
            print(f"Submitting form data: {form_data}")
            
            # Submit form (but don't actually - just prepare the request)
            print("Would submit to:", f"{self.base_url}/screening-types/{screening_id}/edit")
            print("Form data prepared successfully")
            
        except Exception as e:
            print(f"Error in form submission simulation: {e}")
    
    def run_full_debug(self, screening_id=None):
        """Run full debug suite"""
        print("SCREENING TYPES EDIT DEBUG SUITE")
        print("=" * 60)
        print(f"Testing against: {self.base_url}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Test list page first
        self.test_screening_types_list()
        print()
        
        # If no specific screening ID, try to find one
        if not screening_id:
            try:
                response = self.session.get(f"{self.base_url}/screening-list?tab=types")
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    edit_btn = soup.find('button', class_='edit-screening-btn')
                    if edit_btn:
                        screening_id = edit_btn.get('data-id')
                        print(f"Auto-detected screening ID: {screening_id}")
            except:
                pass
        
        if not screening_id:
            print("No screening ID provided and none could be auto-detected")
            return
        
        # Test API endpoint
        self.test_keyword_api(screening_id)
        print()
        
        # Test edit page load
        self.test_edit_page_load(screening_id)
        print()
        
        # Test JavaScript flow
        self.test_keyword_javascript_flow(screening_id)
        print()
        
        # Test form submission simulation
        self.test_form_submission_simulation(screening_id)
        print()
        
        print("=" * 60)
        print("DEBUG SUITE COMPLETE")
        print("=" * 60)

def main():
    import sys
    
    debugger = ScreeningEditDebugger()
    
    if len(sys.argv) > 1:
        screening_id = sys.argv[1]
    else:
        screening_id = None
    
    debugger.run_full_debug(screening_id)

if __name__ == "__main__":
    main()
