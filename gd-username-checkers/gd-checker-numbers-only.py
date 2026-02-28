import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QFont
import requests

# ------------------- Checker Thread ------------------- #
class AccountChecker(QThread):
    update = pyqtSignal(str)
    pupdate = pyqtSignal(int)

    def __init__(self, current_username, cookie, usernames_to_check):
        super().__init__()
        self.current_username = current_username
        self.cookie = cookie
        self.usernames_to_check = usernames_to_check
        self.running = True
        self.count = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.boomlings.com/database/accounts/changeusername.php"
        })
        # Inject the cookie directly into the session
        # Accept either raw value or full name=value format
        cookie = cookie.strip()
        if "=" not in cookie:
            cookie = "PHPSESSID=" + cookie
        for part in cookie.split(";"):
            part = part.strip()
            if "=" in part:
                name, _, value = part.partition("=")
                self.session.cookies.set(name.strip(), value.strip(), domain="www.boomlings.com")

    def stop(self):
        self.running = False

    def log(self, msg):
        self.update.emit(msg)

    def verify_session(self):
        """Check if the cookie is valid by loading the account page and looking for our username."""
        self.log("Verifying session cookie...")
        try:
            resp = self.session.get(
                "https://www.boomlings.com/database/accounts/accountManagement.php",
                timeout=10
            )
            self.log(f"[DEBUG] Session check status: {resp.status_code}")
            self.log(f"[DEBUG] Response snippet: {resp.text[:400]}")

            if f"welcome {self.current_username.lower()}" in resp.text.lower():
                self.log("Session valid! Logged in as: " + self.current_username)
                return True
            else:
                self.log("Session invalid or expired. Please get a fresh cookie.")
                return False
        except Exception as e:
            self.log(f"Session check error: {str(e)}")
            return False

    def try_change_username(self, new_username):
        """
        Try to change username to new_username.
        Returns: 'available', 'taken', 'unknown', 'session_expired', 'error'
        """
        try:
            resp = self.session.post(
                "https://www.boomlings.com/database/accounts/changeusername.php",
                data={
                    "username": self.current_username,
                    "newusername": new_username,
                    "changeusername": "Change Username"
                },
                timeout=10
            )

            self.log(f"[DEBUG] Change attempt '{new_username}' -> Status: {resp.status_code}")
            self.log(f"[DEBUG] Full response: {resp.text}")

            self._last_response = resp.text
            text = resp.text.lower()

            if "already taken" in text or "please try again" in text:
                return "taken"
            elif "username changed" in text or "success" in text or "already been changed" in text:
                return "available"  # Actually changed — revert immediately!
            elif "please login" in text:
                return "session_expired"
            else:
                return "unknown"

        except Exception as e:
            self.log(f"Error: {str(e)}")
            return "error"

    def revert_username(self):
        """Change back to the original username."""
        self.log(f"Reverting back to: {self.current_username}...")
        try:
            resp = self.session.post(
                "https://www.boomlings.com/database/accounts/changeusername.php",
                data={
                    "username": self.current_username,
                    "newusername": self.current_username,
                    "changeusername": "Change Username"
                },
                timeout=10
            )
            if "success" in resp.text.lower() or "changed" in resp.text.lower():
                self.log(f"Reverted back to: {self.current_username}")
            else:
                self.log(f"REVERT MAY HAVE FAILED — check your account manually at boomlings.com!")
        except Exception as e:
            self.log(f"REVERT FAILED: {str(e)} — Check your account manually!")

    def run(self):
        if not self.verify_session():
            self.update.emit("Could not verify session. Get a fresh cookie and try again.")
            return

        for username in self.usernames_to_check:
            if not self.running:
                break

            self.log(f"\n{'='*50}")
            self.log(f"Checking: {username}")

            if username.lower() == self.current_username.lower():
                self.log(f"[SKIPPED] {username} — same as your current username, skipping to save token!")
                self.count += 1
                self.pupdate.emit(self.count)
                continue

            result = self.try_change_username(username)

            if result == "taken":
                self.log(f"[TAKEN] {username}")

            elif result == "available":
                text = getattr(self, '_last_response', '')
                if "already been changed" in text.lower():
                    self.log(f"[AVAILABLE] {username} — Likely available! Weekly limit hit, verify in-game.")
                else:
                    self.log(f"[AVAILABLE] {username} — Username changed! Reverting now...")
                    self.revert_username()

            elif result == "session_expired":
                self.log("Session expired mid-check! Get a fresh cookie.")
                break

            elif result == "unknown":
                self.log(f"[TAKEN] {username} (same as current or unrecognized response)")

            else:
                self.log(f"[ERROR] {username} — Network or API error")

            self.count += 1
            self.pupdate.emit(self.count)
            QThread.msleep(2000)

        self.log("\nDone!")


