# 🎭 Ultimate Username Hunter & Auto-Claimer
![Version](https://img.shields.io/badge/Version-2.0-blueviolet?style=for-the-badge)
![Geode](https://img.shields.io/badge/Powered_by-AI_Assistance-green?style=for-the-badge)
![Discord](https://img.shields.io/badge/Discord-skiesfr-5865F2?style=for-the-badge&logo=discord&logoColor=white)

A collection of high-performance username availability checkers and automation tools for **Instagram, TikTok, Discord, Roblox, GitHub, Steam, and PSN**. Built to replace outdated scripts with modern, working API logic.

---

## 🚀 Core Features
* **Availability Checking:** Real-time API pings to verify if a handle is free.
* **Smart Generation:** Random name generator with **Custom Prefix** support.
* **Webhook Integration:** Get instant Discord notifications when a "hit" is found.
* **Auto-Claiming:** Integrated browser emulation to secure names the second they drop.

---

## 🔍 Supported Platforms & Technical Details

### 📸 Instagram
- **Method:** Requires Account Token.
- **Cool-down:** Built-in bypass system.
- **Note:** No proxies required; the API is stable.

### 🎵 TikTok & Auto-Claimer
- **Method:** Browser Emulation (Chrome) + Session ID.
- **Auto-Claimer:** Pairs with a Discord Bot to check webhooks every 5s and claim via browser.
- > ⚠️ **CRITICAL:** If a name shows available but won't claim, it’s likely a recently deleted account (30-day lock period applies).

### 💬 Discord
- **Warning:** API blocks after 3-4 searches.
- **Setup:** Includes a "No-Proxy" slow mode, but **Proxies are highly recommended**.

### 🤖 Roblox
- **Special Feature:** Includes **Auto-Account Creation** (Logic by `qing762/roblox-auto-signup`).
- **Automation:** Full webhook support and name generation.

### 🐙 GitHub & 💨 Steam
- **Status:** 100% Functional. Great for finding short IDs and rare handles.

### 🎮 PSN (PlayStation Network)
- **Known Issue:** Banned accounts may show as "Available" (False Positive).
- **Limit:** Private accounts cannot be detected due to Sony's API privacy.

---

## 🛠 Setup & Requirements

### 1. Browser Configuration
- **Browser:** [Google Chrome](https://www.google.com/chrome/) (Required for Auto-Claimer).
- **Extension:** [Cookie Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) to export Session IDs.

### 2. Installation
```bash
# Clone the repo
git clone [https://github.com/unfooled/Insta-tiktok-discord-name-checker-and-random-generator.git](https://github.com/unfooled/Insta-tiktok-discord-name-checker-and-random-generator.git)

# Install dependencies
pip install -r requirements.txt

# Run the tool
python main.py
