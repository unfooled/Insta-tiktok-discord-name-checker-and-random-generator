import sys
import requests
import random
import string
import traceback
import threading
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QFont

# ------------------- Checker Thread ------------------- #
class Checker(QThread):
    update = pyqtSignal(str)
    pupdate = pyqtSignal(int)
    count = 0

    def __init__(self, usernames, webhook_url=None, debug=False, save_to_file=True):
        super().__init__()
        self.usernames = usernames
        self.webhook_url = webhook_url
        self.running = True
        self.debug = debug
        self.save_to_file = save_to_file
        self.consecutive_errors = 0
        self.request_delay = 0.2  # initial delay between requests (faster)
        self.min_delay = 0.01     # minimum allowed delay (ultra fast)
        self.rate_lock = threading.Lock()
        self.last_request_time = 0

    def run(self):
        from concurrent.futures import ThreadPoolExecutor
        self.count_lock = threading.Lock()
        max_workers = 5
        rate_limited_usernames = []
        def worker(username):
            if not self.running:
                return
            result = self.check_username(username, rate_limited_usernames)
            with self.count_lock:
                self.count += 1
                self.pupdate.emit(self.count)
            return result
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for username in self.usernames:
                executor.submit(worker, username)

        # Pause before retrying rate-limited usernames
        if rate_limited_usernames:
            self.update.emit(f"\n⏳ Waiting 30 seconds before retrying {len(rate_limited_usernames)} rate-limited usernames...")
            time.sleep(30)
            self.count_lock.acquire()
            self.count = 0
            self.count_lock.release()
            def retry_worker(username):
                if not self.running:
                    return
                result = self.check_username(username)
                with self.count_lock:
                    self.count += 1
                    self.pupdate.emit(self.count)
                return result
            with ThreadPoolExecutor(max_workers=3) as executor:
                for username in rate_limited_usernames:
                    executor.submit(retry_worker, username)

    def stop(self):
        self.running = False

    def check_username(self, username, rate_limited_usernames=None):
        if not self.running:
            return
        retries = 0
        max_retries = 2
        while retries <= max_retries:
            if not self.running:
                return
            # Global request limiter
            with self.rate_lock:
                now = time.time()
                wait = self.request_delay - (now - self.last_request_time)
                if wait > 0:
                    time.sleep(wait)
                self.last_request_time = time.time()
            # Random jitter
            time.sleep(random.uniform(0.02, 0.08))
            try:
                url = f"https://www.reddit.com/user/{username}"
                webhook_desc = f"`{username}` [is available for **Reddit**!](https://www.reddit.com/user/{username})"
                webhook_color = 0xFF4500
                save_file = "available_reddit_usernames.txt"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                if self.debug:
                    self.update.emit(f"\n{'='*60}")
                    self.update.emit(f"[DEBUG] Checking: {username}")
                    self.update.emit(f"[DEBUG] URL: {url}")
                    self.update.emit(f"[DEBUG] Status Code: {response.status_code}")
                page = response.text
                if response.status_code == 200:
                    if "Sorry, nobody on Reddit goes by that name." in page:
                        self.update.emit(f"✅ [AVAILABLE] {username}")
                        if self.save_to_file:
                            try:
                                with open(save_file, "a") as f:
                                    f.write(f"{username}\n")
                            except Exception as e:
                                if self.debug:
                                    self.update.emit(f"[DEBUG] Failed to save to file: {e}")
                        if self.webhook_url:
                            self.send_to_discord(username, webhook_desc, webhook_color)
                        self.consecutive_errors = 0
                        if self.request_delay > 0.2:
                            self.request_delay = max(self.min_delay, self.request_delay * 0.9)
                        return
                    elif "This account has been banned" in page:
                        self.update.emit(f"🚫 [BANNED] {username}")
                        self.consecutive_errors = 0
                        if self.request_delay > 0.2:
                            self.request_delay = max(self.min_delay, self.request_delay * 0.9)
                        return
                    else:
                        self.update.emit(f"❌ [TAKEN] {username}")
                        self.consecutive_errors = 0
                        if self.request_delay > 0.2:
                            self.request_delay = max(self.min_delay, self.request_delay * 0.9)
                        return
                elif response.status_code == 404:
                    self.update.emit(f"✅ [AVAILABLE] {username}")
                    self.consecutive_errors = 0
                    if self.save_to_file:
                        try:
                            with open(save_file, "a") as f:
                                f.write(f"{username}\n")
                        except Exception as e:
                            if self.debug:
                                self.update.emit(f"[DEBUG] Failed to save to file: {e}")
                    if self.webhook_url:
                        self.send_to_discord(username, webhook_desc, webhook_color)
                    if self.request_delay > 0.2:
                        self.request_delay = max(self.min_delay, self.request_delay * 0.9)
                    return
                elif response.status_code == 429:
                    self.update.emit(f"⚠️ [RATE LIMIT] {username}: Reddit is rate limiting! Skipping for now.")
                    self.request_delay = min(10, self.request_delay * 1.7)
                    if rate_limited_usernames is not None:
                        rate_limited_usernames.append(username)
                    return
                elif response.status_code == 403:
                    self.update.emit(f"⚠️ [BLOCKED] {username}: Reddit blocked the request!")
                    self.consecutive_errors += 1
                    self.request_delay = min(10, self.request_delay * 1.7)
                    time.sleep(10)
                    retries += 1
                else:
                    self.update.emit(f"⚠️ [UNKNOWN] {username}: Status {response.status_code}")
                    self.consecutive_errors += 1
                    retries += 1
            except requests.exceptions.Timeout:
                self.consecutive_errors += 1
                self.update.emit(f"⏱️ [TIMEOUT] {username} (retry {retries+1})")
                sleep_time = min(30, 2 ** self.consecutive_errors)
                time.sleep(sleep_time)
                retries += 1
            except Exception as e:
                self.consecutive_errors += 1
                if self.debug:
                    error_msg = traceback.format_exc()
                    self.update.emit(f"⚠️ [ERROR] {username}:\n{error_msg}")
                else:
                    error_msg = str(e)
                    self.update.emit(f"⚠️ [ERROR] {username}: {error_msg}")
                retries += 1
        self.update.emit(f"❌ [FAILED] {username} after {max_retries+1} attempts")

    def send_to_discord(self, username, desc, color):
        try:
            webhook_data = {
                "content": "",
                "tts": False,
                "embeds": [
                    {
                        "id": 487189062,
                        "description": desc,
                        "color": color,
                        "fields": []
                    }
                ],
                "components": [],
                "actions": {},
                "flags": 0
            }
            response = requests.post(self.webhook_url, json=webhook_data, timeout=5)
            if response.status_code == 204:
                if self.debug:
                    self.update.emit(f"[DEBUG] ✅ Sent {username} to Discord webhook")
            else:
                if self.debug:
                    self.update.emit(f"[DEBUG] ⚠️ Webhook failed: Status {response.status_code}")
        except Exception as e:
            if self.debug:
                self.update.emit(f"[DEBUG] ⚠️ Webhook error: {str(e)}")

