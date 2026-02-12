# 🔍 Name checker & Auto-Claimer

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)
![Discord](https://img.shields.io/badge/Discord-skiesfr-5865F2?style=for-the-badge&logo=discord&logoColor=white)

Most name checkers on GitHub are straight garbage or haven't been updated since 2020. I built this because I wanted something that actually hits. **AI helped me through the project** to make sure the logic doesn't break when the APIs change.

---

## 📱 What it supports
| Platform | Icon | Platform | Icon |
| :--- | :---: | :--- | :---: |
| **Instagram** | 📸 | **TikTok** | 🎵 |
| **Discord** | 💬 | **Roblox** | 🤖 |
| **GitHub** | 🐙 | **Steam** | 💨 |
| **PlayStation** | 🎮 | **Webhooks** | 🔗 |

---

## ⚡ The Goodies
* **Fast as hell:** High-speed API pings so you don't miss out on drops.
* **Name Gen:** Random generator with custom prefixes for OG handles.
* **Webhooks:** Sends hits straight to your Discord so you can see them on your phone.
* **Auto-Claim:** Snags the names in a browser session the second they're free.

---

## 🔍 The Lowdown (Don't skip this)

### 📸 Instagram
- Needs an account token to work.
- Has a built-in cooldown so you don't get cooked by rate-limits.
- No proxies needed, the IG API is pretty chill.

### 🎵 TikTok & Claimer
- No token needed just to check if names are free.
- **Auto-Claimer:** Uses Chrome + Cookie Editor to move like a real user.
- > ⚠️ **FYI:** If a name looks available but won't claim, it’s probably a deleted account. You gotta wait for that 30-day lock to expire before it's actually snagable.

### 💬 Discord
- Supports the new username system.
- **Heads up:** Discord is strict. Their API will block you after 3-4 tries, so **use proxies** or it'll be slow as hell.

### 🤖 Roblox
- Has **Auto-Account Creation** (Shoutout to `qing762` for the signup logic).
- Full webhook and random gen support.

### 🐙 GitHub & 💨 Steam
- Works 100%. Good for hunting 3-letter IDs.

### 🎮 PSN (PlayStation)
- Sony's API is weird. Banned accounts might show as "Available" (False Positive). 
- Can't see private accounts, nothing I can do about that.

---

## 🛠 Setup

### 1. Browser Stuff (For Claiming)
* Get [Google Chrome](https://www.google.com/chrome/).
* Get [Cookie Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) to grab your session info.

### 2. Install
```bash
git clone [https://github.com/unfooled/Insta-tiktok-discord-name-checker-and-random-generator.git](https://github.com/unfooled/Insta-tiktok-discord-name-checker-and-random-generator.git)
pip install -r requirements.txt
python main.py