# ------------------- GUI ------------------- #
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GD Cookie Username Checker")
        self.setGeometry(150, 150, 950, 800)
        self.thread = None
        self.initUI()

    def initUI(self):
        wid = QWidget(self)
        self.setCentralWidget(wid)
        layout = QVBoxLayout()
        wid.setLayout(layout)

        # Title
        title = QLabel("GD Cookie-Based Username Checker")
        font = QFont()
        font.setPointSize(15)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("padding: 15px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6b35, stop:1 #f7931e); color: white; border-radius: 5px;")
        layout.addWidget(title)

        # How to get cookie
        warn = QLabel(
            "HOW TO GET YOUR COOKIE:\n"
            "1. Go to boomlings.com and log in\n"
            "2. Press F12 -> Application tab -> Cookies -> www.boomlings.com\n"
            "3. Copy the Name and Value of each cookie and paste below as:  name=value; name2=value2"
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("background-color: #fff3cd; padding: 10px; border-radius: 5px; color: #856404;")
        layout.addWidget(warn)

        # Credentials
        cred_group = QGroupBox("Step 1: Your Session Info")
        cred_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        cred_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Your current GD username e.g. 2525252")
        cred_layout.addRow("GD Username:", self.username_input)

        self.cookie_input = QTextEdit()
        self.cookie_input.setPlaceholderText("Paste just the cookie value e.g. odt5cg26c0jmi9nfbvcpv55oe7")
        self.cookie_input.setMaximumHeight(70)
        cred_layout.addRow("Cookie String:", self.cookie_input)

        cred_group.setLayout(cred_layout)
        layout.addWidget(cred_group)

        # Usernames to check
        check_group = QGroupBox("Step 2: Usernames to Check (one per line)")
        check_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        check_layout = QVBoxLayout()
        self.names_input = QTextEdit()
        self.names_input.setPlaceholderText("RobTop\n2525252\ncoolname123\n...")
        self.names_input.setMaximumHeight(150)
        check_layout.addWidget(self.names_input)
        check_group.setLayout(check_layout)
        layout.addWidget(check_group)

        # Output
        out_group = QGroupBox("Step 3: Results")
        out_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        out_layout = QVBoxLayout()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: 'Courier New'; font-size: 10pt;")
        out_layout.addWidget(self.output)
        out_group.setLayout(out_layout)
        layout.addWidget(out_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("START CHECKING")
        self.start_btn.clicked.connect(self.start)
        self.start_btn.setStyleSheet("background-color: #ff6b35; color: white; font-weight: bold; padding: 12px; font-size: 13px;")
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("STOP")
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold; padding: 12px; font-size: 13px;")
        btn_layout.addWidget(self.stop_btn)

        clear_btn = QPushButton("Clear Results")
        clear_btn.clicked.connect(self.output.clear)
        clear_btn.setStyleSheet("padding: 12px;")
        btn_layout.addWidget(clear_btn)

        layout.addLayout(btn_layout)

        self.progress = QProgressBar()
        self.progress.setStyleSheet("QProgressBar { text-align: center; height: 22px; } QProgressBar::chunk { background-color: #ff6b35; }")
        layout.addWidget(self.progress)

        self.status = QLabel("Ready")
        self.status.setStyleSheet("padding: 8px; font-weight: bold; background-color: #e0e0e0; border-radius: 3px;")
        layout.addWidget(self.status)

    def start(self):
        current_user = self.username_input.text().strip()
        cookie = self.cookie_input.toPlainText().strip()
        names_raw = self.names_input.toPlainText().strip()

        if not current_user or not cookie:
            QMessageBox.warning(self, "Missing Info", "Please enter your GD username and cookie!")
            return

        usernames = [line.strip() for line in names_raw.splitlines() if line.strip()]
        if not usernames:
            QMessageBox.warning(self, "No Usernames", "Please enter at least one username to check!")
            return

        self.output.clear()
        self.progress.setMaximum(len(usernames))
        self.progress.setValue(0)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status.setText(f"Checking {len(usernames)} usernames...")
        self.status.setStyleSheet("padding: 8px; font-weight: bold; background-color: #fff9c4; border-radius: 3px;")

        self.thread = AccountChecker(current_user, cookie, usernames)
        self.thread.update.connect(self.output.append)
        self.thread.pupdate.connect(self.progress.setValue)
        self.thread.finished.connect(self.done)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.thread.stop()
            self.thread.quit()
            self.thread.wait(2000)
        self.done()

    def done(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status.setText("Done!")
        self.status.setStyleSheet("padding: 8px; font-weight: bold; background-color: #c8e6c9; border-radius: 3px;")


# ------------------- Run ------------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec_())
