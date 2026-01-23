"""
TikTok Username Auto-Claimer - Selenium Browser Automation
This uses a real browser to avoid API restrictions

Requirements:
pip install selenium webdriver-manager

Note: You'll need Chrome installed on your system
"""

import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class TikTokSeleniumClaimer:
    def __init__(self, headless=False, check_interval=5, max_retries=3):
        self.headless = headless
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.driver = None
        self.current_username = None
        self.claimed = False
        self.retry_counts = {}
        
    def setup_driver(self):
        """Initialize Chrome driver with appropriate options"""
        print("🌐 Setting up Chrome browser...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
            print("   🕶️ Running in headless mode")
        else:
            print("   👁️ Running in visible mode (you can watch it work!)")
        
        # Anti-detection options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Keep browser open on errors
        chrome_options.add_experimental_option("detach", True)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Remove webdriver flag
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("   ✅ Browser ready!")
            return True
        except Exception as e:
            print(f"   ❌ Error setting up browser: {e}")
            return False
    
    def login_with_cookies(self, cookies_file):
        """Load cookies from JSON file to login"""
        import json
        
        print("\n🔑 Loading session from cookies...")
        
        try:
            # First, visit TikTok to set the domain
            self.driver.get("https://www.tiktok.com")
            time.sleep(2)
            
            # Load cookies
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)
            
            print(f"   📦 Loading {len(cookies)} cookies...")
            
            for cookie in cookies:
                try:
                    # Prepare cookie for Selenium
                    cookie_dict = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.tiktok.com'),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', False),
                    }
                    
                    # Add expiry if present
                    if 'expirationDate' in cookie and cookie['expirationDate']:
                        cookie_dict['expiry'] = int(cookie['expirationDate'])
                    
                    self.driver.add_cookie(cookie_dict)
                except Exception as e:
                    # Skip cookies that fail (some may be incompatible)
                    continue
            
            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(3)
            
            print("   ✅ Cookies loaded!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error loading cookies: {e}")
            return False
    
    def manual_login(self):
        """Wait for user to login manually"""
        print("\n🔐 Manual Login Required")
        print("="*60)
        print("Please login to TikTok in the browser window that opened.")
        print("You can login using:")
        print("  • QR Code")
        print("  • Phone/Email/Username")
        print("  • Social media accounts")
        print("\nOnce logged in, press Enter here to continue...")
        print("="*60)
        
        try:
            self.driver.get("https://www.tiktok.com/login")
            input("\n⏸️  Press Enter after you've logged in: ")
            
            # Verify login
            time.sleep(2)
            return self.verify_logged_in()
            
        except Exception as e:
            print(f"❌ Error during manual login: {e}")
            return False
    
    def verify_logged_in(self):
        """Check if user is logged in"""
        print("\n🔍 Verifying login status...")
        
        try:
            self.driver.get("https://www.tiktok.com/setting")
            time.sleep(3)
            
            # Check if we're redirected to login page
            if "login" in self.driver.current_url:
                print("   ❌ Not logged in - redirected to login page")
                return False
            
            # Look for profile/settings elements
            page_source = self.driver.page_source
            
            if "uniqueId" in page_source or "Edit profile" in page_source:
                print("   ✅ Login verified!")
                return True
            else:
                print("   ⚠️ Login status uncertain")
                return False
                
        except Exception as e:
            print(f"   ❌ Error verifying login: {e}")
            return False
    
    def get_current_username(self):
        """Get current username from settings page"""
        print("\n📋 Fetching current username...")
        
        try:
            self.driver.get("https://www.tiktok.com/setting")
            time.sleep(3)
            
            # Method 1: Look in page source
            page_source = self.driver.page_source
            
            patterns = [
                r'"uniqueId"\s*:\s*"([a-zA-Z0-9_\.]{2,})"',
                r'@([a-zA-Z0-9_\.]{2,})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source)
                if matches:
                    # Filter out false positives
                    valid = [m for m in matches if m.lower() not in ['tiktok', 'user', 'profile', 'settings']]
                    if valid:
                        username = max(valid, key=len).lower()
                        print(f"   ✅ Current username: @{username}")
                        return username
            
            # Method 2: Try to find username input field
            try:
                username_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text'][placeholder*='sername']")
                username = username_input.get_attribute('value')
                if username:
                    print(f"   ✅ Found in input field: @{username}")
                    return username.lower()
            except:
                pass
            
            print("   ⚠️ Could not detect username")
            return None
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def check_username_availability(self, username):
        """Check if username is available"""
        print(f"\n🔍 Checking if @{username} is available...")
        
        try:
            # Visit the profile page
            self.driver.get(f"https://www.tiktok.com/@{username}")
            time.sleep(2)
            
            page_source = self.driver.page_source.lower()
            
            # Check for "couldn't find this account" or similar
            not_found_indicators = [
                "couldn't find this account",
                "account not found",
                "page not available",
                "this account doesn't exist",
            ]
            
            for indicator in not_found_indicators:
                if indicator in page_source:
                    print(f"   ✅ Username appears to be available!")
                    return True, "Available"
            
            # If we can see user content, it's taken
            if "video" in page_source or "followers" in page_source:
                print(f"   ❌ Username is taken")
                return False, "Username is already taken"
            
            print(f"   ⚠️ Status unclear - attempting claim anyway")
            return True, "Status uncertain"
            
        except Exception as e:
            print(f"   ⚠️ Error checking: {e}")
            return True, "Check failed - attempting claim"
    
    def navigate_to_edit_profile(self):
        """Navigate to the edit profile modal"""
        try:
            # First get current username if not set
            if not self.current_username:
                print("   🔍 Getting current username first...")
                self.current_username = self.get_current_username()
                if not self.current_username:
                    print("   ⚠️ Could not get current username, going to main profile page")
                    self.driver.get("https://www.tiktok.com")
                    time.sleep(3)
            
            if self.current_username:
                # Go directly to profile
                profile_url = f"https://www.tiktok.com/@{self.current_username}"
                print(f"   🔗 Going to profile: {profile_url}")
                self.driver.get(profile_url)
                time.sleep(3)
            else:
                # Go to main page
                self.driver.get("https://www.tiktok.com")
                time.sleep(3)
            
            # Now look for "Edit profile" button
            print("   🔍 Looking for 'Edit profile' button...")
            
            edit_button_selectors = [
                "button[data-e2e='edit-profile-entrance']",
                "//button[@data-e2e='edit-profile-entrance']",
                "//button[contains(@class, 'TUXButton') and contains(., 'Edit profile')]",
                "button[aria-haspopup='dialog'][aria-expanded='false']",
                "//button[contains(text(), 'Edit profile')]",
                "//a[contains(text(), 'Edit profile')]",
            ]
            
            edit_button = None
            
            for selector in edit_button_selectors:
                try:
                    if selector.startswith('//'):
                        edit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        edit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    if edit_button:
                        print(f"   ✅ Found 'Edit profile' button!")
                        break
                except:
                    continue
            
            if not edit_button:
                print("   ⚠️ Could not find 'Edit profile' button automatically")
                return False
            
            # Click the edit button
            print("   🖱️ Clicking 'Edit profile'...")
            edit_button.click()
            time.sleep(3)
            
            print("   ✅ Edit profile modal opened!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error navigating: {e}")
            return False
    
    def claim_username(self, username, skip_availability_check=False):
        """Attempt to claim a username"""
        username = username.replace('@', '').strip().lower()
        
        print(f"\n{'='*60}")
        print(f"🎯 Attempting to claim: @{username}")
        print(f"{'='*60}")
        
        # Check if already this username
        if self.current_username == username:
            return True, f"Already using @{username}"
        
        # Check availability (skip if in manual mode)
        if not skip_availability_check:
            available, msg = self.check_username_availability(username)
            if not available:
                return False, msg
        else:
            print("\n⏭️ Skipping availability check (manual mode)")
        
        # Navigate to edit profile
        if not self.navigate_to_edit_profile():
            return False, "Failed to navigate to edit profile"
        
        try:
            print("\n📝 Looking for username input field...")
            
            # Wait a bit for the edit profile modal/page to load
            time.sleep(2)
            
            # Try multiple selectors for the username input
            username_selectors = [
                "input[placeholder*='sername']",
                "input[placeholder*='Username']",
                "input[name='uniqueId']",
                "input[name='username']",
                "//input[contains(@placeholder, 'sername')]",
                "//input[contains(@placeholder, 'Username')]",
                "//label[contains(text(), 'Username')]/..//input",
                "//div[contains(text(), 'Username')]/..//input",
            ]
            
            username_input = None
            
            for selector in username_selectors:
                try:
                    if selector.startswith('//'):
                        # XPath selector
                        username_input = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                    else:
                        # CSS selector
                        username_input = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    
                    if username_input and username_input.is_displayed():
                        print(f"   ✅ Found username input field!")
                        break
                    else:
                        username_input = None
                except:
                    continue
            
            if not username_input:
                print("   ⚠️ Could not find username input field automatically")
                print("\n🔧 MANUAL INTERVENTION NEEDED:")
                print("="*60)
                print(f"1. In the Edit Profile page that's open")
                print(f"2. Find the 'Username' field (should be the first field)")
                print(f"3. Clear it and enter: {username}")
                print(f"4. Click the 'Save' button")
                print(f"5. Handle any CAPTCHA if it appears")
                print("="*60)
                input("\nPress Enter after you've manually changed the username...")
                
                # Verify if change was successful
                time.sleep(2)
                new_username = self.get_current_username()
                if new_username == username:
                    self.current_username = username
                    return True, "Successfully claimed (manual intervention)"
                else:
                    return False, "Manual intervention did not succeed"
            
            # Clear the input completely and enter new username
            print(f"   ✏️ Clearing current username...")
            username_input.click()
            time.sleep(0.5)
            
            # Try multiple methods to clear the field
            # Method 1: Select all and delete
            from selenium.webdriver.common.keys import Keys
            username_input.send_keys(Keys.CONTROL + 'a')  # For Windows/Linux
            username_input.send_keys(Keys.COMMAND + 'a')  # For Mac
            time.sleep(0.3)
            username_input.send_keys(Keys.DELETE)
            time.sleep(0.3)
            username_input.send_keys(Keys.BACKSPACE)
            time.sleep(0.3)
            
            # Method 2: Clear using Selenium's clear() method
            username_input.clear()
            time.sleep(0.5)
            
            # Method 3: Manual backspace clearing
            current_value = username_input.get_attribute('value')
            for _ in range(len(current_value)):
                username_input.send_keys(Keys.BACKSPACE)
                time.sleep(0.05)
            
            time.sleep(0.5)
            
            print(f"   ✏️ Entering new username: @{username}")
            username_input.send_keys(username)
            time.sleep(2)
            
            # Wait 3 seconds and check for instant validation errors
            print("   ⏳ Waiting for validation...")
            time.sleep(3)
            
            # Check for error messages that appear while typing
            print("   🔍 Checking for validation errors...")
            try:
                error_selectors = [
                    "//p[contains(@class, 'PInputError')]",
                    "//p[contains(@class, 'InputError')]",
                    "//p[contains(@class, 'error')]",
                    "//div[contains(@class, 'error-message')]",
                    "//span[contains(@class, 'error')]",
                    "p[class*='InputError']",
                    "p[class*='error']",
                    "div[class*='error']",
                ]
                
                validation_error = False
                error_text = None
                
                for selector in error_selectors:
                    try:
                        if selector.startswith('//'):
                            error_element = self.driver.find_element(By.XPATH, selector)
                        else:
                            error_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if error_element and error_element.is_displayed():
                            error_text = error_element.text
                            # Check if it's actually about username availability
                            if error_text and ("isn't available" in error_text.lower() or 
                                             "not available" in error_text.lower() or 
                                             "already taken" in error_text.lower() or
                                             "already claimed" in error_text.lower() or
                                             "can't use" in error_text.lower()):
                                validation_error = True
                                print(f"   ❌ Validation error: {error_text}")
                                break
                    except:
                        continue
                
                if validation_error:
                    print("   🔄 Username not available - closing modal...")
                    # Close the modal
                    from selenium.webdriver.common.keys import Keys
                    try:
                        close_selectors = [
                            "button[aria-label='Close']",
                            "//button[@aria-label='Close']",
                            "//button[contains(@class, 'close')]",
                        ]
                        
                        close_button = None
                        for selector in close_selectors:
                            try:
                                if selector.startswith('//'):
                                    close_button = self.driver.find_element(By.XPATH, selector)
                                else:
                                    close_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                
                                if close_button and close_button.is_displayed():
                                    close_button.click()
                                    print("   ✅ Closed edit profile modal")
                                    time.sleep(2)
                                    break
                            except:
                                continue
                        
                        if not close_button:
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            print("   ✅ Pressed Escape to close modal")
                            time.sleep(2)
                    except:
                        self.driver.get(f"https://www.tiktok.com/@{self.current_username}")
                        time.sleep(2)
                    
                    return False, f"❌ Username validation failed - {error_text or 'not available'}"
            
            except Exception as e:
                print(f"   ⚠️ Error checking validation: {e}")
            
            # Look for save/submit button
            print("   🔍 Looking for 'Save' button...")
            
            button_selectors = [
                "//button[contains(text(), 'Save')]",
                "//button[contains(text(), 'save')]",
                "//button[@type='submit']",
                "button[type='submit']",
                "//button[contains(@class, 'save')]",
                "//div[contains(@role, 'button') and contains(text(), 'Save')]",
            ]
            
            save_button = None
            
            for selector in button_selectors:
                try:
                    if selector.startswith('//'):
                        save_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        save_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    if save_button and save_button.is_displayed():
                        print(f"   ✅ Found 'Save' button!")
                        break
                    else:
                        save_button = None
                except:
                    continue
            
            # If no save button found, check if there's an error message
            if not save_button:
                print("   ⚠️ Could not find 'Save' button - checking for errors...")
                
                try:
                    # Check page source for error messages
                    page_source = self.driver.page_source.lower()
                    
                    error_keywords = [
                        "isn't available",
                        "not available", 
                        "already taken",
                        "already claimed",
                        "can't use this username",
                        "username is taken"
                    ]
                    
                    error_found = False
                    for keyword in error_keywords:
                        if keyword in page_source:
                            error_found = True
                            print(f"   ❌ Error detected: {keyword}")
                            break
                    
                    if error_found:
                        print("   🔄 Closing modal...")
                        from selenium.webdriver.common.keys import Keys
                        try:
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(2)
                        except:
                            self.driver.get(f"https://www.tiktok.com/@{self.current_username}")
                            time.sleep(2)
                        
                        return False, f"❌ Username is not available or already claimed"
                
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")
                
                print("   ⚠️ Please manually click the 'Save' button in the browser")
                input("Press Enter after clicking 'Save'...")
                
                time.sleep(3)
                new_username = self.get_current_username()
                if new_username == username:
                    self.current_username = username
                    return True, "✅ Successfully claimed (manual save)"
                else:
                    return False, "⚠️ Manual save did not succeed"
            
            if save_button:
                print("   🖱️ Clicking 'Save' button...")
                save_button.click()
                time.sleep(3)
                
                # Check for immediate error messages (auto-moderated/reserved usernames)
                print("   🔍 Checking for instant errors...")
                time.sleep(2)
                
                try:
                    # Look for the specific error message about username not being available
                    error_selectors = [
                        "//p[contains(@class, 'PInputError') and contains(text(), \"isn't available\")]",
                        "//p[contains(@class, 'error') and contains(text(), \"isn't available\")]",
                        "//div[contains(@class, 'error') and contains(text(), \"isn't available\")]",
                        "//span[contains(text(), \"isn't available\")]",
                        "p[class*='InputError']",
                        "div[class*='error-message']",
                    ]
                    
                    error_found = False
                    error_message = None
                    
                    for selector in error_selectors:
                        try:
                            if selector.startswith('//'):
                                error_element = self.driver.find_element(By.XPATH, selector)
                            else:
                                error_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            
                            if error_element and error_element.is_displayed():
                                error_message = error_element.text
                                error_found = True
                                print(f"   ❌ Error detected: {error_message}")
                                break
                        except:
                            continue
                    
                    # Also check page source for error keywords
                    if not error_found:
                        page_source = self.driver.page_source.lower()
                        if "isn't available" in page_source or "username isn't available" in page_source:
                            error_found = True
                            error_message = "Username isn't available (auto-moderated or reserved)"
                            print(f"   ❌ {error_message}")
                    
                    if error_found:
                        print("   🔄 Closing edit profile modal...")
                        # Try to close the modal by pressing Escape key
                        from selenium.webdriver.common.keys import Keys
                        try:
                            # Try to find and click a close button first
                            close_selectors = [
                                "button[aria-label='Close']",
                                "//button[@aria-label='Close']",
                                "//button[contains(@class, 'close')]",
                                "svg[class*='close']",
                            ]
                            
                            close_button = None
                            for selector in close_selectors:
                                try:
                                    if selector.startswith('//'):
                                        close_button = self.driver.find_element(By.XPATH, selector)
                                    else:
                                        close_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    
                                    if close_button and close_button.is_displayed():
                                        close_button.click()
                                        print("   ✅ Closed edit profile modal")
                                        time.sleep(2)
                                        break
                                except:
                                    continue
                            
                            # If no close button found, press Escape
                            if not close_button:
                                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                print("   ✅ Pressed Escape to close modal")
                                time.sleep(2)
                        except:
                            # Last resort: navigate back to profile
                            print("   🔄 Navigating back to profile...")
                            self.driver.get(f"https://www.tiktok.com/@{self.current_username}")
                            time.sleep(2)
                        
                        return False, f"❌ Username is auto-moderated or reserved - {error_message or 'not available'}"
                
                except Exception as e:
                    print(f"   ⚠️ Error checking for error messages: {e}")
                
                # Check for the 30-day confirmation dialog
                print("   🔍 Checking for confirmation dialog...")
                page_source = self.driver.page_source.lower()
                
                if "30 days" in page_source or "can't change" in page_source or "one month" in page_source:
                    print("   ⚠️ TikTok is showing the 30-day warning dialog")
                    
                    # Look for the second confirm button
                    confirm_selectors = [
                        "//button[contains(text(), 'Confirm')]",
                        "//button[contains(text(), 'confirm')]",
                        "//button[contains(@class, 'confirm')]",
                        "button[data-e2e='confirm']",
                        "//div[contains(@role, 'button') and contains(text(), 'Confirm')]",
                    ]
                    
                    second_confirm = None
                    
                    for selector in confirm_selectors:
                        try:
                            if selector.startswith('//'):
                                second_confirm = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                            else:
                                second_confirm = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                            
                            if second_confirm and second_confirm.is_displayed():
                                print(f"   ✅ Found confirmation button!")
                                break
                            else:
                                second_confirm = None
                        except:
                            continue
                    
                    if second_confirm:
                        print("   🖱️ Clicking 'Confirm' button on warning dialog...")
                        second_confirm.click()
                        time.sleep(4)
                    else:
                        print("   ⚠️ Could not find confirm button, may need manual click")
                        input("   If you see a confirmation dialog, click 'Confirm', then press Enter...")
                
                # Wait for the modal to close and page to update
                print("   ⏳ Waiting for changes to apply...")
                time.sleep(5)
                
                # Check if we're back on the profile page (modal closed)
                current_url = self.driver.current_url
                if f"@{username}" not in current_url:
                    # Navigate to the new profile to force refresh
                    print(f"   🔄 Refreshing profile page...")
                    self.driver.get(f"https://www.tiktok.com/@{username}")
                    time.sleep(3)
                else:
                    # Just refresh the current page
                    self.driver.refresh()
                    time.sleep(3)
                
                # Now check for actual CAPTCHA (only look for real CAPTCHA indicators)
                page_source = self.driver.page_source.lower()
                
                # Be more specific about CAPTCHA detection - avoid false positives
                is_captcha = False
                captcha_indicators = ["geetest", "recaptcha", "hcaptcha", "captcha-verify", "puzzle-captcha"]
                
                for indicator in captcha_indicators:
                    if indicator in page_source:
                        is_captcha = True
                        break
                
                # Also check for specific verify elements
                if not is_captcha:
                    try:
                        # Look for actual CAPTCHA iframes or elements
                        captcha_elements = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='captcha'], div[class*='captcha'], canvas[class*='captcha']")
                        if captcha_elements:
                            is_captcha = True
                    except:
                        pass
                
                if is_captcha:
                    print("\n🤖 ACTUAL CAPTCHA DETECTED!")
                    print("="*60)
                    print("Please solve the CAPTCHA in the browser window")
                    print("="*60)
                    input("Press Enter after solving the CAPTCHA...")
                    time.sleep(2)
                
                # Verify the change by getting current username
                print("   🔍 Verifying username change...")
                time.sleep(2)
                new_username = self.get_current_username()
                
                if new_username == username:
                    self.current_username = username
                    return True, f"✅ Successfully claimed @{username}!"
                elif new_username == self.current_username:
                    # Check if there was an error by looking at the page
                    page_source = self.driver.page_source.lower()
                    
                    if "cooldown" in page_source or "recently changed" in page_source:
                        return False, "⏰ 30-day cooldown is active - you recently changed your username"
                    elif "taken" in page_source or "not available" in page_source or "already in use" in page_source:
                        return False, "❌ Username is already taken or not available"
                    else:
                        return False, f"⚠️ Username change failed - still showing as @{new_username}"
                else:
                    return False, f"⚠️ Unexpected username: @{new_username}"
            else:
                print("   ⚠️ Could not find 'Save' button automatically")
                print("\n🔧 Please manually click the 'Save' button in the browser")
                input("Press Enter after clicking 'Save'...")
                
                time.sleep(3)
                new_username = self.get_current_username()
                if new_username == username:
                    self.current_username = username
                    return True, "✅ Successfully claimed (manual save)"
                else:
                    return False, "⚠️ Manual save did not succeed"
                
        except Exception as e:
            print(f"   ❌ Error during claim: {e}")
            return False, f"Error: {str(e)[:100]}"
        
        # Step 6: Find and click Save button
        print("\n📍 Step 6: Looking for Save button...")
        try:
            # Wait a moment for the Save button to become active
            time.sleep(1)
            
            # Try multiple selectors for Save button
            save_button = None
            selectors = [
                "button:has-text('Save')",
                "button[type='submit']",
                "button.save-button",
                "button[data-e2e='save-button']",
            ]
            
            for selector in selectors:
                try:
                    save_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if save_button and save_button.is_enabled():
                        break
                except:
                    continue
            
            # If still not found, look for any button with "Save" text
            if not save_button:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "save" in btn.text.lower():
                        save_button = btn
                        break
            
            if not save_button:
                return False, "Could not find Save button"
            
            if not save_button.is_enabled():
                return False, "Save button is disabled (username might be invalid)"
            
            print("   ✅ Found Save button, clicking...")
            save_button.click()
            
        except Exception as e:
            return False, f"Error clicking Save: {e}"
        
        # Step 7: Wait and check for success/error messages
        print("\n📍 Step 7: Waiting for response...")
        time.sleep(3)
        
        try:
            page_source = self.driver.page_source.lower()
            
            # Check for error messages
            error_patterns = [
                ("auto-moderated", "⛔ Username was auto-moderated by TikTok"),
                ("reserved", "⛔ Username is reserved by TikTok"),
                ("already taken", "❌ Username is already taken"),
                ("not available", "❌ Username is not available"),
                ("invalid", "❌ Username format is invalid"),
                ("cooldown", "⏰ Username change on cooldown"),
                ("wait", "⏰ Please wait before changing username again"),
            ]
            
            for pattern, message in error_patterns:
                if pattern in page_source:
                    return False, message
            
            # If no errors found, assume success
            # Verify by checking the settings page
            time.sleep(2)
            self.driver.get("https://www.tiktok.com/setting")
            time.sleep(3)
            
            current = self.get_current_username()
            
            if current and current.lower() == username.lower():
                self.current_username = username
                return True, f"✅ Successfully claimed @{username}!"
            else:
                # Check for modal/popup indicating auto-moderation
                try:
                    modal_text = self.driver.find_element(By.CSS_SELECTOR, "div[role='dialog']").text.lower()
                    if "auto-moderat" in modal_text or "offensive" in modal_text:
                        # Close the modal
                        try:
                            close_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']")
                            close_btn.click()
                            time.sleep(1)
                        except:
                            pass
                        return False, "⛔ Username was auto-moderated by TikTok"
                except:
                    pass
                
                return False, f"⚠️ Username change uncertain. Current: @{current if current else 'unknown'}"
            
        except Exception as e:
            return False, f"Error checking result: {e}"
    
    def manual_mode(self):
        """Interactive mode - enter usernames manually"""
        print("\n" + "="*60)
        print("✋ Manual Mode")
        print("="*60)
        print("Commands:")
        print("  • Just type a username to claim it (e.g., 'coolname')")
        print("  • 'check @username' - Check if available without claiming")
        print("  • 'current' - Show current username")
        print("  • 'quit' - Exit")
        print("\n💡 In manual mode, the script will try to claim immediately")
        print("   without checking availability first (faster!).")
        print("   If TikTok auto-moderates it, you'll see a modal popup and")
        print("         the script will automatically close the modal")
        print("         and wait for your next username!\n")
        
        while not self.claimed:
            try:
                cmd = input(">>> ").strip()
                
                if cmd.lower() == 'quit':
                    break
                elif cmd.lower() == 'current':
                    username = self.get_current_username()
                    if username:
                        self.current_username = username
                elif cmd.lower().startswith('check '):
                    username = cmd.split(' ', 1)[1].strip().replace('@', '')
                    self.check_username_availability(username)
                elif cmd:
                    username = cmd.replace('@', '')
                    # Skip availability check in manual mode (skip_availability_check=True)
                    success, message = self.claim_username(username, skip_availability_check=True)
                    
                    print(f"\n{message}")
                    
                    if success:
                        print(f"🔗 Verify at: https://www.tiktok.com/@{username}\n")
                        break
                    else:
                        # If it failed due to auto-moderation, just continue to next username
                        if "auto-moderated" in message or "reserved" in message or "isn't available" in message:
                            print("⏭️ Ready for next username...\n")
                        else:
                            print()
                        
            except KeyboardInterrupt:
                print("\n\n👋 Stopped")
                break
    
    def monitor_discord_bot_mode(self, channel_id, bot_token):
        """Monitor Discord channel using bot token for available usernames"""
        import requests
        
        print("\n" + "="*60)
        print("👀 TikTok Username Claimer - Discord Bot Monitor Mode")
        print("="*60)
        print(f"📡 Monitoring channel: {channel_id}")
        print(f"⏱️ Check interval: {self.check_interval}s")
        print("💡 Auto-moderated usernames will be skipped automatically")
        print("🛑 Press Ctrl+C to stop\n")
        
        # Get the current latest message ID to ignore old messages
        print("🔍 Getting current messages (will ignore these old ones)...")
        seen_messages = set()
        
        headers = {'Authorization': f'Bot {bot_token}'}
        channel_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        
        try:
            response = requests.get(f"{channel_url}?limit=100", headers=headers, timeout=10)
            if response.status_code == 200:
                old_messages = response.json()
                # Mark all current messages as seen
                for msg in old_messages:
                    seen_messages.add(msg['id'])
                print(f"   ✅ Marked {len(seen_messages)} existing messages as seen (will be ignored)")
            else:
                print(f"   ⚠️ Could not fetch old messages (HTTP {response.status_code})")
                if response.status_code == 401:
                    print("   ❌ Invalid bot token")
                    return
                elif response.status_code == 403:
                    print("   ❌ Bot doesn't have access to this channel")
                    return
                print("   Will process any messages found...")
        except Exception as e:
            print(f"   ⚠️ Error getting old messages: {e}")
            print("   Will process any messages found...")
        
        print("\n✅ Monitoring started! Send a message with @username now...\n")
        
        check_count = 0
        
        while not self.claimed:
            try:
                check_count += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"[{current_time}] 🔄 Check #{check_count}: Fetching messages...", end="", flush=True)
                
                # Get recent messages
                response = requests.get(f"{channel_url}?limit=10", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    messages = response.json()
                    print(f" ✅ Got {len(messages)} messages", end="")
                    
                    new_message_found = False
                    
                    # Process messages in chronological order (oldest first)
                    for message in reversed(messages):
                        msg_id = message['id']
                        
                        # Skip if we've already seen this message
                        if msg_id in seen_messages:
                            continue
                        
                        # Mark as seen
                        seen_messages.add(msg_id)
                        new_message_found = True
                        
                        # Extract username - check both content and embeds
                        content = message.get('content', '')
                        
                        # Check embeds for username (webhook messages often use embeds)
                        if not content or content.strip() == '':
                            embeds = message.get('embeds', [])
                            for embed in embeds:
                                # Check title
                                if 'title' in embed:
                                    content += ' ' + embed['title']
                                # Check description
                                if 'description' in embed:
                                    content += ' ' + embed['description']
                                # Check fields
                                if 'fields' in embed:
                                    for field in embed['fields']:
                                        if 'value' in field:
                                            content += ' ' + field['value']
                        
                        # Look for @username in the message
                        username_match = re.search(r'@([a-zA-Z0-9_\.]+)', content)
                        
                        if username_match:
                            username = username_match.group(1)
                            print(f"\n\n{'='*60}")
                            print(f"🆕 NEW MESSAGE DETECTED!")
                            print(f"{'='*60}")
                            print(f"Username: @{username}")
                            print(f"Message content: {content[:100]}")
                            print(f"{'='*60}\n")
                            
                            # In monitor mode, SKIP availability check and go straight to claiming
                            success, msg = self.claim_username(username, skip_availability_check=True)
                            
                            if success:
                                print(f"\n🎉 {msg}")
                                print(f"🔗 Profile: https://www.tiktok.com/@{username}")
                                self.claimed = True
                                return
                            else:
                                print(f"\n❌ {msg}")
                                
                                # If auto-moderated, continue monitoring
                                if "auto-moderated" in msg or "reserved" in msg or "isn't available" in msg:
                                    print("⏭️ Continuing to monitor for next username...\n")
                                # If it's a cooldown error, stop monitoring
                                elif "cooldown" in msg.lower() or "wait" in msg.lower():
                                    print("⏰ Cooldown active - stopping monitor mode")
                                    return
                        else:
                            print(f"\n   ℹ️ New message but no @username found")
                            print(f"      Content: '{content[:100]}'")
                            print(f"      Embeds: {len(message.get('embeds', []))}")
                    
                    # If no new messages
                    if not new_message_found:
                        print(f" - No new messages")
                else:
                    print(f" ❌ HTTP {response.status_code}")
                    if response.status_code == 401:
                        print("   ❌ Invalid bot token")
                        break
                    elif response.status_code == 403:
                        print("   ❌ Bot doesn't have access to this channel")
                        break
                    elif response.status_code == 404:
                        print("   ⚠️ Channel not found")
                        break
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n\n👋 Stopped by user")
                break
            except requests.RequestException as e:
                print(f" ❌ Network error: {e}")
                print(f"   💤 Retrying in {self.check_interval}s...\n")
                time.sleep(self.check_interval)
            except Exception as e:
                print(f" ❌ Error: {e}")
                import traceback
                print("\n   Debug info:")
                traceback.print_exc()
                print(f"   💤 Retrying in {self.check_interval}s...\n")
                time.sleep(self.check_interval)
    
    def cleanup(self):
        """Close the browser"""
        if self.driver:
            print("\n🧹 Cleaning up...")
            try:
                self.driver.quit()
                print("   ✅ Browser closed")
            except:
                pass


def main():
    print("="*60)
    print("🎯 TikTok Username Auto-Claimer (Selenium)")
    print("="*60)
    print("\n⚠️  This uses browser automation to bypass API restrictions")
    print("You'll need Chrome browser installed\n")
    print("="*60 + "\n")
    
    # Setup
    headless = input("Run browser in headless mode (invisible)? (y/n): ").strip().lower() == 'y'
    
    claimer = TikTokSeleniumClaimer(headless=headless)
    
    # Initialize browser
    if not claimer.setup_driver():
        print("❌ Failed to setup browser. Make sure Chrome is installed.")
        return
    
    try:
        # Login method
        print("\n" + "="*60)
        print("Choose login method:")
        print("1. Manual login (you login in the browser)")
        print("2. Load cookies from JSON file (enter path)")
        print("3. Load cookies from 'sessions.txt' (same folder)")
        print("="*60)
        
        login_choice = input("\nChoice (1, 2, or 3): ").strip()
        
        logged_in = False
        
        if login_choice == "3":
            # Try to load from sessions.txt in the same directory
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cookies_file = os.path.join(script_dir, "sessions.txt")
            
            if os.path.exists(cookies_file):
                print(f"📂 Loading from: {cookies_file}")
                logged_in = claimer.login_with_cookies(cookies_file)
            else:
                print(f"❌ File not found: {cookies_file}")
                print("Make sure 'sessions.txt' is in the same folder as this script")
                claimer.cleanup()
                return
        elif login_choice == "2":
            cookies_file = input("Enter path to cookies JSON file: ").strip()
            logged_in = claimer.login_with_cookies(cookies_file)
        else:
            logged_in = claimer.manual_login()
        
        if not logged_in:
            print("❌ Login failed")
            claimer.cleanup()
            return
        
        # Get current username
        claimer.current_username = claimer.get_current_username()
        
        # Choose mode
        print("\n" + "="*60)
        print("Select mode:")
        print("1. 👀 Monitor Discord webhook")
        print("2. ✋ Manual mode (enter usernames)")
        print("="*60)
        
        mode_choice = input("\nChoice (1 or 2): ").strip()
        
        if mode_choice == "1":
            print("\n" + "="*60)
            print("Discord Bot Setup")
            print("="*60)
            print("You need a Discord BOT (not webhook) to monitor messages.")
            print("\nHow to set up:")
            print("1. Go to https://discord.com/developers/applications")
            print("2. Create a New Application")
            print("3. Go to 'Bot' section and create a bot")
            print("4. Copy the bot TOKEN")
            print("5. Enable 'MESSAGE CONTENT INTENT' under Privileged Gateway Intents")
            print("6. Go to OAuth2 > URL Generator")
            print("7. Select scopes: 'bot', permissions: 'Read Messages/View Channels'")
            print("8. Copy the URL and invite the bot to your server")
            print("9. Right-click the channel and 'Copy Channel ID' (enable Developer Mode in settings)")
            print("="*60 + "\n")
            
            bot_token = input("Bot Token: ").strip()
            channel_id = input("Channel ID: ").strip()
            
            # Clean up the token - remove any whitespace, newlines, or common artifacts
            bot_token = ''.join(bot_token.split())  # Remove all whitespace
            channel_id = ''.join(channel_id.split())  # Remove all whitespace
            
            # Additional cleanup - sometimes Discord username/timestamp gets copied
            # Bot tokens always start with "MT" or "MTA" or similar base64-like format
            # and contain exactly 2 dots
            if '.' in bot_token:
                # Find the part that looks like a token (has 2 dots and starts with M)
                parts = bot_token.split()
                for part in parts:
                    if part.count('.') == 2 and part[0] in ['M', 'N', 'O']:
                        bot_token = part
                        break
            
            print(f"\n🔑 Using token: {bot_token[:20]}...{bot_token[-10:]}")
            print(f"📡 Channel ID: {channel_id}\n")
            
            if bot_token and channel_id:
                claimer.monitor_discord_bot_mode(channel_id, bot_token)
            else:
                print("❌ Bot token and channel ID required")
        else:
            claimer.manual_mode()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ask before closing
        input("\n⏸️  Press Enter to close the browser...")
        claimer.cleanup()


if __name__ == "__main__":
    main()
