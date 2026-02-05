import sys, requests, random, string, traceback, json
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QFont

# ------------------- Checker Thread ------------------- #
class SteamChecker(QThread):
    update = pyqtSignal(str)
    pupdate = pyqtSignal(int)
    count = 0

    def __init__(self, steam_ids, webhook_url=None, debug=False):
        super().__init__()
        self.steam_ids = steam_ids
        self.webhook_url = webhook_url
        self.running = True
        self.debug = debug

    def run(self):
        for i, steam_id in enumerate(self.steam_ids):
            if not self.running:
                break
            self.check_steam_id(steam_id)
            self.count += 1
            self.pupdate.emit(self.count)
            QThread.msleep(200)

    def stop(self):
        self.running = False

    def check_steam_id(self, steam_id):
        if not self.running:
            return

        try:
            steam_id = steam_id.strip()
            
            if self.debug:
                self.update.emit(f"\n{'='*60}")
                self.update.emit(f"[DEBUG] Checking: {steam_id}")
            
            # Handle both custom IDs and SteamID64
            if steam_id.isdigit() and len(steam_id) == 17:
                profile_url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
            else:
                profile_url = f"https://steamcommunity.com/id/{steam_id}/?xml=1"
            
            if self.debug:
                self.update.emit(f"[DEBUG] XML URL: {profile_url}")
            
            try:
                response = requests.get(profile_url, timeout=10)
                
                if self.debug:
                    self.update.emit(f"[DEBUG] Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    xml_text = response.text
                    
                    if "<e>" in xml_text.lower() or "the specified profile could not be found" in xml_text.lower():
                        self.update.emit(f"[AVAILABLE] {steam_id}")
                        
                        # Send to webhook when ID is available
                        if self.webhook_url:
                            self.send_to_discord(steam_id)
                        return
                    
                    # Profile exists - extract minimal information
                    persona_name = self.extract_xml_tag(xml_text, "steamID")
                    is_online = self.extract_xml_tag(xml_text, "onlineState")
                    
                    # Simple one-line output
                    result = f"[TAKEN] {steam_id} | Name: {persona_name} | Status: {is_online}"
                    self.update.emit(result)
                    
                    return
                
                elif response.status_code == 429:
                    self.update.emit(f"[RATE LIMIT] {steam_id}")
                    QThread.sleep(2)
                    
                elif response.status_code == 403:
                    self.update.emit(f"[PRIVATE] {steam_id}")
                    
                else:
                    self.update.emit(f"[ERROR] {steam_id}: HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                self.update.emit(f"[TIMEOUT] {steam_id}")
                
        except Exception as e:
            if self.debug:
                error_msg = traceback.format_exc()
                self.update.emit(f"[ERROR] {steam_id}:\n{error_msg}")
            else:
                error_msg = str(e)
                self.update.emit(f"[ERROR] {steam_id}: {error_msg}")

    def extract_xml_tag(self, xml_text, tag_name):
        try:
            start_tag = f"<{tag_name}>"
            end_tag = f"</{tag_name}>"
            
            start_idx = xml_text.find(start_tag)
            if start_idx == -1:
                start_tag = f"<{tag_name}><![CDATA["
                end_tag = f"]]></{tag_name}>"
                start_idx = xml_text.find(start_tag)
            
            if start_idx != -1:
                end_idx = xml_text.find(end_tag, start_idx)
                if end_idx != -1:
                    content = xml_text[start_idx + len(start_tag):end_idx]
                    return content.strip()
            return None
        except:
            return None

    def send_to_discord(self, steam_id):
        try:
            embed_data = {
                "title": "Available Steam ID Found!",
                "color": 65280,
                "fields": [
                    {
                        "name": "Available ID",
                        "value": f"`{steam_id}`",
                        "inline": True
                    },
                    {
                        "name": "Direct Link",
                        "value": f"https://steamcommunity.com/id/{steam_id}",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "Steam ID Checker"
                }
            }
            
            webhook_data = {"embeds": [embed_data]}
            
            response = requests.post(self.webhook_url, json=webhook_data, timeout=5)
            
            if response.status_code == 204:
                if self.debug:
                    self.update.emit(f"[DEBUG] Sent {steam_id} to Discord webhook")
            else:
                if self.debug:
                    self.update.emit(f"[DEBUG] Webhook failed: Status {response.status_code}")
                    
        except Exception as e:
            if self.debug:
                self.update.emit(f"[DEBUG] Webhook error: {str(e)}")

# ------------------- GUI App ------------------- #
class SteamCheckerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steam ID Checker")
        self.setGeometry(150, 150, 1100, 800)
        self.thread = None
        self.initUI()

    def initUI(self):
        wid = QWidget(self)
        self.setCentralWidget(wid)
        main_layout = QVBoxLayout()
        wid.setLayout(main_layout)

        # Title
        title = QLabel("Steam ID Checker")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("padding: 15px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1b2838, stop:1 #2a475e); color: white; border-radius: 5px;")
        main_layout.addWidget(title)

        # Info Section
        info_group = QGroupBox("About")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        info_layout = QVBoxLayout()
        
        instruction = QLabel(
            "Check Steam profiles using custom IDs (like 'skiesfr') or SteamID64 numbers.\n"
            "No API key required. Private profiles will show limited information."
        )
        instruction.setWordWrap(True)
        instruction.setStyleSheet("background-color: #e7f3ff; padding: 10px; border-radius: 3px; color: #004085;")
        info_layout.addWidget(instruction)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # Webhook Section
        webhook_group = QGroupBox("Discord Webhook (Optional)")
        webhook_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        webhook_layout = QVBoxLayout()
        
        webhook_input_layout = QHBoxLayout()
        self.webhook_input = QLineEdit()
        self.webhook_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        webhook_input_layout.addWidget(self.webhook_input)
        
        test_webhook_btn = QPushButton("Test")
        test_webhook_btn.setMaximumWidth(80)
        test_webhook_btn.clicked.connect(self.test_webhook)
        webhook_input_layout.addWidget(test_webhook_btn)
        
        webhook_layout.addLayout(webhook_input_layout)
        webhook_group.setLayout(webhook_layout)
        main_layout.addWidget(webhook_group)

        # Generator Section
        gen_group = QGroupBox("Step 1: Generate Random Custom IDs (Optional)")
        gen_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        gen_layout = QVBoxLayout()
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Length:"))
        self.length_input = QLineEdit("6")
        self.length_input.setMaximumWidth(80)
        row1.addWidget(self.length_input)
        
        row1.addWidget(QLabel("Count:"))
        self.count_input = QLineEdit("20")
        self.count_input.setMaximumWidth(80)
        row1.addWidget(self.count_input)
        
        row1.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Letters only (abc)",
            "Letters + Numbers (a1b2)",
            "Numbers + Letters (12ab)",
            "Numbers only (1234)",
            "Letters_Letters (abc_def)",
            "CamelCase (AbcDef)"
        ])
        row1.addWidget(self.pattern_combo)
        row1.addStretch()
        gen_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("e.g., pro_")
        self.prefix_input.setMaximumWidth(150)
        row2.addWidget(self.prefix_input)
        
        row2.addWidget(QLabel("Suffix:"))
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("e.g., _2024")
        self.suffix_input.setMaximumWidth(150)
        row2.addWidget(self.suffix_input)
        
        gen_btn = QPushButton("Generate")
        gen_btn.clicked.connect(self.generate_ids)
        gen_btn.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 8px;")
        row2.addWidget(gen_btn)
        row2.addStretch()
        gen_layout.addLayout(row2)
        
        gen_group.setLayout(gen_layout)
        main_layout.addWidget(gen_group)

        # Input Section
        input_group = QGroupBox("Step 2: Enter Steam IDs to Check (One Per Line)")
        input_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        input_layout = QVBoxLayout()
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("skiesfr\ngaben\nrobinwalker\n76561197960265728\n...")
        self.input_text.setMaximumHeight(150)
        input_layout.addWidget(self.input_text)
        
        input_buttons = QHBoxLayout()
        
        load_btn = QPushButton("Load from File")
        load_btn.clicked.connect(self.load_from_file)
        input_buttons.addWidget(load_btn)
        
        save_btn = QPushButton("Save to File")
        save_btn.clicked.connect(self.save_to_file)
        input_buttons.addWidget(save_btn)
        
        clear_input_btn = QPushButton("Clear Input")
        clear_input_btn.clicked.connect(lambda: self.input_text.clear())
        input_buttons.addWidget(clear_input_btn)
        
        input_layout.addLayout(input_buttons)
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Output Section
        output_group = QGroupBox("Results")
        output_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("font-family: 'Courier New'; background-color: #000000; color: #00ff00;")
        output_layout.addWidget(self.output_text)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.start_button = QPushButton("START CHECKING")
        self.start_button.clicked.connect(self.start_clicked)
        self.start_button.setStyleSheet("background-color: #00cc99; color: white; font-weight: bold; padding: 15px; font-size: 14px;")
        btn_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("STOP")
        self.stop_button.clicked.connect(self.stop_clicked)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold; padding: 15px; font-size: 14px;")
        btn_layout.addWidget(self.stop_button)
        
        self.clear_button = QPushButton("Clear Results")
        self.clear_button.clicked.connect(lambda: self.output_text.clear())
        self.clear_button.setStyleSheet("padding: 15px;")
        btn_layout.addWidget(self.clear_button)
        
        main_layout.addLayout(btn_layout)

        # Progress & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; height: 25px; } QProgressBar::chunk { background-color: #1b2838; }")
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #e0e0e0; border-radius: 3px;")
        main_layout.addWidget(self.status_label)

        self.debug_checkbox = QCheckBox("Debug mode (detailed logs)")
        main_layout.addWidget(self.debug_checkbox)

    def generate_ids(self):
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
            
            if username:
                generated.append(username)

        existing = self.input_text.toPlainText().strip()
        all_users = ("\n".join(generated) if not existing else existing + "\n" + "\n".join(generated))
        self.input_text.setText(all_users)
        
        self.status_label.setText(f"Generated {len(generated)} IDs")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #c8e6c9; border-radius: 3px;")

    def load_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Steam IDs", "", "Text Files (*.txt);;All Files (*)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                self.input_text.setText(content)
                self.status_label.setText(f"Loaded from {filename}")
                self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #c8e6c9; border-radius: 3px;")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")

    def save_to_file(self):
        content = self.input_text.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "No Content", "No Steam IDs to save!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(self, "Save Steam IDs", "", "Text Files (*.txt);;All Files (*)")
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(content)
                self.status_label.setText(f"Saved to {filename}")
                self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #c8e6c9; border-radius: 3px;")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

    def test_webhook(self):
        webhook_url = self.webhook_input.text().strip()
        
        if not webhook_url:
            QMessageBox.warning(self, "No Webhook", "Please enter a webhook URL first!")
            return
        
        try:
            test_data = {
                "embeds": [{
                    "title": "Test Message",
                    "description": "Your webhook is working correctly!",
                    "color": 1752220,
                    "footer": {
                        "text": "Steam ID Checker - Webhook Test"
                    }
                }]
            }
            
            response = requests.post(webhook_url, json=test_data, timeout=5)
            
            if response.status_code == 204:
                QMessageBox.information(self, "Success", "Webhook test successful!\nCheck your Discord channel.")
            else:
                QMessageBox.warning(self, "Failed", f"Webhook test failed!\nStatus code: {response.status_code}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send test message:\n{str(e)}")

    def start_clicked(self):
        steam_ids = self.get_steam_ids()
        if not steam_ids:
            QMessageBox.warning(self, "No Steam IDs", "Please enter Steam IDs to check!")
            return
        
        debug = self.debug_checkbox.isChecked()
        webhook_url = self.webhook_input.text().strip() or None
        
        self.progress_bar.setMaximum(len(steam_ids))
        self.progress_bar.setValue(0)
        self.output_text.clear()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        self.status_label.setText(f"Checking {len(steam_ids)} Steam IDs...")
        self.status_label.setStyleSheet("padding: 8px; font-weight: bold; background-color: #fff9c4; border-radius: 3px;")

        self.thread = SteamChecker(steam_ids, webhook_url, debug)
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
        self.status_label.setText("Checking complete!")
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
        self.status_label.setText(f"Progress: {value}/{total} ({percent}%)")

    def get_steam_ids(self):
        txt = self.input_text.toPlainText().strip()
        steam_ids = []
        for line in txt.splitlines():
            sid = line.strip()
            if sid:
                steam_ids.append(sid)
        return steam_ids

# ------------------- Run ------------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SteamCheckerApp()
    w.show()
    sys.exit(app.exec_())
