#!/usr/bin/env python3

import requests
import json
import sys

def test_ai_search():
    """Test the AI search functionality with authentication"""
    
    base_url = 'http://localhost:5000'
    
    # Test credentials
    username = 'testuser'
    password = 'testpass123'
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("🔐 Testing AI Search Authentication and Functionality")
    print("=" * 50)
    
    # Step 1: Get login page to check if server is running
    try:
        response = session.get(f'{base_url}/login')
        if response.status_code != 200:
            print(f"❌ Server not accessible. Status: {response.status_code}")
            return False
        print("✅ Server is running")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the web app is running on localhost:5000")
        return False
    
    # Step 2: Login
    print(f"\n🔑 Logging in as {username}...")
    login_data = {
        'username': username,
        'password': password
    }
    
    response = session.post(f'{base_url}/login', data=login_data, allow_redirects=False)
    
    if response.status_code == 302:  # Redirect indicates successful login
        print("✅ Login successful")
    else:
        print(f"❌ Login failed. Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return False
    
    # Step 3: Test AI Search API
    print("\n🤖 Testing AI Search functionality...")
    
    # Test queries
    test_queries = [
        "python files",
        "images",
        "documents",
        "links about programming",
        "files from last week"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        
        search_data = {
            'query': query,
            'include_files': True,
            'include_links': True,
            'limit': 5
        }
        
        response = session.post(
            f'{base_url}/api/ai-search',
            json=search_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            try:
                result = response.json()
                total_results = len(result.get('results', []))
                total_files = result.get('total_files', 0)
                total_links = result.get('total_links', 0)
                
                print(f"   ✅ Search successful")
                print(f"   📊 Results: {total_results} total ({total_files} files, {total_links} links)")
                
                # Show top result if available
                if result.get('results'):
                    top_result = result['results'][0]
                    result_type = top_result.get('type', 'unknown')
                    score = top_result.get('similarity_score', 0) * 100
                    if result_type == 'file':
                        name = top_result.get('filename', 'Unknown')
                    else:
                        name = top_result.get('link_domain', 'Unknown')
                    print(f"   🏆 Top result: {name} ({result_type}, {score:.1f}% match)")
                else:
                    print(f"   ℹ️  No results found for this query")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON response")
                print(f"   Response: {response.text[:200]}...")
        else:
            print(f"   ❌ Search failed. Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
    
    # Step 4: Test AI Search Stats
    print("\n📈 Testing AI Search Stats...")
    response = session.get(f'{base_url}/api/ai-search/stats')
    
    if response.status_code == 200:
        try:
            stats = response.json()
            print("✅ Stats retrieved successfully:")
            print(f"   📁 Files with embeddings: {stats.get('file_embeddings', 0)}")
            print(f"   🔗 Links with embeddings: {stats.get('link_embeddings', 0)}")
            print(f"   📊 Total files: {stats.get('total_files', 0)}")
            print(f"   🔗 Total links: {stats.get('total_links', 0)}")
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response for stats")
    else:
        print(f"❌ Stats request failed. Status: {response.status_code}")
    
    print("\n🎉 AI Search testing completed!")
    print("\n💡 You can now test the AI search manually by:")
    print(f"   1. Opening {base_url} in your browser")
    print(f"   2. Logging in with username: {username}, password: {password}")
    print(f"   3. Navigating to the AI Search page")
    print(f"   4. Trying different search queries")
    
    return True

if __name__ == '__main__':
    test_ai_search()