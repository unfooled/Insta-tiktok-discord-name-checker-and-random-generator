import sys, requests, asyncio, random, string, traceback
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QFont

# ------------------- Checker Thread ------------------- #
class Checker(QThread):
    update = pyqtSignal(str)
    pupdate = pyqtSignal(int)
    count = 0

    def __init__(self, usernames, webhook_url=None, debug=False):
        super().__init__()
        self.usernames = usernames
        self.webhook_url = webhook_url
        self.running = True
        self.debug = debug
        self.consecutive_errors = 0
        self.max_errors_before_pause = 3

    def run(self):
        for i, username in enumerate(self.usernames):
            if not self.running:
                break
            self.check_user(username)
            self.count += 1
            self.pupdate.emit(self.count)

    def stop(self):
        self.running = False

    def check_user(self, username):
        if not self.running:
            return

        try:
            url = "https://users.roblox.com/v1/usernames/users"
            data = {"usernames": [username]}
            
            if self.debug:
                self.update.emit(f"\n{'='*60}")
                self.update.emit(f"[DEBUG] Checking: {username}")
                self.update.emit(f"[DEBUG] API URL: {url}")
            
            response = requests.post(url, json=data, timeout=10)
            
            if self.debug:
                self.update.emit(f"[DEBUG] Status Code: {response.status_code}")
                self.update.emit(f"[DEBUG] Response: {response.text[:200]}")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("data") and len(result["data"]) > 0:
                    user_data = result["data"][0]
                    if user_data.get("id") is not None:
                        user_id = user_data.get("id")
                        display_name = user_data.get("displayName", username)
                        self.update.emit(f"❌ [TAKEN] {username} (ID: {user_id}, Display: {display_name})")
                        self.consecutive_errors = 0
                        return
                
                # If we get here, username is available
                self.update.emit(f"✅ [AVAILABLE] {username}")
                self.consecutive_errors = 0
                
                # Send to Discord webhook if provided
                if self.webhook_url:
                    self.send_to_discord(username)
                
            elif response.status_code == 429:
                self.update.emit(f"⚠️ [RATE LIMIT] {username}: Slow down!")
                self.consecutive_errors += 1
                
            else:
                self.update.emit(f"⚠️ [ERROR] {username}: Status {response.status_code}")
                self.consecutive_errors += 1
                
        except requests.exceptions.Timeout:
            self.consecutive_errors += 1
            self.update.emit(f"⏱️ [TIMEOUT] {username}")
            
        except Exception as e:
            self.consecutive_errors += 1
            if self.debug:
                error_msg = traceback.format_exc()
                self.update.emit(f"⚠️ [ERROR] {username}:\n{error_msg}")
            else:
                error_msg = str(e)
                self.update.emit(f"⚠️ [ERROR] {username}: {error_msg}")

    def send_to_discord(self, username):
        """Send available username to Discord webhook"""
        try:
            webhook_data = {
                "embeds": [{
                    "title": "🎮 Available Roblox Username Found!",
                    "description": f"**Username:** `{username}`",
                    "color": 3447003,  # Blue color
                    "fields": [
                        {
                            "name": "🔗 Direct Link",
                            "value": f"https://www.roblox.com/search/users?keyword={username}",
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": "Roblox Username Checker"
                    }
                }]
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
        self.setWindowTitle("Roblox Username Checker")
        self.setGeometry(150, 150, 1100, 800)
        self.thread = None
        self.initUI()

    def initUI(self):
        wid = QWidget(self)
        self.setCentralWidget(wid)
        main_layout = QVBoxLayout()
        wid.setLayout(main_layout)

        # Title
        title = QLabel("🎮 Roblox Username Checker")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("padding: 15px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e74c3c, stop:1 #3498db); color: white; border-radius: 5px;")
        main_layout.addWidget(title)

        # Info Section
        info_group = QGroupBox("ℹ️ About Roblox Username Checker")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        info_layout = QVBoxLayout()
        
        instruction = QLabel("✨ No login required! This checker uses Roblox's public API.\n⚠️ Note: Roblox may rate limit requests if you check too many at once.")
        instruction.setWordWrap(True)
        instruction.setStyleSheet("background-color: #e7f3ff; padding: 10px; border-radius: 3px; color: #004085;")
        info_layout.addWidget(instruction)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # Webhook Section
        webhook_group = QGroupBox("🔔 Discord Webhook (Optional)")
        webhook_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        webhook_layout = QVBoxLayout()
        
        webhook_info = QLabel("💬 Paste your Discord webhook URL to get notified when available usernames are found!")
        webhook_info.setWordWrap(True)
        webhook_info.setStyleSheet("background-color: #f8d7da; padding: 8px; border-radius: 3px; color: #721c24;")
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
        
        # First row - basic options
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Length:"))
        self.length_input = QLineEdit("5")
        self.length_input.setMaximumWidth(60)
        row1.addWidget(self.length_input)
        
        row1.addWidget(QLabel("Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g., Pro")
        self.prefix_input.setMaximumWidth(100)
        row1.addWidget(self.prefix_input)
        
        row1.addWidget(QLabel("Suffix:"))
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g., _YT")
        self.suffix_input.setMaximumWidth(100)
        row1.addWidget(self.suffix_input)
        
        row1.addWidget(QLabel("Count:"))
        self.count_input = QLineEdit("10")
        self.count_input.setMaximumWidth(60)
        row1.addWidget(self.count_input)
        
        row1.addStretch()
        gen_layout.addLayout(row1)
        
        # Second row - pattern options
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Letters only (abc)",
            "Letters + Numbers (a1b2)",
            "Numbers + Letters (12ab)",
            "Letters_Letters (abc_def)",
            "CamelCase (AbcDef)"
        ])
        self.pattern_combo.setMaximumWidth(200)
        row2.addWidget(self.pattern_combo)
        
        self.gen_button = QPushButton("🎲 Generate")
        self.gen_button.clicked.connect(self.generate_usernames)
        self.gen_button.setStyleSheet("background-color: #3498db; color: white; padding: 8px; font-weight: bold;")
        row2.addWidget(self.gen_button)
        
        self.debug_checkbox = QCheckBox("🐛 Debug Mode (Detailed)")
        self.debug_checkbox.setToolTip("Show detailed API responses")
        row2.addWidget(self.debug_checkbox)
        
        row2.addStretch()
        gen_layout.addLayout(row2)
        
        gen_group.setLayout(gen_layout)
        main_layout.addWidget(gen_group)

        # Input/Output Section
        io_group = QGroupBox("Step 2: Check Usernames")
        io_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        io_layout = QHBoxLayout()
        
        # Input side
        input_box = QVBoxLayout()
        input_label = QLabel("📝 Usernames to Check:")
        input_label.setStyleSheet("font-weight: bold;")
        input_box.addWidget(input_label)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter usernames here\n(one per line)\n\nExample:\nCoolGamer123\nProPlayer\nEpicUser")
        input_box.addWidget(self.input_text)
        
        # Output side
        output_box = QVBoxLayout()
        output_label = QLabel("📊 Results:")
        output_label.setStyleSheet("font-weight: bold;")
        output_box.addWidget(output_label)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #1a1a1a; color: #00ff00; font-family: Consolas, Monaco, monospace; padding: 10px;")
        output_box.addWidget(self.output_text)
        
        io_layout.addLayout(input_box)
        io_layout.addLayout(output_box)
        io_group.setLayout(io_layout)
        main_layout.addWidget(io_group)

        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶️ START CHECKING")
        self.start_button.clicked.connect(self.start_clicked)
        self.start_button.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 15px; font-size: 14px;")
        btn_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ STOP")
        self.stop_button.clicked.connect(self.stop_clicked)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 15px; font-size: 14px;")
        btn_layout.addWidget(self.stop_button)
        
        self.clear_button = QPushButton("🗑️ Clear Results")
        self.clear_button.clicked.connect(lambda: self.output_text.clear())
        self.clear_button.setStyleSheet("padding: 15px;")
        btn_layout.addWidget(self.clear_button)
        
        main_layout.addLayout(btn_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; height: 25px; } QProgressBar::chunk { background-color: #3498db; }")
        main_layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QLabel("✅ Ready - No login required!")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #e0e0e0; border-radius: 3px;")
        main_layout.addWidget(self.status_label)

    def generate_usernames(self):
        try:
            length = int(self.length_input.text())
        except:
            length = 5
        
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()
        pattern = self.pattern_combo.currentText()
        
        try:
            count = int(self.count_input.text())
        except:
            count = 10

        generated = []
        
        for _ in range(count):
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
            
            # Add prefix and suffix
            username = prefix + username + suffix
            
            # Roblox validation: 3-20 chars, alphanumeric + underscores
            username = ''.join(c for c in username if c.isalnum() or c == '_')
            
            if 3 <= len(username) <= 20:
                generated.append(username)

        existing = self.input_text.toPlainText().strip()
        all_users = ("\n".join(generated) if not existing else existing + "\n" + "\n".join(generated))
        self.input_text.setText(all_users)
        
        self.status_label.setText(f"✅ Generated {len(generated)} usernames")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #c8e6c9; border-radius: 3px;")

    def test_webhook(self):
        """Test the Discord webhook"""
        webhook_url = self.webhook_input.text().strip()
        
        if not webhook_url:
            QMessageBox.warning(self, "No Webhook", "Please enter a webhook URL first!")
            return
        
        try:
            test_data = {
                "embeds": [{
                    "title": "🧪 Test Message",
                    "description": "Your webhook is working correctly!",
                    "color": 5763719,  # Green color
                    "footer": {
                        "text": "Roblox Username Checker - Webhook Test"
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
        webhook_url = self.webhook_input.text().strip() or None
        
        self.progress_bar.setMaximum(len(usernames))
        self.progress_bar.setValue(0)
        self.output_text.clear()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        if webhook_url:
            self.status_label.setText(f"🔄 Checking {len(usernames)} usernames (webhook enabled)...")
        else:
            self.status_label.setText(f"🔄 Checking {len(usernames)} usernames...")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #fff9c4; border-radius: 3px;")

        self.thread = Checker(usernames, webhook_url, debug)
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
        self.status_label.setText("✅ Checking complete!")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #c8e6c9; border-radius: 3px;")

    def update_text(self, text):
        self.output_text.append(text)
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        self.output_text.setTextCursor(cursor)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        total = self.progress_bar.maximum()
        percent = int((value / total) * 100) if total > 0 else 0
        self.status_label.setText(f"🔄 Progress: {value}/{total} ({percent}%)")

    def get_usernames(self):
        txt = self.input_text.toPlainText().strip()
        usernames = []
        for line in txt.splitlines():
            u = line.strip()
            # Roblox allows letters, numbers, and underscores
            if u and (u.replace('_', '').isalnum()):
                usernames.append(u)
        return usernames

# ------------------- Run ------------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec_())
