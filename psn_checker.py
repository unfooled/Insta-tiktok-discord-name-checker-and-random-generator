import sys, random, string, traceback, time, json, requests
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QFont

# ---------------------------------------------------------------------------
# Lazy-import PSNAWP so the app can still launch and show the install error
# ---------------------------------------------------------------------------
try:
    from psnawp_api import PSNAWP
    from psnawp_api.models.user import User          # raised on bad online_id
    PSNAWP_AVAILABLE = True
except ImportError:
    PSNAWP_AVAILABLE = False


class Checker(QThread):
    update  = pyqtSignal(str)
    pupdate = pyqtSignal(int)
    count   = 0

    def __init__(self, usernames, npsso, webhook_url=None, debug=False):
        super().__init__()
        self.usernames   = usernames
        self.npsso       = npsso
        self.webhook_url = webhook_url
        self.running     = True
        self.debug       = debug
        self.psnawp      = None          # created once in run()

    # ------------------------------------------------------------------
    def run(self):
        # ---- 1.  Initialise PSNAWP (token exchange happens here) -----
        try:
            self.psnawp = PSNAWP(self.npsso)
            if self.debug:
                self.update.emit("[DEBUG] PSNAWP initialised – token exchange successful.")
        except Exception as e:
            self.update.emit(f"[AUTH ERROR] Failed to authenticate with PSN.\n"
                             f"  • Make sure your npsso token is fresh (< 24 h old).\n"
                             f"  • Detail: {e}")
            return                        # nothing more we can do

        # ---- 2.  Loop through usernames --------------------------------
        for username in self.usernames:
            if not self.running:
                break
            self.check_user(username)
            self.count += 1
            self.pupdate.emit(self.count)
            time.sleep(0.6)               # gentle rate-limit (PSN is strict)

    # ------------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------------
    def check_user(self, username):
        if not self.running:
            return
        try:
            # PSNAWP.user() does a real PSN lookup.
            # If the online_id does NOT exist it raises an exception
            # whose message contains "User not found" (or similar).
            user = self.psnawp.user(online_id=username)

            # If we reach here the account exists ──► TAKEN
            if self.debug:
                self.update.emit(f"[DEBUG] {username} → accountId: {user.account_id}")
            self.update.emit(f"[TAKEN] {username}")

        except Exception as e:
            err_text = str(e).lower()

            # ----------------------------------------------------------
            # PSN "not found" errors – username is genuinely available
            # ----------------------------------------------------------
            if any(phrase in err_text for phrase in
                   ("not found", "no such user", "does not exist",
                    "invalid online id", "user not found")):
                self.update.emit(f"[AVAILABLE] {username}")
                if self.webhook_url:
                    self.send_to_discord(username)

            # ----------------------------------------------------------
            # Rate-limited by Sony – back off and retry once
            # ----------------------------------------------------------
            elif "rate" in err_text or "429" in err_text or "too many" in err_text:
                self.update.emit(f"[RATE LIMIT] {username} – waiting 15 s …")
                time.sleep(15)
                self.check_user(username)   # single retry

            # ----------------------------------------------------------
            # Auth token expired mid-run
            # ----------------------------------------------------------
            elif "401" in err_text or "unauthori" in err_text or "token" in err_text:
                self.update.emit("[AUTH ERROR] Token expired – please get a fresh npsso and restart.")
                self.running = False

            # ----------------------------------------------------------
            # Anything else – log it
            # ----------------------------------------------------------
            else:
                if self.debug:
                    self.update.emit(f"[ERROR] {username}:\n{traceback.format_exc()}")
                else:
                    self.update.emit(f"[ERROR] {username}: {e}")

    # ------------------------------------------------------------------
    def send_to_discord(self, username):
        try:
            webhook_data = {
                "embeds": [{
                    "title": "🎮 Available PlayStation Username",
                    "description": f"**{username}** is available!",
                    "color": 0x00ff00,
                    "fields": [{"name": "Username", "value": f"`{username}`", "inline": True}],
                    "footer": {"text": "Claim it fast on PlayStation.com!"},
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')
                }]
            }
            response = requests.post(self.webhook_url, json=webhook_data, timeout=5)
            if self.debug and response.status_code == 204:
                self.update.emit("[DEBUG] Sent to Discord webhook.")
        except Exception as e:
            if self.debug:
                self.update.emit(f"[DEBUG] Webhook error: {e}")


