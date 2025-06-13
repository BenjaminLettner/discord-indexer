#!/usr/bin/env python3

import sys
import os
from user_manager import UserManager

def create_test_user():
    """Create a test user for authentication testing"""
    
    # Database path
    db_path = 'indexer.db'
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found!")
        return False
    
    # Initialize user manager
    user_manager = UserManager(db_path)
    
    # Test user credentials
    username = 'testuser'
    password = 'testpass123'
    email = 'test@example.com'
    is_admin = True  # Make admin to test all features
    
    print(f"Creating test user: {username}")
    
    # Create the user
    success = user_manager.create_user(
        username=username,
        password=password,
        email=email,
        is_admin=is_admin
    )
    
    if success:
        print(f"✅ Test user created successfully!")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Email: {email}")
        print(f"Admin: {is_admin}")
        print("\nYou can now login to the web interface with these credentials.")
        return True
    else:
        print(f"❌ Failed to create test user. User might already exist.")
        
        # Check if user already exists
        existing_user = user_manager.get_user_by_username(username)
        if existing_user:
            print(f"\nUser '{username}' already exists:")
            print(f"Username: {existing_user['username']}")
            print(f"Email: {existing_user['email']}")
            print(f"Admin: {existing_user['is_admin']}")
            print(f"Active: {existing_user['is_active']}")
            print(f"\nYou can use the existing credentials:")
            print(f"Username: {username}")
            print(f"Password: {password} (if not changed)")
        
        return False

if __name__ == '__main__':
    create_test_user()