import requests
import json
from urllib.parse import urlencode
from typing import Optional, Dict, List
import discord
import asyncio
from flask import session, current_app
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DiscordOAuth2:
    """Discord OAuth2 authentication handler"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, 
                 required_guild_id: str = None, required_roles: List[str] = None, 
                 admin_roles: List[str] = None, bot_token: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.required_guild_id = required_guild_id
        self.guild_id = required_guild_id  # Add this for compatibility
        self.required_roles = required_roles or []
        self.admin_roles = admin_roles or []
        self.bot_token = bot_token
        
        self.base_url = "https://discord.com/api/v10"
        self.api_endpoint = "https://discord.com/api/v10"  # Add this for compatibility
        self.oauth_url = "https://discord.com/api/oauth2"
    
    def get_authorization_url(self, state=None):
        """Generate Discord OAuth2 authorization URL"""
        scopes = ['identify', 'guilds', 'guilds.members.read']
        scope_string = '+'.join(scopes)
        
        url = f"https://discord.com/oauth2/authorize?response_type=code&client_id={self.client_id}&scope={scope_string}&redirect_uri={self.redirect_uri}"
        
        if state:
            url += f"&state={state}"
            
        return url
    
    def exchange_code(self, code):
        """Exchange authorization code for access token"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            print(f"DEBUG: Exchanging code for token with data: {data}")
            response = requests.post(f'{self.base_url}/oauth2/token', data=data, headers=headers)
            print(f"DEBUG: Token exchange response status: {response.status_code}")
            print(f"DEBUG: Token exchange response: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to exchange code for token: {e}")
            print(f"DEBUG: Token exchange error: {e}")
            return None
    
    def get_user_info(self, access_token):
        """Get user information from Discord API"""
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        try:
            print(f"DEBUG: Getting user info with token: {access_token[:20]}...")
            response = requests.get(f'{self.base_url}/users/@me', headers=headers)
            print(f"DEBUG: User info response status: {response.status_code}")
            print(f"DEBUG: User info response: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get user info: {e}")
            print(f"DEBUG: User info error: {e}")
            return None
    
    def get_user_guilds(self, access_token):
        """Get user's guilds from Discord API"""
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        try:
            print(f"DEBUG: Getting user guilds")
            response = requests.get(f'{self.base_url}/users/@me/guilds', headers=headers)
            print(f"DEBUG: User guilds response status: {response.status_code}")
            print(f"DEBUG: User guilds response: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get user guilds: {e}")
            print(f"DEBUG: User guilds error: {e}")
            return None
    
    def get_guild_member(self, user_id):
        """Get guild member information using bot token"""
        if not self.guild_id:
            logger.error("Guild ID not configured")
            print("DEBUG: Guild ID not configured")
            return None
            
        headers = {
            'Authorization': f'Bot {self.bot_token}'
        }
        
        try:
            print(f"DEBUG: Getting guild member for user {user_id} in guild {self.guild_id}")
            response = requests.get(
                f'{self.base_url}/guilds/{self.guild_id}/members/{user_id}',
                headers=headers
            )
            print(f"DEBUG: Guild member response status: {response.status_code}")
            print(f"DEBUG: Guild member response: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get guild member: {e}")
            print(f"DEBUG: Guild member error: {e}")
            return None
    
    def check_user_roles(self, user_id, guild_roles):
        """Check if user has required roles in the guild"""
        if not self.required_roles:
            print("DEBUG: No required roles configured")
            return True  # No specific roles required
        
        print(f"DEBUG: Checking roles for user {user_id}")
        print(f"DEBUG: Required roles: {self.required_roles}")
        
        member_info = self.get_guild_member(user_id)
        if not member_info:
            print("DEBUG: Could not get member info")
            return False
        
        user_role_ids = member_info.get('roles', [])
        print(f"DEBUG: User role IDs: {user_role_ids}")
        
        # Create a mapping of role names to IDs
        role_name_to_id = {role['name'].lower(): role['id'] for role in guild_roles}
        print(f"DEBUG: Available roles: {role_name_to_id}")
        
        # Check if user has any of the required roles
        for required_role in self.required_roles:
            required_role_lower = required_role.lower()
            print(f"DEBUG: Checking for required role: {required_role_lower}")
            
            # Check by role name
            if required_role_lower in role_name_to_id:
                role_id = role_name_to_id[required_role_lower]
                print(f"DEBUG: Found role {required_role_lower} with ID {role_id}")
                if role_id in user_role_ids:
                    print(f"DEBUG: User has required role {required_role_lower}")
                    return True
            
            # Check by role ID (if required_role is already an ID)
            if required_role in user_role_ids:
                print(f"DEBUG: User has required role by ID {required_role}")
                return True
        
        print("DEBUG: User does not have any required roles")
        return False
    
    def get_guild_roles(self):
        """Get all roles in the configured guild"""
        if not self.guild_id:
            print("DEBUG: No guild ID configured for roles")
            return []
            
        headers = {
            'Authorization': f'Bot {self.bot_token}'
        }
        
        try:
            print(f"DEBUG: Getting guild roles for guild {self.guild_id}")
            response = requests.get(
                f'{self.base_url}/guilds/{self.guild_id}/roles',
                headers=headers
            )
            print(f"DEBUG: Guild roles response status: {response.status_code}")
            print(f"DEBUG: Guild roles response: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get guild roles: {e}")
            print(f"DEBUG: Guild roles error: {e}")
            return []
    
    def is_user_in_guild(self, access_token):
        """Check if user is in the configured guild"""
        if not self.guild_id:
            print("DEBUG: No guild ID configured for membership check")
            return False
            
        user_guilds = self.get_user_guilds(access_token)
        if not user_guilds:
            print("DEBUG: Could not get user guilds")
            return False
        
        guild_ids = [guild['id'] for guild in user_guilds]
        print(f"DEBUG: User is in guilds: {guild_ids}")
        print(f"DEBUG: Required guild: {self.guild_id}")
        is_member = self.guild_id in guild_ids
        print(f"DEBUG: User is member of required guild: {is_member}")
        return is_member
    
    def get_user_roles_with_bot(self, user_id: str, guild_id: str) -> Optional[List[str]]:
        """Get user roles using bot token for more reliable access"""
        if not self.bot_token:
            return None
            
        try:
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }
            
            # Get guild member info
            response = requests.get(
                f'{self.base_url}/guilds/{guild_id}/members/{user_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                member_data = response.json()
                role_ids = member_data.get('roles', [])
                
                # Get guild roles to map IDs to names
                guild_response = requests.get(
                    f'{self.base_url}/guilds/{guild_id}/roles',
                    headers=headers
                )
                
                if guild_response.status_code == 200:
                    guild_roles = guild_response.json()
                    role_names = []
                    
                    for role in guild_roles:
                        if role['id'] in role_ids:
                            role_names.append(role['name'])
                    
                    return role_names
            
            return None
            
        except Exception as e:
            print(f"Error getting user roles with bot: {e}")
            return None
    
    def authenticate_user(self, code):
        """Complete authentication flow and return user data if authorized"""
        print(f"DEBUG: Starting authentication with code: {code[:20]}...")
        
        # Exchange code for token
        token_data = self.exchange_code(code)
        if not token_data:
            print("DEBUG: Failed to exchange code for token")
            return None
        
        access_token = token_data.get('access_token')
        if not access_token:
            print("DEBUG: No access token in response")
            return None
        
        print("DEBUG: Successfully got access token")
        
        # Get user info
        user_info = self.get_user_info(access_token)
        if not user_info:
            print("DEBUG: Failed to get user info")
            return None
        
        print(f"DEBUG: Got user info for: {user_info.get('username')}")
        
        # Check if user is in the required guild
        if not self.is_user_in_guild(access_token):
            logger.warning(f"User {user_info['username']} is not in the required guild")
            print(f"DEBUG: User {user_info['username']} is not in the required guild")
            return None
        
        print("DEBUG: User is in required guild")
        
        # Check user roles if required
        if self.required_roles:
            guild_roles = self.get_guild_roles()
            if not self.check_user_roles(user_info['id'], guild_roles):
                logger.warning(f"User {user_info['username']} does not have required roles")
                print(f"DEBUG: User {user_info['username']} does not have required roles")
                return None
        
        print("DEBUG: User has required roles")
        
        # Check if user has admin roles
        is_admin = False
        if self.admin_roles:
            user_roles = self.get_user_roles_with_bot(user_info['id'], self.guild_id)
            if user_roles:
                print(f"DEBUG: User roles: {user_roles}")
                print(f"DEBUG: Admin roles: {self.admin_roles}")
                # Check if user has any admin role
                for admin_role in self.admin_roles:
                    if admin_role in user_roles:
                        is_admin = True
                        print(f"DEBUG: User has admin role: {admin_role}")
                        break
            else:
                print("DEBUG: Could not get user roles for admin check")
        
        print(f"DEBUG: User admin status: {is_admin}")
        
        # Store token in session for future API calls
        session['discord_token'] = access_token
        session['discord_token_expires'] = datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
        
        print("DEBUG: Authentication successful")
        return {
            'id': user_info['id'],
            'username': user_info['username'],
            'discriminator': user_info.get('discriminator'),
            'avatar': user_info.get('avatar'),
            'email': user_info.get('email'),
            'is_admin': is_admin,
            'auth_method': 'discord'
        }