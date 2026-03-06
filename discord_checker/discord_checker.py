import sys
import os
import re
import json
import random
import string
import asyncio
import aiohttp
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QGroupBox, QRadioButton,
    QComboBox, QCheckBox, QProgressBar, QFileDialog, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

VERSION = "V3.0 - Unauthed + Async"

UNAUTHED_URL  = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
AUTHED_URL    = "https://discord.com/api/v9/users/@me/pomelo-attempt"
LEGACY_URL    = "https://discord.com/api/v9/users/@me"
USER_INFO_URL = "https://discord.com/api/v9/users/@me"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
X_SUPER = (
    "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6"
    "ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2lu"
    "NjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAu"
    "MCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEw"
    "IiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJl"
    "ZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9i"
    "dWlsZF9udW1iZXIiOjI1MDcxMCwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="
)

DIR_PATH       = os.path.dirname(os.path.realpath(__file__))
TOKENS_FILE    = os.path.join(DIR_PATH, "tokens.txt")
AVAILABLE_FILE = os.path.join(DIR_PATH, "available_usernames.txt")
USERNAMES_FILE = os.path.join(DIR_PATH, "usernames.txt")


def load_tokens_from_file():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    return []


def save_available(username):
    with open(AVAILABLE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{username}\n")


# ---------------------------------------------------------------------------
# Checker thread
# ---------------------------------------------------------------------------
class Checker(QThread):
    update  = pyqtSignal(str)
    pupdate = pyqtSignal(int)

    POMELO_URL = "https://discord.com/api/v9/users/@me/pomelo-attempt"

    def __init__(self, usernames, tokens, check_mode="pomelo", proxies=None, debug=False):
        super().__init__()
        self.usernames   = usernames
        self.tokens      = tokens if isinstance(tokens, list) else ([tokens] if tokens else [])
        self.token_index = 0
        self.check_mode  = check_mode
        self.proxies     = proxies or []
        self.proxy_index = 0
        self.running     = True
        self.debug       = debug
        self.consecutive_errors      = 0
        self.max_errors_before_pause = 3
        self.count           = 0
        self.available_count = 0
        self.taken_count     = 0
        self.error_count     = 0
        self.rate_limit_until = {}

    @property
    def token(self):
        return self.tokens[self.token_index] if self.tokens else ""

    def next_token(self):
        """Rotate to next free token, wraps back to first."""
        if not self.tokens:
            return
        import time
        now = time.time()
        for _ in range(len(self.tokens)):
            self.token_index = (self.token_index + 1) % len(self.tokens)
            if self.rate_limit_until.get(self.token_index, 0) <= now:
                self.update.emit(f"[TOKEN] Switched to token {self.token_index + 1}/{len(self.tokens)}")
                return
        # All rate limited - pick soonest
        best = min(range(len(self.tokens)), key=lambda i: self.rate_limit_until.get(i, 0))
        self.token_index = best
        wait = max(0, self.rate_limit_until.get(best, 0) - now)
        self.update.emit(f"[TOKEN] All tokens rate limited. Token {self.token_index + 1} ready in {wait:.2f}s")

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.main())
        finally:
            loop.close()

    def stop(self):
        self.running = False

    def get_next_proxy(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

    async def check_pomelo_username(self, username, session, proxy=None):
        try:
            payload = {"username": username}

            if self.debug and proxy:
                self.update.emit(f"[DEBUG] Using proxy: {proxy}")

            # Retry loop - same as friend's script
            while True:
                req_headers = {"Authorization": self.token} if self.token else {}
                async with session.post(self.POMELO_URL, json=payload, proxy=proxy, timeout=15, headers=req_headers) as resp:
                    status = resp.status

                    if self.debug:
                        self.update.emit(f"\n{'='*60}")
                        self.update.emit(f"[DEBUG] Checking: {username}")
                        self.update.emit(f"[DEBUG] Status Code: {status}")

                    if status in (200, 201):
                        data = await resp.json()

                        if self.debug:
                            self.update.emit(f"[DEBUG] Response: {json.dumps(data, indent=2)}")

                        if "taken" in data:
                            taken = data["taken"]
                            if not taken:
                                self.available_count += 1
                                self.update.emit(f"[AVAILABLE] '{username}'  [Stats: {self.available_count} available / {self.taken_count + self.available_count} checked]")
                                save_available(username)
                            else:
                                self.taken_count += 1
                                self.update.emit(f"[TAKEN] '{username}'  [Stats: {self.available_count} available / {self.taken_count + self.available_count} checked]")
                            return not taken
                        else:
                            self.update.emit(f"[UNCERTAIN] '{username}' - Unexpected response")
                            return None

                    elif status == 429:
                        import time
                        # Get retry_after from JSON body (same as friend's script)
                        try:
                            data = await resp.json()
                            retry_after = data.get("retry_after", 5.0)
                        except Exception:
                            retry_after = 5.0
                        self.rate_limit_until[self.token_index] = time.time() + retry_after
                        self.update.emit(f"[RATE LIMIT] token {self.token_index + 1} limited for {retry_after:.2f}s")
                        # Switch token and retry immediately - no sleep if new token is free
                        self.next_token()
                        wait = max(0, self.rate_limit_until.get(self.token_index, 0) - time.time())
                        if wait > 1:
                            self.update.emit(f"[WAIT] All tokens busy, waiting {wait:.2f}s...")
                            await asyncio.sleep(wait + 1)
                        continue  # retry same username with new token

                    elif status == 401:
                        self.update.emit(f"[AUTH ERROR] Invalid token {self.token_index + 1}, switching...")
                        self.next_token()
                        continue

                    else:
                        self.update.emit(f"[UNCERTAIN] '{username}' - Status {status}")
                        return None

        except Exception as e:
            self.update.emit(f"[ERROR] '{username}': {str(e)[:80]}")
            return None

    async def check_user(self, username, sem, session, lock, idx):
        if not self.running:
            return
        async with sem:
            proxy = self.get_next_proxy()
            try:
                result = await self.check_pomelo_username(username, session, proxy)

                if result is None:
                    self.error_count += 1
                    self.consecutive_errors += 1
                    await self.check_for_cooldown()
                else:
                    self.consecutive_errors = 0

            except aiohttp.ClientProxyConnectionError:
                self.update.emit(f"[PROXY ERROR] {username}: Could not connect via proxy")
                self.consecutive_errors += 1
                self.error_count += 1
            except asyncio.TimeoutError:
                self.consecutive_errors += 1
                self.error_count += 1
                self.update.emit(f"[TIMEOUT] {username}")
                await self.check_for_cooldown()
            except Exception as e:
                self.consecutive_errors += 1
                self.error_count += 1
                self.update.emit(f"[ERROR] {username}: {str(e)[:80]}")
                await self.check_for_cooldown()
            finally:
                async with lock:
                    self.count += 1
                self.pupdate.emit(self.count)

    async def check_for_cooldown(self):
        if self.consecutive_errors >= self.max_errors_before_pause:
            await self.cooldown(15, f"{self.consecutive_errors} errors in a row")
            self.consecutive_errors = 0

    async def cooldown(self, duration, reason):
        self.update.emit(f"\nCOOLDOWN: {reason}!")
        self.update.emit(f"Waiting {duration}s...")
        for remaining in range(duration, 0, -1):
            if not self.running:
                break
            # Only print every 60s for long waits, every 5s for short ones
            interval = 60 if duration > 60 else 5
            if remaining % interval == 0 or remaining <= 5:
                self.update.emit(f"Resuming in {remaining}s...")
            await asyncio.sleep(1)
        self.update.emit("Cooldown complete! Continuing...\n")

    async def main(self):
        concurrent_limit = len(self.proxies) if self.proxies else 1
        concurrent_limit = min(concurrent_limit, 5)
        sem  = asyncio.Semaphore(concurrent_limit)
        lock = asyncio.Lock()

        if self.proxies:
            self.update.emit(f"Using {len(self.proxies)} proxies with {concurrent_limit} concurrent requests\n")
        else:
            self.update.emit(f"No proxies loaded - using direct connection\n")

        # Match friend's headers exactly - minimal, no X-Super-Properties
        headers = {
            "Content-Type":  "application/json",
            "Origin":        "https://discord.com",
            "Referer":       "https://discord.com/",
            "User-Agent":    USER_AGENT,
        }

        connector = aiohttp.TCPConnector(limit=concurrent_limit, ssl=True)
        timeout   = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout) as session:
            for i, username in enumerate(self.usernames):
                if not self.running:
                    break
                await self.check_user(username, sem, session, lock, i)
                # Random delay matching friend's script: base ±30%, min 0.5s
                base = 1.0 if self.proxies else 2.5
                variation = base * 0.3
                import random as _r
                delay = max(0.5, base + _r.uniform(-variation, variation))
                await asyncio.sleep(delay)

        total = self.available_count + self.taken_count + self.error_count
        self.update.emit(f"\n{'-'*50}")
        self.update.emit(f"Available : {self.available_count}")
        self.update.emit(f"Taken     : {self.taken_count}")
        self.update.emit(f"Errors    : {self.error_count}")
        self.update.emit(f"Total     : {total}")
        if self.available_count:
            self.update.emit(f"Saved {self.available_count} username(s) to available_usernames.txt")
        self.update.emit(f"{'-'*50}\n")

# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Discord Username Checker  {VERSION}")
        self.setGeometry(150, 150, 1150, 870)
        self.setMinimumSize(900, 700)
        self.thread = None
        self.initUI()
        self._try_load_tokens_file()

    def _try_load_tokens_file(self):
        tokens = load_tokens_from_file()
        if tokens:
            self.token_input.setText("\n".join(tokens))
            self.token_count_lbl.setText(f"Tokens loaded: {len(tokens)}")
            self.set_status(f"Loaded {len(tokens)} token(s) from tokens.txt", "green")

    def initUI(self):
        wid  = QWidget(self)
        self.setCentralWidget(wid)
        root = QVBoxLayout()
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)
        wid.setLayout(root)

        # Title
        title = QLabel(f"Discord Username Checker  {VERSION}")
        tf = QFont()
        tf.setPointSize(15)
        tf.setBold(True)
        title.setFont(tf)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "padding: 12px;"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #5865F2,stop:1 #7289DA);"
            "color: white; border-radius: 6px;"
        )
        root.addWidget(title)

        # Token
        tok_grp = QGroupBox("Step 1: Discord Token  (optional)")
        tok_grp.setStyleSheet("QGroupBox { font-weight: bold; }")
        tok_lay = QVBoxLayout()

        info = QLabel(
            "Leave blank to use the faster unauthed endpoint (no token needed).\n"
            "Add tokens to use the authed endpoint. Also supports tokens.txt (one per line)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background: #fff3cd; padding: 8px; border-radius: 4px; color: #856404;")
        tok_lay.addWidget(info)

        tok_row = QHBoxLayout()
        self.token_input = QTextEdit()
        self.token_input.setPlaceholderText("Paste tokens here, one per line...")
        self.token_input.setMaximumHeight(90)
        tok_row.addWidget(self.token_input)

        tok_btns = QVBoxLayout()
        load_tok_btn = QPushButton("Load tokens.txt")
        load_tok_btn.clicked.connect(self.load_token_from_file)
        tok_btns.addWidget(load_tok_btn)
        clr_tok_btn = QPushButton("Clear")
        clr_tok_btn.clicked.connect(lambda: self.token_input.clear())
        tok_btns.addWidget(clr_tok_btn)
        tok_btns.addStretch()
        tok_row.addLayout(tok_btns)

        tok_lay.addLayout(tok_row)
        self.token_count_lbl = QLabel("Tokens loaded: 0")
        self.token_count_lbl.setStyleSheet("font-style: italic; color: #555;")
        tok_lay.addWidget(self.token_count_lbl)
        tok_grp.setLayout(tok_lay)
        root.addWidget(tok_grp)

        # Proxies
        prx_grp = QGroupBox("Step 2: Proxies  (optional)")
        prx_grp.setStyleSheet("QGroupBox { font-weight: bold; }")
        prx_lay = QVBoxLayout()

        prx_info = QLabel(
            "Format: http://ip:port  or  http://user:pass@ip:port  or  socks5://ip:port  (one per line)"
        )
        prx_info.setWordWrap(True)
        prx_info.setStyleSheet("background: #d1ecf1; padding: 6px; border-radius: 4px; color: #0c5460;")
        prx_lay.addWidget(prx_info)

        prx_row = QHBoxLayout()
        self.proxy_input = QTextEdit()
        self.proxy_input.setPlaceholderText(
            "http://proxy1.com:8080\nhttp://user:pass@proxy2.com:8080\nsocks5://proxy3.com:1080"
        )
        self.proxy_input.setMaximumHeight(80)
        prx_row.addWidget(self.proxy_input)

        prx_btns = QVBoxLayout()
        load_prx_btn = QPushButton("Load File")
        load_prx_btn.clicked.connect(self.load_proxies_from_file)
        prx_btns.addWidget(load_prx_btn)
        clr_prx_btn = QPushButton("Clear")
        clr_prx_btn.clicked.connect(lambda: self.proxy_input.clear())
        prx_btns.addWidget(clr_prx_btn)
        prx_btns.addStretch()
        prx_row.addLayout(prx_btns)
        prx_lay.addLayout(prx_row)

        self.proxy_count_lbl = QLabel("Proxies loaded: 0")
        self.proxy_count_lbl.setStyleSheet("font-style: italic; color: #555;")
        prx_lay.addWidget(self.proxy_count_lbl)
        prx_grp.setLayout(prx_lay)
        root.addWidget(prx_grp)

        # Generator
        gen_grp = QGroupBox("Step 3: Generate Random Usernames  (optional)")
        gen_grp.setStyleSheet("QGroupBox { font-weight: bold; }")
        gen_lay = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Length:"))
        self.len_input = QLineEdit("5")
        self.len_input.setMaximumWidth(55)
        row1.addWidget(self.len_input)
        row1.addWidget(QLabel("Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g. og")
        self.prefix_input.setMaximumWidth(90)
        row1.addWidget(self.prefix_input)
        row1.addWidget(QLabel("Suffix:"))
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g. _xd")
        self.suffix_input.setMaximumWidth(90)
        row1.addWidget(self.suffix_input)
        row1.addWidget(QLabel("Count:"))
        self.count_input = QLineEdit("20")
        self.count_input.setMaximumWidth(55)
        row1.addWidget(self.count_input)
        row1.addStretch()
        gen_lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Letters only  (abc)",
            "Letters + Numbers  (a1b2)",
            "Numbers + Letters  (12ab)",
            "Letters_Letters  (ab_cd)",
            "CamelCase  (AbcDef)",
            "4-char OG style  (gc9_)",
        ])
        self.pattern_combo.setMinimumWidth(220)
        row2.addWidget(self.pattern_combo)

        gen_btn = QPushButton("Generate")
        gen_btn.clicked.connect(self.generate_usernames)
        gen_btn.setStyleSheet(
            "background: #2196F3; color: white; padding: 7px 14px; font-weight: bold; border-radius: 4px;"
        )
        row2.addWidget(gen_btn)

        self.debug_chk = QCheckBox("Debug mode")
        self.debug_chk.setToolTip("Show detailed API responses in the log")
        row2.addWidget(self.debug_chk)
        row2.addStretch()
        gen_lay.addLayout(row2)
        gen_grp.setLayout(gen_lay)
        root.addWidget(gen_grp)

        # Input / Output
        io_grp = QGroupBox("Step 4: Check Usernames")
        io_grp.setStyleSheet("QGroupBox { font-weight: bold; }")
        io_lay = QHBoxLayout()

        in_box = QVBoxLayout()
        in_lbl = QLabel("Usernames to check:")
        in_lbl.setStyleSheet("font-weight: bold;")
        in_box.addWidget(in_lbl)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(
            "Enter usernames here (one per line)\n\nPomelo:  username\nLegacy:  username#1234"
        )
        in_box.addWidget(self.input_text)

        in_file_row = QHBoxLayout()
        load_list_btn = QPushButton("Load usernames.txt")
        load_list_btn.clicked.connect(self.load_usernames_file)
        in_file_row.addWidget(load_list_btn)
        clr_in_btn = QPushButton("Clear")
        clr_in_btn.clicked.connect(lambda: self.input_text.clear())
        in_file_row.addWidget(clr_in_btn)
        in_file_row.addStretch()
        in_box.addLayout(in_file_row)

        out_box = QVBoxLayout()
        out_lbl = QLabel("Results:")
        out_lbl.setStyleSheet("font-weight: bold;")
        out_box.addWidget(out_lbl)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet(
            "background: #1e1e2e; color: #cdd6f4;"
            "font-family: Consolas, Monaco, monospace; font-size: 12px; padding: 8px;"
        )
        out_box.addWidget(self.output_text)

        save_row = QHBoxLayout()
        save_btn = QPushButton("Save results")
        save_btn.clicked.connect(self.save_results)
        save_row.addWidget(save_btn)
        clr_out_btn = QPushButton("Clear log")
        clr_out_btn.clicked.connect(lambda: self.output_text.clear())
        save_row.addWidget(clr_out_btn)
        save_row.addStretch()
        out_box.addLayout(save_row)

        io_lay.addLayout(in_box)
        io_lay.addLayout(out_box)
        io_grp.setLayout(io_lay)
        root.addWidget(io_grp)

        # Controls
        ctrl = QHBoxLayout()

        self.start_btn = QPushButton("START CHECKING")
        self.start_btn.clicked.connect(self.start_clicked)
        self.start_btn.setStyleSheet(
            "background: #4CAF50; color: white; font-weight: bold;"
            "padding: 14px; font-size: 13px; border-radius: 5px;"
        )
        ctrl.addWidget(self.start_btn)

        self.stop_btn = QPushButton("STOP")
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "background: #f44336; color: white; font-weight: bold;"
            "padding: 14px; font-size: 13px; border-radius: 5px;"
        )
        ctrl.addWidget(self.stop_btn)

        root.addLayout(ctrl)

        # Progress + Status
        self.progress = QProgressBar()
        self.progress.setStyleSheet(
            "QProgressBar { text-align: center; height: 22px; border-radius: 4px; }"
            "QProgressBar::chunk { background: #5865F2; border-radius: 4px; }"
        )
        root.addWidget(self.progress)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(
            "padding: 7px; font-weight: bold; background: #e0e0e0; border-radius: 4px;"
        )
        root.addWidget(self.status_lbl)

    def set_status(self, msg, color="gray"):
        colors = {"green": "#c8e6c9", "red": "#ffcdd2", "yellow": "#fff9c4", "gray": "#e0e0e0"}
        bg = colors.get(color, "#e0e0e0")
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(
            f"padding: 7px; font-weight: bold; background: {bg}; border-radius: 4px;"
        )

    def get_tokens(self):
        txt = self.token_input.toPlainText().strip()
        if not txt:
            return []
        tokens = [l.strip() for l in txt.splitlines() if l.strip()]
        self.token_count_lbl.setText(f"Tokens loaded: {len(tokens)}")
        return tokens

    def load_token_from_file(self):
        tokens = load_tokens_from_file()
        if tokens:
            self.token_input.setText("\n".join(tokens))
            self.token_count_lbl.setText(f"Tokens loaded: {len(tokens)}")
            self.set_status(f"Loaded {len(tokens)} token(s) from tokens.txt", "green")
        else:
            QMessageBox.information(
                self, "tokens.txt",
                "tokens.txt is empty or not found.\n"
                "Create it next to this script with one token per line."
            )

    def load_proxies_from_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Load Proxy List", "", "Text Files (*.txt);;All (*)")
        if fname:
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    content = f.read()
                self.proxy_input.setText(content)
                cnt = len([l for l in content.splitlines() if l.strip()])
                self.proxy_count_lbl.setText(f"Proxies loaded: {cnt}")
                self.set_status(f"{cnt} proxies loaded", "green")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def load_usernames_file(self):
        path = USERNAMES_FILE if os.path.exists(USERNAMES_FILE) else None
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Load Username List", "", "Text Files (*.txt);;All (*)"
            )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.input_text.setText(content)
                cnt = len([l for l in content.splitlines() if l.strip()])
                self.set_status(f"Loaded {cnt} usernames", "green")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def get_proxies(self):
        txt = self.proxy_input.toPlainText().strip()
        if not txt:
            return []
        proxies = [
            l.strip() for l in txt.splitlines()
            if l.strip() and any(
                l.strip().startswith(p) for p in ("http://", "https://", "socks5://")
            )
        ]
        self.proxy_count_lbl.setText(f"Proxies loaded: {len(proxies)}")
        return proxies

    def get_usernames(self):
        return [l.strip() for l in self.input_text.toPlainText().splitlines() if l.strip()]

    def save_results(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "results.txt", "Text Files (*.txt);;All (*)"
        )
        if fname:
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(self.output_text.toPlainText())
                self.set_status(f"Saved to {fname}", "green")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def generate_usernames(self):
        try:
            length = int(self.len_input.text())
        except Exception:
            length = 5
        try:
            count = int(self.count_input.text())
        except Exception:
            count = 20

        prefix  = self.prefix_input.text().strip()
        suffix  = self.suffix_input.text().strip()
        pattern = self.pattern_combo.currentIndex()

        L  = string.ascii_lowercase
        D  = string.digits
        LD = L + D

        generated = []
        seen      = set()
        attempts  = 0
        while len(generated) < count and attempts < count * 15:
            attempts += 1
            if pattern == 0:
                core = "".join(random.choice(L) for _ in range(length))
            elif pattern == 1:
                core = "".join(random.choice(LD) for _ in range(length))
            elif pattern == 2:
                n    = random.randint(1, max(1, length - 1))
                core = "".join(random.choice(D) for _ in range(n)) + \
                       "".join(random.choice(L) for _ in range(length - n))
            elif pattern == 3:
                h    = length // 2
                core = "".join(random.choice(L) for _ in range(h)) + "_" + \
                       "".join(random.choice(L) for _ in range(length - h))
            elif pattern == 4:
                parts, rem = [], length
                while rem > 0:
                    pl = random.randint(2, min(4, rem))
                    parts.append(
                        "".join(random.choice(L) for _ in range(pl)).capitalize()
                    )
                    rem -= pl
                core = "".join(parts)
            elif pattern == 5:
                base = "".join(random.choice(LD) for _ in range(3))
                p    = random.choice("_.")
                pos  = random.choice(["end", "start", "mid1", "mid2"])
                if pos == "end":
                    core = base + p
                elif pos == "start":
                    core = p + base
                elif pos == "mid1":
                    core = base[:2] + p + base[2:]
                else:
                    core = base[:1] + p + base[1:]
            else:
                core = "".join(random.choice(LD) for _ in range(length))

            u = prefix + core + suffix
            u = re.sub(r'[^a-zA-Z0-9_.]', '', u)
            u = re.sub(r'\.\.+', '.', u)
            u = re.sub(r'__+', '_', u)
            u = u.strip('._')
            if u and u not in seen and 2 <= len(u) <= 32:
                seen.add(u)
                generated.append(u)

        existing = self.input_text.toPlainText().strip()
        new_text = "\n".join(generated)
        self.input_text.setText((existing + "\n" + new_text) if existing else new_text)
        self.set_status(f"Generated {len(generated)} usernames", "green")

    def start_clicked(self):
        tokens = self.get_tokens()

        usernames = self.get_usernames()
        if not usernames:
            QMessageBox.warning(self, "No usernames", "Enter or generate some usernames first!")
            return

        proxies = self.get_proxies()
        debug   = self.debug_chk.isChecked()

        self.progress.setMaximum(len(usernames))
        self.progress.setValue(0)
        self.output_text.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        proxy_note = f" with {len(proxies)} proxies" if proxies else ""
        token_note = f"authed ({len(tokens)} token(s))" if tokens else "unauthed (no token)"
        self.set_status(
            f"Checking {len(usernames)} usernames{proxy_note}  [{token_note}]...", "yellow"
        )

        self.thread = Checker(usernames, tokens, "pomelo", proxies, debug)
        self.thread.update.connect(self.on_update)
        self.thread.pupdate.connect(self.on_progress)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def stop_clicked(self):
        if self.thread:
            self.thread.stop()
            self.thread.quit()
            self.thread.wait(3000)
        self.on_finished()

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.set_status("Done!", "green")

    def on_update(self, text):
        self.output_text.append(text)
        c = self.output_text.textCursor()
        c.movePosition(c.End)
        self.output_text.setTextCursor(c)

    def on_progress(self, value):
        self.progress.setValue(value)
        total   = self.progress.maximum()
        percent = int((value / total) * 100) if total else 0
        self.set_status(f"Progress: {value}/{total}  ({percent}%)", "yellow")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = App()
    w.show()
    sys.exit(app.exec_())