# ------------------- GUI App ------------------- #
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reddit Username Checker")
        self.setGeometry(150, 150, 1100, 800)
        self.thread = None
        self.initUI()

    def initUI(self):
        wid = QWidget(self)
        self.setCentralWidget(wid)
        main_layout = QVBoxLayout()
        wid.setLayout(main_layout)

        # Title
        self.title = QLabel()
        self.title_font = QFont()
        self.title_font.setPointSize(16)
        self.title_font.setBold(True)
        self.title.setFont(self.title_font)
        main_layout.addWidget(self.title)

        # Info Section
        self.info_group = QGroupBox()
        self.info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        self.info_layout = QVBoxLayout()
        self.instruction = QLabel()
        self.instruction.setWordWrap(True)
        self.instruction.setStyleSheet("background-color: #ff4500; padding: 10px; border-radius: 3px; color: white;")
        self.info_layout.addWidget(self.instruction)
        self.info_group.setLayout(self.info_layout)
        main_layout.addWidget(self.info_group)

        # Webhook Section
        webhook_group = QGroupBox("🔔 Discord Webhook (Optional)")
        webhook_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        webhook_layout = QVBoxLayout()
        webhook_info = QLabel("💬 Get notified when available usernames are found!")
        webhook_info.setWordWrap(True)
        webhook_info.setStyleSheet("background-color: #ffe5d5; padding: 8px; border-radius: 3px; color: #ff4500;")
        webhook_layout.addWidget(webhook_info)
        webhook_input_layout = QHBoxLayout()
        self.webhook_input = QLineEdit()
        self.webhook_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        webhook_input_layout.addWidget(self.webhook_input)
        test_webhook_btn = QPushButton("🧪 Test")
        test_webhook_btn.setMaximumWidth(80)
        test_webhook_btn.clicked.connect(self.test_webhook)
        webhook_input_layout.addWidget(test_webhook_btn)
        webhook_layout.addLayout(webhook_input_layout)
        webhook_group.setLayout(webhook_layout)
        main_layout.addWidget(webhook_group)

        # Generator Section
        gen_group = QGroupBox("Step 1: Generate Random Usernames (Optional)")
        gen_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        gen_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Length:"))
        self.length_input = QLineEdit("3")
        self.length_input.setMaximumWidth(60)
        row1.addWidget(self.length_input)
        row1.addWidget(QLabel("Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g., reddit")
        self.prefix_input.setMaximumWidth(100)
        row1.addWidget(self.prefix_input)
        row1.addWidget(QLabel("Suffix:"))
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g., -pro")
        self.suffix_input.setMaximumWidth(100)
        row1.addWidget(self.suffix_input)
        row1.addWidget(QLabel("Count:"))
        self.count_input = QLineEdit("10")
        self.count_input.setMaximumWidth(60)
        row1.addWidget(self.count_input)
        row1.addStretch()
        gen_layout.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Letters only (abc)",
            "Letters + Numbers (a1b2)",
            "Numbers + Letters (12ab)",
            "Numbers only (1234)",
            "Letters_Letters (abc_def)",
            "CamelCase (AbcDef)"
        ])
        self.pattern_combo.setMaximumWidth(200)
        row2.addWidget(self.pattern_combo)
        self.gen_button = QPushButton("🎲 Generate")
        self.gen_button.clicked.connect(self.generate_usernames)
        self.gen_button.setStyleSheet("background-color: #ff4500; color: white; padding: 8px; font-weight: bold;")
        row2.addWidget(self.gen_button)
        self.debug_checkbox = QCheckBox("🐛 Debug Mode (Detailed)")
        self.debug_checkbox.setToolTip("Show detailed responses")
        row2.addWidget(self.debug_checkbox)
        self.save_checkbox = QCheckBox("💾 Save to File")
        self.save_checkbox.setChecked(True)
        self.save_checkbox.setToolTip("Save available usernames to file")
        row2.addWidget(self.save_checkbox)
        row2.addStretch()
        gen_layout.addLayout(row2)
        gen_group.setLayout(gen_layout)
        main_layout.addWidget(gen_group)

        # Input/Output Section
        io_group = QGroupBox("Step 2: Check Usernames")
        io_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        io_layout = QHBoxLayout()
        input_box = QVBoxLayout()
        input_label = QLabel("📝 Usernames to Check:")
        input_label.setStyleSheet("font-weight: bold;")
        input_box.addWidget(input_label)
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter usernames here\n(one per line)\n\nExample:\nabc\nxyz\nredditpro123")
        input_box.addWidget(self.input_text)
        output_box = QVBoxLayout()
        output_label = QLabel("📊 Results:")
        output_label.setStyleSheet("font-weight: bold;")
        output_box.addWidget(output_label)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #1a1a1a; color: #ff4500; font-family: Consolas, Monaco, monospace; padding: 10px;")
        output_box.addWidget(self.output_text)
        io_layout.addLayout(input_box)
        io_layout.addLayout(output_box)
        io_group.setLayout(io_layout)
        main_layout.addWidget(io_group)

        # Control Buttons
        btn_layout = QHBoxLayout()
        self.start_button = QPushButton("▶️ START CHECKING")
        self.start_button.clicked.connect(self.start_clicked)
        btn_layout.addWidget(self.start_button)
        self.stop_button = QPushButton("⏹️ STOP")
        self.stop_button.clicked.connect(self.stop_clicked)
        self.stop_button.setEnabled(False)
        btn_layout.addWidget(self.stop_button)
        self.clear_button = QPushButton("🗑️ Clear Results")
        self.clear_button.clicked.connect(lambda: self.output_text.clear())
        btn_layout.addWidget(self.clear_button)
        main_layout.addLayout(btn_layout)
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        self.status_label = QLabel()
        main_layout.addWidget(self.status_label)

        self.update_ui()

    def generate_usernames(self):
        try:
            length = int(self.length_input.text())
        except:
            length = 3
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()
        pattern = self.pattern_combo.currentText()
        try:
            count = int(self.count_input.text())
        except:
            count = 10
        generated = []
        attempts = 0
        max_attempts = count * 3
        while len(generated) < count and attempts < max_attempts:
            attempts += 1
            username = ""
            if pattern == "Letters only (abc)":
                username = "".join(random.choice(string.ascii_lowercase) for _ in range(length))
            elif pattern == "Letters + Numbers (a1b2)":
                chars = string.ascii_lowercase + string.digits
                username = "".join(random.choice(chars) for _ in range(length))
            elif pattern == "Numbers + Letters (12ab)":
                num_count = random.randint(1, max(1, length - 2))
                letter_count = length - num_count
                username = "".join(random.choice(string.digits) for _ in range(num_count))
                username += "".join(random.choice(string.ascii_lowercase) for _ in range(letter_count))
            elif pattern == "Numbers only (1234)":
                username = "".join(random.choice(string.digits) for _ in range(length))
            elif pattern == "Letters_Letters (abc_def)":
                part1_len = length // 2
                part2_len = length - part1_len
                part1 = "".join(random.choice(string.ascii_lowercase) for _ in range(part1_len))
                part2 = "".join(random.choice(string.ascii_lowercase) for _ in range(part2_len))
                username = f"{part1}_{part2}"
            elif pattern == "CamelCase (AbcDef)":
                parts = []
                remaining = length
                while remaining > 0:
                    part_len = random.randint(2, min(4, remaining))
                    part = "".join(random.choice(string.ascii_lowercase) for _ in range(part_len))
                    part = part.capitalize()
                    parts.append(part)
                    remaining -= part_len
                username = "".join(parts)
            username = prefix + username + suffix
            username = ''.join(c for c in username if c.isalnum() or c == '_')
            if len(username) > 0 and username not in generated:
                generated.append(username)
        if len(generated) == 0:
            self.status_label.setText(f"⚠️ No valid usernames generated")
            self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #fff3cd; border-radius: 3px;")
            return
        existing = self.input_text.toPlainText().strip()
        all_usernames = ("\n".join(generated) if not existing else existing + "\n" + "\n".join(generated))
        self.input_text.setText(all_usernames)
        self.status_label.setText(f"✅ Generated {len(generated)} usernames")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #c8e6c9; border-radius: 3px;")

    def test_webhook(self):
        webhook_url = self.webhook_input.text().strip()
        if not webhook_url:
            QMessageBox.warning(self, "No Webhook", "Please enter a webhook URL first!")
            return
        try:
            test_data = {
                "embeds": [{
                    "title": "🧪 Test Message",
                    "description": "Your webhook is working correctly!",
                    "color": 0xFF4500,
                    "footer": {
                        "text": "Reddit Username Checker - Webhook Test"
                    }
                }]
            }
            response = requests.post(webhook_url, json=test_data, timeout=5)
            if response.status_code == 204:
                QMessageBox.information(self, "Success", "✅ Webhook test successful!\nCheck your Discord channel.")
            else:
                QMessageBox.warning(self, "Failed", f"❌ Webhook test failed!\nStatus code: {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Failed to send test message:\n{str(e)}")

    def start_clicked(self):
        usernames = self.get_usernames()
        if not usernames:
            QMessageBox.warning(self, "No Usernames", "Please enter or generate usernames to check!")
            return
        debug = self.debug_checkbox.isChecked()
        save_to_file = self.save_checkbox.isChecked()
        webhook_url = self.webhook_input.text().strip() or None
        self.progress_bar.setMaximum(len(usernames))
        self.progress_bar.setValue(0)
        self.output_text.clear()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        status_text = f"🔄 Checking {len(usernames)} usernames"
        if save_to_file:
            status_text += " (saving to file)"
        if webhook_url:
            status_text += " (webhook enabled)"
        status_text += " on Reddit..."
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #fff9c4; border-radius: 3px;")
        self.thread = Checker(usernames, webhook_url, debug, save_to_file)
        self.thread.update.connect(self.update_text)
        self.thread.pupdate.connect(self.update_progress)
        self.thread.finished.connect(self.checking_finished)
        self.thread.start()

    def stop_clicked(self):
        if self.thread:
            self.thread.stop()
            self.thread.quit()
            self.thread.wait(2000)
        self.checking_finished()

    def checking_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText(f"✅ Checking complete on Reddit!")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #c8e6c9; border-radius: 3px;")

    def update_text(self, text):
        # Color coding for UI
        color = None
        if '[TAKEN]' in text:
            color = '#888888'  # gray
        elif '[AVAILABLE]' in text:
            color = '#00ff00'  # green
        elif '[BANNED]' in text:
            color = '#ff4500'  # reddit orange
        elif '[RATE LIMIT]' in text or '[BLOCKED]' in text or '[UNKNOWN]' in text or '[ERROR]' in text or '[TIMEOUT]' in text:
            color = '#fff700'  # yellow
        else:
            color = '#ff4500'  # default reddit orange

        # Console output with color
        try:
            import sys
            if color == '#00ff00':
                print(f"\033[92m{text}\033[0m")  # green
            elif color == '#888888':
                print(f"\033[90m{text}\033[0m")  # gray
            elif color == '#fff700':
                print(f"\033[93m{text}\033[0m")  # yellow
            elif color == '#ff4500':
                print(f"\033[91m{text}\033[0m")  # orange/red
            else:
                print(text)
        except Exception:
            print(text)

        # UI output with color
        self.output_text.append(f'<span style="color:{color}">{text}</span>')
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        self.output_text.setTextCursor(cursor)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        total = self.progress_bar.maximum()
        percent = int((value / total) * 100) if total > 0 else 0
        self.status_label.setText(f"🔄 Progress: {value}/{total} ({percent}%) on Reddit")

    def get_usernames(self):
        txt = self.input_text.toPlainText().strip()
        usernames = []
        for line in txt.splitlines():
            u = line.strip()
            if u and all(c.isalnum() or c == '_' for c in u):
                usernames.append(u)
        return usernames

    def update_ui(self):
        self.title.setText("👤 Reddit Username Checker")
        self.title.setStyleSheet("padding: 15px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4500, stop:1 #ffb380); color: white; border-radius: 5px;")
        self.info_group.setTitle("ℹ️ About Reddit Username Checker")
        self.instruction.setText("✨ Check if Reddit usernames are available!\n⚠️ Note: Reddit may rate limit requests. Check responsibly.\n💾 Available usernames are saved to: available_reddit_usernames.txt")
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; height: 25px; } QProgressBar::chunk { background-color: #ff4500; }")

# ------------------- Run ------------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec_())
