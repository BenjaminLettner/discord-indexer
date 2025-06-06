#!/usr/bin/env python3
import sys
import json
from discord_auth import DiscordOAuth2

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Filter out 'enabled' field
oauth_config = {k: v for k, v in config['discord_oauth'].items() if k != 'enabled'}

# Create OAuth instance
oauth = DiscordOAuth2(**oauth_config)

# Print authorization URL
print('Authorization URL:', oauth.get_authorization_url())
print('Redirect URI:', oauth.redirect_uri)
print('Client ID:', oauth.client_id)