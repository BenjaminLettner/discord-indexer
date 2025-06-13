# Discord OAuth2 Authentication Setup

This guide explains how to set up Discord OAuth2 authentication for the Discord Indexer application.

## Prerequisites

1. A Discord application with OAuth2 configured
2. Access to the Discord server where files are indexed
3. Appropriate roles set up in your Discord server

## Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Navigate to the "OAuth2" section in the left sidebar
4. Under "Redirects", add your callback URL:
   - For local development: `http://localhost:5000/auth/discord/callback`
   - For production: `https://yourdomain.com/auth/discord/callback`

## Step 2: Get Required Information

### Application Credentials
- **Client ID**: Found in the "General Information" section
- **Client Secret**: Found in the "OAuth2" section (click "Reset Secret" if needed)

### Discord Server Information
- **Guild ID**: Right-click your Discord server → "Copy Server ID" (requires Developer Mode)
- **Role Names**: Note the exact names of roles you want to require/grant admin access

## Step 3: Configure the Application

Edit the `config.json` file and update the `discord_oauth` section:

```json
{
  "discord_oauth": {
    "enabled": true,
    "client_id": "YOUR_DISCORD_CLIENT_ID",
    "client_secret": "YOUR_DISCORD_CLIENT_SECRET",
    "redirect_uri": "http://localhost:5000/auth/discord/callback",
    "required_guild_id": "YOUR_DISCORD_GUILD_ID",
    "required_roles": ["Member", "Verified"],
    "admin_roles": ["Admin", "Moderator"]
  }
}
```

### Configuration Options

- **enabled**: Set to `true` to enable Discord OAuth
- **client_id**: Your Discord application's Client ID
- **client_secret**: Your Discord application's Client Secret
- **redirect_uri**: The callback URL (must match what's configured in Discord)
- **required_guild_id**: The Discord server ID where users must be members
- **required_roles**: Array of role names that users must have (at least one)
- **admin_roles**: Array of role names that grant admin access in the application

## Step 4: Discord Bot Setup (Optional but Recommended)

For better role checking, you can set up a bot:

1. In your Discord application, go to the "Bot" section
2. Click "Add Bot"
3. Copy the bot token and add it to your `config.json`:

```json
{
  "discord": {
    "token": "YOUR_BOT_TOKEN",
    "guild_id": "YOUR_DISCORD_GUILD_ID"
  }
}
```

4. Invite the bot to your server with the following permissions:
   - View Channels
   - Read Message History

## Step 5: Required Discord Scopes

The application requests the following OAuth2 scopes:
- `identify`: Get user's basic profile information
- `email`: Get user's email address
- `guilds`: See what servers the user is in
- `guilds.members.read`: Read user's member information in guilds

## Step 6: Testing

1. Start the application: `python web_app.py`
2. Navigate to the login page
3. You should see a "Sign in with Discord" button
4. Click it to test the OAuth flow

## Troubleshooting

### Common Issues

1. **"Invalid redirect_uri"**
   - Ensure the redirect URI in `config.json` exactly matches what's configured in Discord
   - Check for trailing slashes or protocol mismatches

2. **"User not in required guild"**
   - Verify the `required_guild_id` is correct
   - Ensure the user is actually a member of the Discord server

3. **"User does not have required roles"**
   - Check that role names in `required_roles` match exactly (case-sensitive)
   - Verify the user has at least one of the required roles

4. **"Access token invalid"**
   - Check that your `client_secret` is correct
   - Ensure your Discord application has the correct scopes enabled

### Debug Mode

To enable debug logging, set the logging level to "DEBUG" in `config.json`:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## Security Considerations

1. **Keep your client secret secure** - Never commit it to version control
2. **Use HTTPS in production** - OAuth2 should always use secure connections
3. **Regularly rotate secrets** - Consider rotating your client secret periodically
4. **Validate redirect URIs** - Only use trusted domains for redirect URIs
5. **Monitor access logs** - Keep track of who's accessing your application

## Role-Based Access Control

### User Roles
- Users with any role in `required_roles` can log in
- Users with roles in `admin_roles` get admin privileges
- Users without required roles are denied access

### Example Role Setup
```json
{
  "required_roles": ["Member", "Verified", "Contributor"],
  "admin_roles": ["Admin", "Moderator", "Owner"]
}
```

In this setup:
- Users need "Member", "Verified", OR "Contributor" role to log in
- Users with "Admin", "Moderator", OR "Owner" role get admin access
- Admin roles automatically satisfy the required roles requirement