# Universal Username Checker

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Discord](https://img.shields.io/badge/Discord-skiesfr-5865F2?style=for-the-badge&logo=discord&logoColor=white)

Most name checkers on GitHub are outdated and don't actually hit anymore. I built this project for fun because I wanted something that works with current APIs. AI helped me through the project to make sure the logic is solid and stays updated.

---

## Supported Platforms

| Platform | What it does | Token / Cookie needed |
|---|---|---|
| Discord | Checks new pomelo username availability. GUI with multi-token rotation, random name generator, and auto-saves hits. | Optional. Works without one but a token lets you check more before hitting limits. |
| Instagram | Checks username availability. | Yes, an account token is required. |
| TikTok | Checks username availability. | No. |
| TikTok Auto-Claimer | Automatically claims a username using a real browser session. | Yes, session cookies from Cookie Editor extension. |
| Roblox | Checks availability and supports auto account creation. | No. |
| GitHub | Checks username availability. | No. |
| Steam | Checks username availability. | No. |
| PlayStation | Checks username availability using the official PSN API. | Yes, a PSN NPSSO token is required. |
| Geometry Dash | Checks username availability. | No. |
| Minecraft | Checks username availability with rate control. | No. |

---

## Setup

1. Install Python from https://python.org (3.10 or higher recommended).
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run whichever script you want.