# ======================================================================
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PlayStation Username Checker")
        self.setGeometry(150, 150, 1100, 870)
        self.thread = None
        self.initUI()

    # ------------------------------------------------------------------
    def initUI(self):
        wid = QWidget(self)
        self.setCentralWidget(wid)
        main_layout = QVBoxLayout()
        wid.setLayout(main_layout)

        # ── Title bar ─────────────────────────────────────────────────
        title = QLabel("PlayStation Username Checker")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("padding: 15px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                            " stop:0 #003087, stop:1 #0070cc); color: white; border-radius: 5px;")
        main_layout.addWidget(title)

        # ── PSNAWP install warning (shown only if missing) ───────────
        if not PSNAWP_AVAILABLE:
            warn = QLabel("⚠️  PSNAWP is not installed.  Run:   pip install PSNAWP   then restart this app.")
            warn.setWordWrap(True)
            warn.setStyleSheet("background-color: #f8d7da; padding: 10px; border-radius: 3px; color: #721c24;")
            main_layout.addWidget(warn)

        # ── About ─────────────────────────────────────────────────────
        info_group   = QGroupBox("About")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        info_layout  = QVBoxLayout()
        instruction  = QLabel(
            "✅ Check PlayStation username availability using the real PSN network.\n"
            "Requires a fresh npsso token (see instructions below).  "
            "Usernames: 3–16 characters (letters, numbers, hyphens, underscores).")
        instruction.setWordWrap(True)
        instruction.setStyleSheet("background-color: #d4edda; padding: 10px; border-radius: 3px; color: #155724;")
        info_layout.addWidget(instruction)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # ── npsso token input ─────────────────────────────────────────
        api_group  = QGroupBox("PSN Authentication (npsso token – Required)")
        api_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        api_layout = QVBoxLayout()

        api_info = QLabel(
            "🔑 How to get your npsso token:\n"
            "1. Open a browser and log in at https://my.playstation.com/\n"
            "2. In the SAME browser go to  https://ca.account.sony.com/api/v1/ssocookie\n"
            "3. Copy the 64-character value from the \"npsso\" field and paste it below.\n"
            "⚠️  The token expires after ~24 hours – refresh it if checks fail.")
        api_info.setWordWrap(True)
        api_info.setStyleSheet("background-color: #fff3cd; padding: 8px; border-radius: 3px; color: #856404;")
        api_layout.addWidget(api_info)

        api_input_layout = QHBoxLayout()
        api_input_layout.addWidget(QLabel("npsso:"))
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Paste your 64-character npsso token here")
        self.api_input.setEchoMode(QLineEdit.Password)
        api_input_layout.addWidget(self.api_input)
        api_layout.addLayout(api_input_layout)

        show_api_btn = QCheckBox("Show token")
        show_api_btn.stateChanged.connect(
            lambda state: self.api_input.setEchoMode(QLineEdit.Normal if state else QLineEdit.Password))
        api_layout.addWidget(show_api_btn)

        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)

        # ── Discord webhook ──────────────────────────────────────────
        webhook_group  = QGroupBox("Discord Webhook (Optional)")
        webhook_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        webhook_layout = QVBoxLayout()

        webhook_info = QLabel("Get notified when available usernames are found.")
        webhook_info.setWordWrap(True)
        webhook_info.setStyleSheet("background-color: #d1ecf1; padding: 8px; border-radius: 3px; color: #0c5460;")
        webhook_layout.addWidget(webhook_info)

        webhook_input_layout = QHBoxLayout()
        self.webhook_input = QLineEdit()
        self.webhook_input.setPlaceholderText("https://discord.com/api/webhooks/…")
        webhook_input_layout.addWidget(self.webhook_input)

        test_webhook_btn = QPushButton("Test")
        test_webhook_btn.setMaximumWidth(80)
        test_webhook_btn.clicked.connect(self.test_webhook)
        webhook_input_layout.addWidget(test_webhook_btn)

        webhook_layout.addLayout(webhook_input_layout)
        webhook_group.setLayout(webhook_layout)
        main_layout.addWidget(webhook_group)

        # ── Username generator ────────────────────────────────────────
        gen_group  = QGroupBox("Step 1: Generate Random Usernames (Optional)")
        gen_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        gen_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Length:"))
        self.length_input = QLineEdit("8")
        self.length_input.setMaximumWidth(60)
        row1.addWidget(self.length_input)
        row1.addWidget(QLabel("Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g., Pro_")
        row1.addWidget(self.prefix_input)
        row1.addWidget(QLabel("Suffix:"))
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g., _Gaming")
        row1.addWidget(self.suffix_input)
        gen_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Letters only", "Letters + Numbers", "Numbers + Letters",
            "Numbers only", "Letters_Letters", "CamelCase"
        ])
        row2.addWidget(self.pattern_combo)
        row2.addWidget(QLabel("Count:"))
        self.count_input = QLineEdit("20")
        self.count_input.setMaximumWidth(60)
        row2.addWidget(self.count_input)

        gen_btn = QPushButton("Generate")
        gen_btn.clicked.connect(self.generate_usernames)
        gen_btn.setStyleSheet("background-color: #0070cc; color: white; padding: 8px; font-weight: bold;")
        row2.addWidget(gen_btn)
        gen_layout.addLayout(row2)

        gen_group.setLayout(gen_layout)
        main_layout.addWidget(gen_group)

        # ── Username input ────────────────────────────────────────────
        input_group  = QGroupBox("Step 2: Enter Usernames to Check")
        input_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        input_layout = QVBoxLayout()
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter usernames (one per line)")
        self.input_text.setMaximumHeight(120)
        input_layout.addWidget(self.input_text)
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # ── Results ───────────────────────────────────────────────────
        output_group  = QGroupBox("Results")
        output_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Results will appear here")
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # ── Buttons ───────────────────────────────────────────────────
        btn_layout = QHBoxLayout()

        self.start_button = QPushButton("START CHECKING")
        self.start_button.clicked.connect(self.start_clicked)
        self.start_button.setStyleSheet("background-color: #003087; color: white; font-weight: bold;"
                                        " padding: 15px; font-size: 14px;")
        btn_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("STOP")
        self.stop_button.clicked.connect(self.stop_clicked)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #ff4444; color: white;"
                                       " font-weight: bold; padding: 15px; font-size: 14px;")
        btn_layout.addWidget(self.stop_button)

        self.clear_button = QPushButton("Clear Results")
        self.clear_button.clicked.connect(lambda: self.output_text.clear())
        self.clear_button.setStyleSheet("padding: 15px;")
        btn_layout.addWidget(self.clear_button)
        main_layout.addLayout(btn_layout)

        # ── Progress ──────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; height: 25px; }"
                                        " QProgressBar::chunk { background-color: #003087; }")
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready – paste your npsso token to begin.")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold;"
                                        " background-color: #e0e0e0; border-radius: 3px;")
        main_layout.addWidget(self.status_label)

        self.debug_checkbox = QCheckBox("Debug mode (shows detailed info)")
        main_layout.addWidget(self.debug_checkbox)

    # ------------------------------------------------------------------
    # Username generator  (unchanged logic)
    # ------------------------------------------------------------------
    def generate_usernames(self):
        try:
            length = int(self.length_input.text())
        except ValueError:
            length = 8
        length = max(3, min(16, length))

        prefix  = self.prefix_input.text().strip()
        suffix  = self.suffix_input.text().strip()
        pattern = self.pattern_combo.currentText()

        try:
            count = int(self.count_input.text())
        except ValueError:
            count = 20

        generated = []
        for _ in range(count):
            if pattern == "Letters only":
                username = "".join(random.choice(string.ascii_lowercase) for _ in range(length))
            elif pattern == "Letters + Numbers":
                chars    = string.ascii_lowercase + string.digits
                username = "".join(random.choice(chars) for _ in range(length))
            elif pattern == "Numbers + Letters":
                num_count   = random.randint(1, max(1, length - 2))
                letter_count = length - num_count
                username = ("".join(random.choice(string.digits)          for _ in range(num_count))
                          + "".join(random.choice(string.ascii_lowercase) for _ in range(letter_count)))
            elif pattern == "Numbers only":
                username = "".join(random.choice(string.digits) for _ in range(length))
            elif pattern == "Letters_Letters":
                p1 = length // 2
                p2 = length - p1
                username = ("".join(random.choice(string.ascii_lowercase) for _ in range(p1))
                          + "_"
                          + "".join(random.choice(string.ascii_lowercase) for _ in range(p2)))
            elif pattern == "CamelCase":
                parts, remaining = [], length
                while remaining > 0:
                    pl   = random.randint(2, min(4, remaining))
                    part = "".join(random.choice(string.ascii_lowercase) for _ in range(pl))
                    parts.append(part.capitalize())
                    remaining -= pl
                username = "".join(parts)
            else:
                username = "".join(random.choice(string.ascii_lowercase) for _ in range(length))

            username = prefix + username + suffix
            username = ''.join(c for c in username if c.isalnum() or c in '_-')
            if 3 <= len(username) <= 16:
                generated.append(username)

        existing = self.input_text.toPlainText().strip()
        combined = "\n".join(generated) if not existing else existing + "\n" + "\n".join(generated)
        self.input_text.setText(combined)

        self.status_label.setText(f"Generated {len(generated)} usernames")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold;"
                                        " background-color: #c8e6c9; border-radius: 3px;")

    # ------------------------------------------------------------------
    def test_webhook(self):
        webhook_url = self.webhook_input.text().strip()
        if not webhook_url:
            QMessageBox.warning(self, "No Webhook", "Please enter a webhook URL first.")
            return
        try:
            test_data = {"embeds": [{"title": "🎮 Test Message",
                                     "description": "Webhook is working correctly!",
                                     "color": 0x00ff00}]}
            response = requests.post(webhook_url, json=test_data, timeout=5)
            if response.status_code == 204:
                QMessageBox.information(self, "Success", "✅ Webhook test successful!")
            else:
                QMessageBox.warning(self, "Failed", f"❌ Webhook failed: HTTP {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Failed: {e}")

    # ------------------------------------------------------------------
    def start_clicked(self):
        if not PSNAWP_AVAILABLE:
            QMessageBox.critical(self, "Missing dependency",
                                 "PSNAWP is not installed.\n\nOpen a terminal and run:\n\n"
                                 "    pip install PSNAWP\n\nthen restart this app.")
            return

        usernames = self.get_usernames()
        if not usernames:
            QMessageBox.warning(self, "No Usernames", "Please enter or generate usernames to check.")
            return

        npsso = self.api_input.text().strip()
        if not npsso:
            QMessageBox.warning(self, "No npsso token",
                                "You need a fresh npsso token to authenticate with PSN.\n\n"
                                "Follow the instructions in the \"PSN Authentication\" box above.")
            return

        if len(npsso) != 64:
            QMessageBox.warning(self, "Invalid npsso",
                                f"npsso tokens are exactly 64 characters.  "
                                f"Yours is {len(npsso)} – please double-check it.")
            return

        debug        = self.debug_checkbox.isChecked()
        webhook_url  = self.webhook_input.text().strip() or None

        self.progress_bar.setMaximum(len(usernames))
        self.progress_bar.setValue(0)
        self.output_text.clear()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self.status_label.setText(f"Authenticating & checking {len(usernames)} usernames …")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold;"
                                        " background-color: #fff9c4; border-radius: 3px;")

        self.thread = Checker(usernames, npsso, webhook_url, debug)
        self.thread.update.connect(self.update_text)
        self.thread.pupdate.connect(self.update_progress)
        self.thread.finished.connect(self.checking_finished)
        self.thread.start()

    # ------------------------------------------------------------------
    def stop_clicked(self):
        if self.thread:
            self.thread.stop()
            self.thread.quit()
            self.thread.wait(2000)
        self.checking_finished()

    def checking_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Complete")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold;"
                                        " background-color: #c8e6c9; border-radius: 3px;")

    def update_text(self, text):
        self.output_text.append(text)
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        self.output_text.setTextCursor(cursor)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        total   = self.progress_bar.maximum()
        percent = int((value / total) * 100) if total > 0 else 0
        self.status_label.setText(f"Progress: {value}/{total} ({percent}%)")

    # ------------------------------------------------------------------
    def get_usernames(self):
        txt       = self.input_text.toPlainText().strip()
        usernames = []
        for line in txt.splitlines():
            u = line.strip()
            if u and 3 <= len(u) <= 16:
                clean = ''.join(c for c in u if c.isalnum() or c in '_-')
                if clean:
                    usernames.append(clean)
        return usernames


# ======================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w   = App()
    w.show()
    sys.exit(app.exec_())
