# Username Checker and Auto Claimer

A collection of username availability checkers for Instagram, TikTok, Discord, Roblox, GitHub, Steam, and PSN. Most of the code was made with AI assistance because I wanted to create something that actually works since most of the current scripts out there are outdated.

## Features

All checkers include:
- Username availability checking
- Random username generation
- Custom prefix support for generated names
- Webhook notifications for available usernames

## Available Checkers

### Instagram Checker
- Requires Instagram account token
- Check any username availability
- Generate random usernames with optional prefixes
- Built-in cooldown system to bypass API blocks
- No proxy needed since Instagram's API is pretty chill

### TikTok Checker
- No token or cookies required
- Check username availability
- Generate random usernames
- Note: If a username shows as available but you can't claim it, the account was likely deleted and you need to wait up to 30 days

### Discord Checker
- Discord API blocks after 3-4 searches, so proxies are recommended
- Includes a no-proxy version but it's slower
- Same generation features as other checkers

### Roblox Checker
- Auto account creation feature using code from qing762/roblox-auto-signup
- Username availability checking
- Webhook notifications
- Random name generation

### GitHub Checker
- Check GitHub username availability

### Steam Checker
- Works perfectly for checking Steam IDs

### PSN Checker
- Some false positives (banned accounts may show as available, private accounts can't be detected)
- I can't really fix these issues, it's just how their API works

## TikTok Auto Claimer

Automatically attempts to claim TikTok usernames as they become available.

### Requirements
- Chrome browser installed
- Cookie Editor extension: https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm

### How it Works
1. Gets your session ID/cookies from the Cookie Editor extension
2. Emulates a browser session
3. Logs in and checks if the username is available
4. If available, attempts to claim it
5. If not available, moves to the next username

### Pro Tip
Pair this with the TikTok username checker:
1. Set up the checker to send available usernames to a webhook
2. Create a Discord bot (the script has step-by-step instructions)
3. The bot checks every 5 seconds for new available usernames
4. Automatically tries to claim them in your browser

Note: This script is not made to spam TikTok with change requests.

## Installation

Install the required dependencies:
```
pip install -r requirements.txt
```

## Known Issues

- When the script gives a proxy error, you might need to copy and paste the error message to see the full details (I think I fixed this)
- TikTok usernames might show as available but can't be claimed if the account was recently deleted (30-day lock period)

## Credits

Roblox auto account creation based on: https://github.com/qing762/roblox-auto-signup
