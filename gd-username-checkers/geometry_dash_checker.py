import sys, requests, random, string, traceback
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
            # Longer delay to avoid rate limiting (1 second between requests)
            QThread.msleep(1000)

    def stop(self):
        self.running = False

    def check_user(self, username):
        if not self.running:
            return

        try:
            # Official Geometry Dash API endpoint
            url = "http://www.boomlings.com/database/getGJUsers20.php"
            
            # Required parameters for the official API
            data = {
                "str": username,
                "total": 0,
                "page": 0,
                "secret": "Wmfd2893gb7"  # Public secret used by the game
            }
            
            headers = {
                "User-Agent": ""  # Empty User-Agent as used by the game
            }
            
            if self.debug:
                self.update.emit(f"\n{'='*60}")
                self.update.emit(f"[DEBUG] Checking: {username}")
                self.update.emit(f"[DEBUG] API URL: {url}")
                self.update.emit(f"[DEBUG] Data: {data}")
            
            response = requests.post(url, data=data, headers=headers, timeout=10)
            
            if self.debug:
                self.update.emit(f"[DEBUG] Status Code: {response.status_code}")
                self.update.emit(f"[DEBUG] Response: {response.text[:200]}")
            
            if response.status_code == 200:
                response_text = response.text.strip()
                
                # Check if the response is an error code
                if response_text == "-1":
                    # -1 means user not found (username is available!)
                    self.update.emit(f"✅ [AVAILABLE] {username} - Verify in-game!")
                    self.consecutive_errors = 0
                    
                    # Send to Discord webhook if provided
                    if self.webhook_url:
                        self.send_to_discord(username)
                
                elif response_text == "-2":
                    # -2 can sometimes indicate rate limiting
                    self.update.emit(f"⚠️ [RATE LIMIT] {username}: Waiting 60 seconds...")
                    self.consecutive_errors += 1
                    QThread.msleep(60000)  # Wait 60 seconds
                
                elif "#" in response_text and ":" in response_text:
                    # User exists - parse the response
                    # Format: username:playerID:stars:demons:...
                    try:
                        parts = response_text.split("#")[0].split(":")
                        if len(parts) >= 4:
                            found_username = parts[0]
                            player_id = parts[1]
                            stars = parts[2]
                            demons = parts[3]
                            self.update.emit(f"❌ [TAKEN] {username} (ID: {player_id}, Stars: {stars}, Demons: {demons})")
                        else:
                            self.update.emit(f"❌ [TAKEN] {username}")
                    except:
                        self.update.emit(f"❌ [TAKEN] {username}")
                    
                    self.consecutive_errors = 0
                else:
                    # Unexpected response
                    self.update.emit(f"⚠️ [UNKNOWN] {username}: Unexpected response")
                    if self.debug:
                        self.update.emit(f"[DEBUG] Full response: {response_text}")
                    self.consecutive_errors += 1
                
            elif response.status_code == 429:
                self.update.emit(f"⚠️ [RATE LIMIT] {username}: Waiting 60 seconds...")
                self.consecutive_errors += 1
                QThread.msleep(60000)  # Wait 60 seconds (1 minute) on rate limit
                
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
                    "title": "🔺 Available Geometry Dash Username Found!",
                    "description": f"**Username:** `{username}`\n\n⚠️ **Note:** Always verify in-game! Some usernames may be banned/reserved.",
                    "color": 16760576,  # Orange/gold color
                    "fields": [
                        {
                            "name": "📝 How to Claim",
                            "value": "Open Geometry Dash → Account → Click 'More' → Change your username!",
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": "Geometry Dash Username Checker"
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
        self.setWindowTitle("Geometry Dash Username Checker")
        self.setGeometry(150, 150, 1100, 800)
        self.thread = None
        self.initUI()

    def initUI(self):
        wid = QWidget(self)
        self.setCentralWidget(wid)
        main_layout = QVBoxLayout()
        wid.setLayout(main_layout)

        # Title
        title = QLabel("🔺 Geometry Dash Username Checker")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("padding: 15px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6b35, stop:1 #f7931e); color: white; border-radius: 5px;")
        main_layout.addWidget(title)

        # Info Section
        info_group = QGroupBox("ℹ️ About Geometry Dash Username Checker")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        info_layout = QVBoxLayout()
        
        instruction = QLabel("✨ Uses the official Geometry Dash API (boomlings.com) to check usernames.\n⚠️ Note: Some 'available' usernames may be banned/reserved - always verify in-game!\n💡 Please be respectful and don't spam the servers!")
        instruction.setWordWrap(True)
        instruction.setStyleSheet("background-color: #fff3cd; padding: 10px; border-radius: 3px; color: #856404;")
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
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Length:"))
        self.length_input = QLineEdit("6")
        self.length_input.setMaximumWidth(60)
        row1.addWidget(self.length_input)
        
        row1.addWidget(QLabel("Count:"))
        self.count_input = QLineEdit("20")
        self.count_input.setMaximumWidth(60)
        row1.addWidget(self.count_input)
        
        row1.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Letters only (abc)",
            "Letters + Numbers (a1b2)",
            "Numbers + Letters (12ab)",
            "Numbers only (1234)",
            "CamelCase (AbcDef)"
        ])
        row1.addWidget(self.pattern_combo)
        row1.addStretch()
        gen_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g. GD")
        self.prefix_input.setMaximumWidth(100)
        row2.addWidget(self.prefix_input)
        
        row2.addWidget(QLabel("Suffix:"))
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g. 2024")
        self.suffix_input.setMaximumWidth(100)
        row2.addWidget(self.suffix_input)
        
        gen_btn = QPushButton("🎲 Generate Usernames")
        gen_btn.clicked.connect(self.generate_usernames)
        gen_btn.setStyleSheet("background-color: #28a745; color: white; padding: 8px; font-weight: bold;")
        row2.addWidget(gen_btn)
        row2.addStretch()
        
        gen_layout.addLayout(row2)
        gen_group.setLayout(gen_layout)
        main_layout.addWidget(gen_group)

        # Input Section
        input_group = QGroupBox("Step 2: Enter Usernames to Check")
        input_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        input_layout = QVBoxLayout()
        
        input_info = QLabel("📝 Enter usernames (one per line):")
        input_layout.addWidget(input_info)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Username1\nUsername2\nUsername3\n...")
        self.input_text.setMaximumHeight(150)
        input_layout.addWidget(self.input_text)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Output Section
        output_group = QGroupBox("Step 3: Results")
        output_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: 'Courier New'; font-size: 10pt;")
        output_layout.addWidget(self.output_text)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶️ START CHECKING")
        self.start_button.clicked.connect(self.start_clicked)
        self.start_button.setStyleSheet("background-color: #ff6b35; color: white; font-weight: bold; padding: 15px; font-size: 14px;")
        btn_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ STOP")
        self.stop_button.clicked.connect(self.stop_clicked)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold; padding: 15px; font-size: 14px;")
        btn_layout.addWidget(self.stop_button)
        
        self.clear_button = QPushButton("🗑️ Clear Results")
        self.clear_button.clicked.connect(lambda: self.output_text.clear())
        self.clear_button.setStyleSheet("padding: 15px;")
        btn_layout.addWidget(self.clear_button)
        
        main_layout.addLayout(btn_layout)

        # Progress & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; height: 25px; } QProgressBar::chunk { background-color: #ff6b35; }")
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("✅ Ready - Enter usernames to check!")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #e0e0e0; border-radius: 3px;")
        main_layout.addWidget(self.status_label)

        self.debug_checkbox = QCheckBox("Debug mode (detailed logs)")
        main_layout.addWidget(self.debug_checkbox)

    def generate_usernames(self):
        try:
            length = int(self.length_input.text())
        except:
            length = 6
        
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()
        pattern = self.pattern_combo.currentText()
        
        try:
            count = int(self.count_input.text())
        except:
            count = 20

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
            
            elif pattern == "Numbers only (1234)":
                username = "".join(random.choice(string.digits) for _ in range(length))
            
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
            
            # GD usernames can contain letters, numbers, and underscores
            username = ''.join(c for c in username if c.isalnum() or c == '_')
            
            # GD username length is typically 3-15 characters
            if 3 <= len(username) <= 15:
                generated.append(username)

        existing = self.input_text.toPlainText().strip()
        all_users = ("\n".join(generated) if not existing else existing + "\n" + "\n".join(generated))
        self.input_text.setText(all_users)
        
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
                    "color": 16760576,
                    "footer": {
                        "text": "Geometry Dash Username Checker - Webhook Test"
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
            if u and (u.replace('_', '').isalnum()):
                usernames.append(u)
        return usernames

# ------------------- Run ------------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec_())
