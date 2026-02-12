# Name checker & Auto-Claimer

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Discord](https://img.shields.io/badge/Discord-skiesfr-5865F2?style=for-the-badge&logo=discord&logoColor=white)

Most name checkers on GitHub are outdated and don't actually hit anymore. I built this project for fun because I wanted something that works with current APIs. AI helped me through the project to make sure the logic is solid and stays updated.

---

## Supported Platforms
Instagram, TikTok, Discord, Roblox, GitHub, Steam, and PlayStation.

---

## Features
* Username availability checking using current API logic.
* Random name generator with support for custom prefixes.
* Webhook support to send available names to Discord.
* Auto-claiming system using browser emulation.

---

## How it works

### Instagram
Requires an account token. It uses a built-in cooldown system to bypass blocks, so you do not need to use proxies for this part.

### TikTok & Auto-Claimer
You do not need a token or cookies just to check if a name is free. For the Auto-Claimer, the script uses Chrome and your session cookies from the Cookie Editor extension to emulate a real user. 
Note: If a name shows as available but won't claim, it is probably a deleted account. You have to wait out the 30-day lock period before it can be claimed.

### Discord
Supports the new username system. Discord rate-limits heavily after 3-4 searches, so proxies are recommended for this. There is a no-proxy mode included, but it is very slow.

### Roblox
Includes auto-account creation using logic from qing762/roblox-auto-signup. It checks availability and sends hits to your webhook.

### GitHub & Steam
Both of these work normally without any issues or special requirements.

### PlayStation
Fixed: This now uses the actual PSN API. Banned accounts and private accounts are no longer an issue, and the checker works perfectly.

---

## Setup

### Requirements
1. Have Google Chrome installed.
2. Use the Cookie Editor extension to get your session ID for the claimer.
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
