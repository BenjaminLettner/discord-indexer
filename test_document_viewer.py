import requests
import sys

try:
    # Test accessing the document viewer
    response = requests.get('http://localhost:5000/document_viewer/11', 
                          auth=('testuser', 'testpass123'))
    print('Status:', response.status_code)
    print('Content length:', len(response.text))
    
    # Check if the search stamps HTML is present
    if 'search-stamps' in response.text:
        print('✓ Search stamps HTML found in response')
    else:
        print('✗ Search stamps HTML NOT found in response')
        
    # Check if createSearchStamps function is present
    if 'createSearchStamps' in response.text:
        print('✓ createSearchStamps function found')
    else:
        print('✗ createSearchStamps function NOT found')
        
    # Check if the search input is present
    if 'search-input' in response.text:
        print('✓ Search input found')
    else:
        print('✗ Search input NOT found')
        
except Exception as e:
    print('Error:', e)