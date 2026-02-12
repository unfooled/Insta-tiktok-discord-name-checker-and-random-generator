# 🔍 Name Hunter & Auto-Claimer

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Discord](https://img.shields.io/badge/Discord-skiesfr-5865F2?style=for-the-badge&logo=discord&logoColor=white)

Most name checkers out there are outdated and don't actually hit. I built this for fun because I wanted something that works. **AI helped me through the project** to keep the logic updated with current APIs.

---

## 📱 Platforms
| Platform | Icon | Platform | Icon |
| :--- | :---: | :--- | :---: |
| **Instagram** | 📸 | **TikTok** | 🎵 |
| **Discord** | 💬 | **Roblox** | 🤖 |
| **GitHub** | 🐙 | **Steam** | 💨 |
| **PlayStation** | 🎮 | **Webhooks** | 🔗 |

---

## ⚡ Features
* **Availability Checking:** Pings APIs to see if names are free.
* **Random Generation:** Generates names with custom prefixes.
* **Webhook Notifications:** Sends available names to your Discord.
* **Auto-Claimer:** Attempts to snag names in your browser session.

---

## 🔍 How it works

### 📸 Instagram
- Needs an account token.
- Has a built-in cooldown so you don't get blocked.
- No proxies needed.

### 🎵 TikTok & Auto-Claimer
- No token or cookies needed just to check availability.
- **Auto-Claimer:** Emulates a browser session using your Chrome cookies.
- > ⚠️ **Note:** If a name shows available but you can't claim it, the account was likely recently deleted and you have to wait for the 30-day lock period.

### 💬 Discord
- Works with the new username system.
- Discord blocks you after 3-4 searches, so **proxies are recommended**. There's a no-proxy version but it's slow.

### 🤖 Roblox
- Features auto account creation (code from `qing762/roblox-auto-signup`).
- Checks availability and sends webhook alerts.

### 🐙 GitHub & 💨 Steam
- Works without any issues.

### 🎮 PSN (PlayStation)
- **Fixed:** Uses the actual PSN API now. Banned and private accounts are no longer an issue.

---

## 🛠 Setup

### 1. Requirements
* [Google Chrome](https://www.google.com/chrome/) installed.
* [Cookie Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) extension to get your session ID.

### 2. Install
```bash
pip install -r requirements.txt
python main.py
