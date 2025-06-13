import requests
import sys

# Create a session to maintain cookies
session = requests.Session()

try:
    # First, try to login
    login_data = {
        'username': 'testuser',
        'password': 'testpass123'
    }
    
    print('Attempting to login...')
    login_response = session.post('http://localhost:5000/login', data=login_data)
    print(f'Login status: {login_response.status_code}')
    
    if login_response.status_code == 200:
        print('Login successful, now accessing document viewer...')
        
        # Now try to access the document viewer
        viewer_response = session.get('http://localhost:5000/document_viewer/11')
        print(f'Document viewer status: {viewer_response.status_code}')
        
        if viewer_response.status_code == 200:
            html_content = viewer_response.text
            
            # Save the actual response
            with open('authenticated_viewer_response.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print('Authenticated response saved to authenticated_viewer_response.html')
            
            # Check for search elements
            search_elements = [
                'search-input',
                'search-stamps', 
                'createSearchStamps',
                'performSearch',
                'Document Viewer'
            ]
            
            print('\nChecking for elements:')
            for element in search_elements:
                if element in html_content:
                    print(f'✓ {element} found')
                else:
                    print(f'✗ {element} NOT found')
                    
        else:
            print(f'Failed to access document viewer: {viewer_response.status_code}')
            print('Response text:', viewer_response.text[:500])
    else:
        print(f'Login failed: {login_response.status_code}')
        print('Response text:', login_response.text[:500])
        
except Exception as e:
    print('Error:', e)