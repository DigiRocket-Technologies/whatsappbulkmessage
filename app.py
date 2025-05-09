#!/usr/bin/env python3
"""
WhatsApp Bulk Message Sender - GUI Application
----------------------------------------------
A user-friendly interface for sending bulk WhatsApp messages.
Requirements:
- Python 3.6+
- Selenium
- Chrome WebDriver
- Tkinter (included with standard Python installation)

Installation:
pip install selenium
"""

import os
import csv
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class WhatsAppBulkSender:
    def __init__(self, headless=False, log_callback=None):
        """Initialize the WhatsApp Bulk Message Sender."""
        self.driver = None
        self.wait = None
        self.headless = headless
        self.log_callback = log_callback
        self.is_running = False
        self.cancel_requested = False
        
    def log(self, message):
        """Log messages to the UI."""
        if self.log_callback:
            self.log_callback(message)
        print(message)
        
    def _setup_driver(self):
        """Set up and return a Chrome WebDriver."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Attempt to create the driver with error handling
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            error_msg = f"Error setting up Chrome WebDriver: {e}"
            self.log(error_msg)
            self.log("\nPlease ensure Chrome is installed correctly and updated to the latest version.")
            raise
        
    def start(self):
        """Open WhatsApp Web and wait for QR code scan."""
        self.is_running = True
        self.cancel_requested = False
        
        try:
            self.driver = self._setup_driver()
            self.wait = WebDriverWait(self.driver, 30)
            
            self.driver.get("https://web.whatsapp.com")
            self.log("Please scan the QR code to log in to WhatsApp Web...")
            self.log("The browser will wait for 2 minutes for you to scan the QR code.")
            
            # Wait for the user to scan the QR code and load WhatsApp Web
            try:
                # Wait for WhatsApp to load - look for either the chat/search interface or QR code
                self.wait.until(lambda driver: driver.find_elements(By.XPATH, '//div[@contenteditable="true"]') or 
                                              driver.find_elements(By.XPATH, '//canvas[contains(@aria-label, "Scan")]'))
                
                # Extended wait for user to scan QR and for WhatsApp to fully load
                extended_wait = WebDriverWait(self.driver, 120)  # 2 minute timeout
                extended_wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]')))
                self.log("Successfully logged in to WhatsApp Web!")
                return True
            except TimeoutException:
                self.log("\nTimeout: QR code scan took too long or WhatsApp Web didn't load properly.")
                self.log("Please try running the script again.")
                return False
        except Exception as e:
            self.log(f"Error starting WhatsApp Web: {e}")
            return False
            
    def search_contact(self, contact):
        """Search for a contact in WhatsApp."""
        if self.cancel_requested:
            return False
            
        try:
            # Wait for the search or chat input to be available
            search_xpath = [
                '//div[@contenteditable="true"][@data-tab="3"]',  # Primary search box
                '//div[@role="textbox"][@contenteditable="true"]',  # Alternative search box
                '//div[contains(@class, "selectable-text")][@contenteditable="true"]'  # Generic contenteditable
            ]
            
            # Try different XPaths to find the search box
            search_box = None
            for xpath in search_xpath:
                try:
                    search_box = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    if search_box and search_box.is_displayed():
                        break
                except:
                    continue
            
            if not search_box:
                self.log("Could not find the search box. WhatsApp Web interface might have changed.")
                return False
            
            # Clear any existing text and search for the contact
            search_box.clear()
            
            # Check if contact is likely a phone number (all digits)
            is_phone = contact.replace('+', '').isdigit()
            
            if is_phone:
                # For phone numbers, we need to use the WhatsApp format
                formatted_contact = contact
                # Add the "+" if it's missing and has enough digits to be a phone number
                if len(contact) > 7 and not contact.startswith('+'):
                    formatted_contact = f"+{contact}"
                
                search_box.send_keys(formatted_contact)
                self.log(f"Searching for phone number: {formatted_contact}")
            else:
                search_box.send_keys(contact)
                self.log(f"Searching for contact: {contact}")
                
            time.sleep(2)  # Wait for search results
            
            # Try different approaches to find and click the contact
            try:
                # First approach: Try to find by title attribute
                xpath_patterns = [
                    f'//span[@title="{contact}"]',
                    f'//span[contains(@title, "{contact}")]',
                    f'//div[contains(@title, "{contact}")]',
                    '//div[contains(@class, "matched-text")]/..',
                    '//div[contains(@class, "chat-title")]'
                ]
                
                for xpath in xpath_patterns:
                    if self.cancel_requested:
                        return False
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        if elements:
                            elements[0].click()
                            time.sleep(1)
                            return True
                    except:
                        continue
                
                # If all attempts fail for phone numbers, try direct URL approach
                if is_phone and len(contact) > 7:
                    # Remove any + symbol for the URL
                    clean_number = contact.replace('+', '')
                    # Go directly to chat with this number
                    self.driver.get(f"https://web.whatsapp.com/send?phone={clean_number}")
                    # Wait for chat to load
                    self.wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))
                    time.sleep(2)
                    return True
                    
            except (TimeoutException, NoSuchElementException):
                pass
                
            self.log(f"Could not find contact: {contact}")
            return False
        except Exception as e:
            self.log(f"Error searching for contact {contact}: {e}")
            return False
            
    def send_message(self, message):
        """Send a message to the currently selected contact."""
        if self.cancel_requested:
            return False
            
        try:
            # Try different XPaths to find the message input box
            message_box_xpaths = [
                '//div[@contenteditable="true"][@data-tab="10"]',
                '//div[@contenteditable="true"][@spellcheck="true"]',
                '//div[@role="textbox"][@contenteditable="true"]',
                '//div[contains(@class, "selectable-text")][@contenteditable="true"]'
            ]
            
            message_box = None
            for xpath in message_box_xpaths:
                try:
                    message_box = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    if message_box and message_box.is_displayed():
                        break
                except:
                    continue
            
            if not message_box:
                self.log("Could not find the message input box. WhatsApp Web interface might have changed.")
                return False
            
            # Check if we need to handle "unknown number" popups for new numbers
            try:
                # Look for "OK"/"YES" buttons in popups
                buttons = self.driver.find_elements(By.XPATH, '//div[@role="button" and (contains(., "OK") or contains(., "Yes") or contains(., "Continue"))]')
                for button in buttons:
                    if button.is_displayed():
                        button.click()
                        time.sleep(1)
                        break
            except:
                pass
            
            # Type the message with line breaks
            message_box.clear()
            for line in message.split('\n'):
                message_box.send_keys(line)
                # For new lines
                message_box.send_keys(Keys.SHIFT + Keys.ENTER)
            
            # Remove the last extra line break
            message_box.send_keys(Keys.BACKSPACE)
            
            # Send the message
            message_box.send_keys(Keys.ENTER)
            time.sleep(1)
            return True
        except Exception as e:
            self.log(f"Failed to send message: {e}")
            return False
            
    def send_bulk_messages(self, contacts, message, delay=3):
        """Send messages to multiple contacts."""
        if not contacts:
            self.log("No contacts found or invalid file format.")
            return
            
        success_count = 0
        fail_count = 0
        
        self.log(f"\nSending messages to {len(contacts)} contacts...\n")
        
        for i, contact in enumerate(contacts, 1):
            if self.cancel_requested:
                self.log("Operation cancelled by user.")
                break
                
            contact_name = contact['name']
            
            self.log(f"[{i}/{len(contacts)}] Sending to: {contact_name}...")
            
            if self.search_contact(contact_name):
                # Personalize message if needed
                personalized_message = message
                if '{name}' in message:
                    personalized_message = message.replace('{name}', contact_name)
                
                # Add any custom fields from the CSV
                for key, value in contact.items():
                    if key != 'name' and f'{{{key}}}' in personalized_message:
                        personalized_message = personalized_message.replace(f'{{{key}}}', str(value))
                
                if self.send_message(personalized_message):
                    self.log(f"✓ Message sent to {contact_name}")
                    success_count += 1
                else:
                    self.log(f"✗ Failed to send message to {contact_name}")
                    fail_count += 1
            else:
                self.log(f"✗ Could not find contact: {contact_name}")
                fail_count += 1
                
            # Wait between messages to avoid being flagged as spam
            for i in range(delay):
                if self.cancel_requested:
                    break
                time.sleep(1)
            
        self.log(f"\nDone! Messages sent: {success_count}, Failed: {fail_count}")
        self.is_running = False
        
    def load_contacts_from_csv(self, file_path):
        """Load contacts from a CSV file."""
        contacts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if 'name' in row:
                        contacts.append(row)
                    else:
                        self.log("Error: CSV file must have a 'name' column.")
                        return []
        except Exception as e:
            self.log(f"Error loading contacts file: {e}")
            return []
            
        return contacts
        
    def quit(self):
        """Close the browser and end the session."""
        if self.driver:
            try:
                self.driver.quit()
                self.log("Browser closed. Session ended.")
            except:
                pass
        self.is_running = False


class WhatsAppSenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp Bulk Message Sender")
        self.root.geometry("700x700")
        self.root.minsize(600, 600)
        
        # Define custom styles for prominent buttons
        self.setup_styles()
        
        # Initialize variables
        self.contacts_file_path = tk.StringVar()
        self.headless_var = tk.BooleanVar(value=False)
        self.delay_var = tk.IntVar(value=3)
        self.add_phone_var = tk.StringVar()
        self.input_method_var = tk.StringVar(value="csv")
        
        self.sender = WhatsAppBulkSender(log_callback=self.update_log)
        self.manual_contacts = []
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.message_tab = ttk.Frame(self.notebook)
        self.logs_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.setup_tab, text="Setup")
        self.notebook.add(self.message_tab, text="Message")
        self.notebook.add(self.logs_tab, text="Logs")
        
        # Setup the tabs
        self._setup_setup_tab()
        self._setup_message_tab()
        self._setup_logs_tab()
        
        # Control buttons at the bottom
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_button = ttk.Button(controls_frame, text="Start WhatsApp", command=self.start_whatsapp)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Make the send button larger and more prominent
        self.send_button = ttk.Button(
            controls_frame, 
            text="SEND MESSAGES", 
            command=self.start_sending,
            state=tk.DISABLED,
            style="Send.TButton"  # Custom style for prominence
        )
        self.send_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.cancel_button = ttk.Button(controls_frame, text="Cancel", command=self.cancel_operation, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        self.quit_button = ttk.Button(controls_frame, text="Quit", command=self.quit_application)
        self.quit_button.pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Set up protocol for window close
        root.protocol("WM_DELETE_WINDOW", self.quit_application)
    
    def setup_styles(self):
        """Set up custom styles for buttons."""
        style = ttk.Style()
        
        # Create a prominent style for the send button
        style.configure("Send.TButton", 
                       font=("", 10, "bold"),
                       padding=(10, 5))
        
        # Create a style for section headers
        style.configure("Header.TLabel",
                       font=("", 11, "bold"))
                       
    def _setup_setup_tab(self):
        """Setup the configuration tab."""
        frame = ttk.Frame(self.setup_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Input method selection
        ttk.Label(frame, text="Select Input Method:", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        method_frame = ttk.Frame(frame)
        method_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))
        
        ttk.Radiobutton(method_frame, text="CSV File", variable=self.input_method_var, value="csv", 
                        command=self.toggle_input_method).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(method_frame, text="Manual Input", variable=self.input_method_var, value="manual", 
                        command=self.toggle_input_method).pack(side=tk.LEFT)
        
        # CSV File selection
        self.csv_frame = ttk.LabelFrame(frame, text="CSV File Input", padding="10")
        self.csv_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=(0, 15))
        
        ttk.Label(self.csv_frame, text="CSV File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        ttk.Entry(self.csv_frame, textvariable=self.contacts_file_path, width=40).grid(row=0, column=1, sticky=tk.EW, pady=5)
        ttk.Button(self.csv_frame, text="Browse...", command=self.browse_csv).grid(row=0, column=2, padx=(5, 0), pady=5)
        
        csv_info = ttk.Label(self.csv_frame, text="CSV file must have a 'name' column for contact names/numbers.\nYou can use column names as placeholders in your message like {name}, {company}, etc.", 
                            justify=tk.LEFT, wraplength=500)
        csv_info.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        # Manual Input
        self.manual_frame = ttk.LabelFrame(frame, text="Manual Phone Input", padding="10")
        self.manual_frame.grid(row=3, column=0, columnspan=3, sticky=tk.NSEW, pady=(0, 15))
        self.manual_frame.grid_remove()  # Initially hidden
        
        # New multi-number input
        ttk.Label(self.manual_frame, text="Enter individual phone number:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        phone_entry = ttk.Entry(self.manual_frame, textvariable=self.add_phone_var, width=20)
        phone_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        phone_entry.bind('<Return>', lambda e: self.add_phone())
        
        ttk.Button(self.manual_frame, text="Add", command=self.add_phone).grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # IMPROVED: Bulk phone number input
        ttk.Label(self.manual_frame, text="OR paste multiple phone numbers:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(15, 5))
        
        self.bulk_phones_frame = ttk.Frame(self.manual_frame)
        self.bulk_phones_frame.grid(row=2, column=0, columnspan=3, sticky=tk.NSEW, pady=(0, 5))
        
        self.bulk_phones_text = scrolledtext.ScrolledText(self.bulk_phones_frame, wrap=tk.WORD, width=40, height=5)
        self.bulk_phones_text.pack(fill=tk.BOTH, expand=True)
        
        bulk_info = ttk.Label(self.manual_frame, text="Enter one phone number per line, or separate with commas, semicolons, or spaces.\nNumbers should include country code (e.g., 14155552671).", 
                             justify=tk.LEFT, wraplength=500)
        bulk_info.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        # Frame for the bulk import button - prominent placement
        bulk_btn_frame = ttk.Frame(self.manual_frame)
        bulk_btn_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(5, 15))
        
        # Important button for bulk import functionality - prominently styled
        self.add_all_btn = ttk.Button(bulk_btn_frame, text="ADD ALL NUMBERS", 
                                     command=self.add_bulk_phones)
        self.add_all_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Adding a note to highlight the button's function
        ttk.Label(bulk_btn_frame, text="← Click to process all pasted numbers", 
                 font=("", 9, "italic")).pack(side=tk.LEFT, padx=(5, 0))
        
        # Phone list
        ttk.Label(self.manual_frame, text="Added Phone Numbers:").grid(row=5, column=0, sticky=tk.W, pady=(10, 5))
        
        self.phones_listbox_frame = ttk.Frame(self.manual_frame)
        self.phones_listbox_frame.grid(row=6, column=0, columnspan=3, sticky=tk.NSEW, pady=(0, 5))
        self.phones_listbox_frame.grid_columnconfigure(0, weight=1)
        self.phones_listbox_frame.grid_rowconfigure(0, weight=1)
        
        self.phones_listbox = tk.Listbox(self.phones_listbox_frame, height=6)
        self.phones_listbox.grid(row=0, column=0, sticky=tk.NSEW)
        
        phones_scrollbar = ttk.Scrollbar(self.phones_listbox_frame, orient=tk.VERTICAL, command=self.phones_listbox.yview)
        phones_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.phones_listbox.configure(yscrollcommand=phones_scrollbar.set)
        
        phones_buttons_frame = ttk.Frame(self.manual_frame)
        phones_buttons_frame.grid(row=7, column=0, columnspan=3, sticky=tk.E, pady=(5, 0))
        
        ttk.Button(phones_buttons_frame, text="Remove Selected", command=self.remove_phone).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(phones_buttons_frame, text="Clear All", command=self.clear_phones).pack(side=tk.RIGHT)
        
        # General Settings
        settings_frame = ttk.LabelFrame(frame, text="Settings", padding="10")
        settings_frame.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=(0, 10))
        
        ttk.Label(settings_frame, text="Delay between messages (seconds):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        ttk.Spinbox(settings_frame, from_=1, to=30, textvariable=self.delay_var, width=5).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Checkbutton(settings_frame, text="Headless mode (no browser UI)", variable=self.headless_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Make rows and columns expandable
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        self.manual_frame.grid_columnconfigure(1, weight=1)
        self.manual_frame.grid_rowconfigure(6, weight=1)
        
    def _setup_message_tab(self):
        """Setup the message composition tab."""
        frame = ttk.Frame(self.message_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Compose your message:", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        message_info = ttk.Label(frame, text="You can use {name} as a placeholder for the contact name.\nFor CSV input, you can use other column names as placeholders like {company}, {date}, etc.",
                                justify=tk.LEFT, wraplength=600)
        message_info.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        # Message text area
        self.message_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=60, height=15)
        self.message_text.grid(row=2, column=0, sticky=tk.NSEW, pady=(0, 10))
        
        # Template buttons
        templates_frame = ttk.LabelFrame(frame, text="Templates", padding="10")
        templates_frame.grid(row=3, column=0, sticky=tk.EW, pady=(0, 10))
        
        ttk.Button(templates_frame, text="Greeting", 
                  command=lambda: self.insert_template("Hello {name}!\n\nI hope this message finds you well. "
                                                     "I wanted to reach out regarding our upcoming meeting.\n\n"
                                                     "Best regards,\n[Your Name]")).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(templates_frame, text="Reminder", 
                  command=lambda: self.insert_template("Hi {name},\n\nThis is a friendly reminder about our "
                                                     "appointment scheduled for tomorrow.\n\n"
                                                     "Please let me know if you need to reschedule.\n\n"
                                                     "Regards,\n[Your Name]")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(templates_frame, text="Thank You", 
                  command=lambda: self.insert_template("Dear {name},\n\nThank you for your recent purchase. "
                                                     "We truly appreciate your business.\n\n"
                                                     "If you have any questions, please don't hesitate to reach out.\n\n"
                                                     "Warm regards,\n[Your Name]")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(templates_frame, text="Clear", 
                  command=lambda: self.message_text.delete(1.0, tk.END)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Make rows and columns expandable
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        
    def _setup_logs_tab(self):
        """Setup the logs tab."""
        frame = ttk.Frame(self.logs_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Operation Logs:", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=60, height=20, state=tk.DISABLED)
        self.log_text.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 10))
        
        # Buttons
        buttons_frame = ttk.Frame(frame)
        buttons_frame.grid(row=2, column=0, sticky=tk.E, pady=(0, 10))
        
        ttk.Button(buttons_frame, text="Copy Logs", command=self.copy_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT)
        
        # Make rows and columns expandable
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
    
    def toggle_input_method(self):
        """Toggle between CSV and manual input methods."""
        if self.input_method_var.get() == "csv":
            self.csv_frame.grid()
            self.manual_frame.grid_remove()
        else:
            self.csv_frame.grid_remove()
            self.manual_frame.grid()
            
    def browse_csv(self):
        """Open file dialog to select CSV file."""
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.contacts_file_path.set(file_path)
    
    # IMPROVED: New method to add bulk phone numbers
    def add_bulk_phones(self):
        """Add multiple phone numbers from the bulk input field."""
        bulk_text = self.bulk_phones_text.get(1.0, tk.END).strip()
        if not bulk_text:
            return
            
        # Process the text to extract phone numbers
        # First replace common separators with newlines
        bulk_text = bulk_text.replace(',', '\n').replace(';', '\n')
        # Then split by lines and process each
        lines = bulk_text.split('\n')
        
        added_count = 0
        invalid_count = 0
        
        for line in lines:
            # Split by spaces and process each potential number
            potential_numbers = line.split()
            for number in potential_numbers:
                # Clean the number
                clean_number = number.strip()
                if not clean_number:
                    continue
                    
                # Basic validation
                if not clean_number.replace('+', '').isdigit():
                    invalid_count += 1
                    continue
                    
                # Format phone number
                if not clean_number.startswith('+') and len(clean_number) > 7:
                    clean_number = f"+{clean_number}"
                    
                # Add to listbox and internal list
                self.phones_listbox.insert(tk.END, clean_number)
                self.manual_contacts.append({"name": clean_number})
                added_count += 1
                
        # Clear the bulk input field
        self.bulk_phones_text.delete(1.0, tk.END)
        
        # Show results
        if added_count > 0:
            messagebox.showinfo("Numbers Added", f"Successfully added {added_count} phone numbers to the list.")
            if invalid_count > 0:
                messagebox.showwarning("Invalid Numbers", f"{invalid_count} numbers were skipped because they were invalid.")
        else:
            if invalid_count > 0:
                messagebox.showwarning("Invalid Numbers", f"All {invalid_count} numbers were invalid. No numbers added.")
            else:
                messagebox.showinfo("No Numbers", "No phone numbers were found in the input.")
            
    def add_phone(self):
        """Add a phone number to the list."""
        phone = self.add_phone_var.get().strip()
        if not phone:
            return
            
        # Basic validation
        if not phone.replace('+', '').isdigit():
            messagebox.showerror("Invalid Input", "Please enter only digits, optionally starting with +")
            return
            
        # Format phone number
        if not phone.startswith('+') and len(phone) > 7:
            phone = f"+{phone}"
            
        # Add to listbox and internal list
        self.phones_listbox.insert(tk.END, phone)
        self.manual_contacts.append({"name": phone})
        
        # Clear the entry
        self.add_phone_var.set("")
        
    def remove_phone(self):
        """Remove selected phone number from the list."""
        try:
            selected_idx = self.phones_listbox.curselection()[0]
            self.phones_listbox.delete(selected_idx)
            self.manual_contacts.pop(selected_idx)
        except (IndexError, TypeError):
            pass
            
    def clear_phones(self):
        """Clear all phone numbers from the list."""
        self.phones_listbox.delete(0, tk.END)
        self.manual_contacts.clear()
        
    def insert_template(self, template_text):
        """Insert a template message."""
        self.message_text.delete(1.0, tk.END)
        self.message_text.insert(tk.END, template_text)
        
    def update_log(self, message):
        """Update the log text area."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
    def copy_logs(self):
        """Copy all logs to clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text.get(1.0, tk.END))
        self.status_var.set("Logs copied to clipboard")
        
    def clear_logs(self):
        """Clear all logs."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.status_var.set("Logs cleared")
        
    def start_whatsapp(self):
        """Start WhatsApp Web and wait for login."""
        self.sender.headless = self.headless_var.get()
        
        # Update UI
        self.start_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.status_var.set("Starting WhatsApp Web...")
        self.notebook.select(self.logs_tab)
        
        # Create and start thread
        self.update_log("Starting WhatsApp Web browser...")
        
        def whatsapp_thread():
            success = self.sender.start()
            if success:
                self.root.after(0, self.after_whatsapp_started)
            else:
                self.root.after(0, self.after_whatsapp_failed)
        
        threading.Thread(target=whatsapp_thread, daemon=True).start()
        
    def after_whatsapp_started(self):
        """Called after WhatsApp has successfully started."""
        self.send_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.NORMAL)
        self.start_button.config(state=tk.DISABLED)
        self.status_var.set("WhatsApp Web ready. You can send messages now.")
        self.notebook.select(self.message_tab)
        
    def after_whatsapp_failed(self):
        """Called when WhatsApp failed to start."""
        self.send_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)
        self.status_var.set("Failed to start WhatsApp Web.")
        
    def start_sending(self):
        """Start sending messages to the contacts."""
        # Validate inputs
        message = self.message_text.get(1.0, tk.END).strip()
        if not message:
            messagebox.showerror("Error", "Please enter a message to send.")
            self.notebook.select(self.message_tab)
            return
            
        contacts = []
        
        if self.input_method_var.get() == "csv":
            csv_path = self.contacts_file_path.get().strip()
            if not csv_path or not os.path.isfile(csv_path):
                messagebox.showerror("Error", "Please select a valid CSV file.")
                self.notebook.select(self.setup_tab)
                return
            contacts = self.sender.load_contacts_from_csv(csv_path)
            if not contacts:
                messagebox.showerror("Error", "No valid contacts found in the CSV file.")
                return
        else:  # manual input
            if not self.manual_contacts:
                messagebox.showerror("Error", "Please add at least one phone number.")
                self.notebook.select(self.setup_tab)
                return
            contacts = self.manual_contacts
            
        delay = self.delay_var.get()
        
        # Update UI
        self.send_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.status_var.set("Sending messages...")
        self.notebook.select(self.logs_tab)
        
        # Create and start thread
        def sending_thread():
            self.sender.send_bulk_messages(contacts, message, delay)
            self.root.after(0, self.after_sending_completed)
            
        threading.Thread(target=sending_thread, daemon=True).start()
        
    def after_sending_completed(self):
        """Called after sending messages is completed."""
        if not self.sender.cancel_requested:
            self.update_log("Sending completed!")
            self.status_var.set("Message sending completed.")
        
        self.send_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        
    def cancel_operation(self):
        """Cancel the current operation."""
        if self.sender.is_running:
            self.sender.cancel_requested = True
            self.update_log("Cancelling operation... Please wait.")
            self.status_var.set("Cancelling operation...")
            self.cancel_button.config(state=tk.DISABLED)
            
    def quit_application(self):
        """Quit the application."""
        if self.sender.is_running:
            if not messagebox.askyesno("Quit", "An operation is in progress. Are you sure you want to quit?"):
                return
            self.sender.cancel_requested = True
            
        # Close the browser if it's open
        try:
            self.sender.quit()
        except:
            pass
            
        self.root.destroy()
        
def main():
    """Main function to run the WhatsApp Bulk Sender GUI."""
    root = tk.Tk()
    app = WhatsAppSenderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()