import requests

try:
    # Test accessing the document viewer
    response = requests.get('http://localhost:5000/document_viewer/11', 
                          auth=('testuser', 'testpass123'))
    
    if response.status_code == 200:
        # Save the HTML to a file for inspection
        with open('document_viewer_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print('HTML response saved to document_viewer_response.html')
        
        # Check for key elements
        html_content = response.text
        
        # Look for search-related elements
        search_elements = [
            'search-input',
            'search-stamps',
            'createSearchStamps',
            'performSearch',
            'search-highlight'
        ]
        
        print('\nChecking for search elements:')
        for element in search_elements:
            if element in html_content:
                print(f'✓ {element} found')
            else:
                print(f'✗ {element} NOT found')
                
        # Check if it's the right template
        if 'Document Viewer' in html_content:
            print('\n✓ This is the document viewer template')
        else:
            print('\n✗ This does not appear to be the document viewer template')
            
    else:
        print(f'Error: Status code {response.status_code}')
        
except Exception as e:
    print('Error:', e)