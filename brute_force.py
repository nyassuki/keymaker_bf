import ecdsa
import hashlib
import base58
import requests
import os
import json
import logging
from dotenv import load_dotenv

try:
    from telegram import Bot
except ImportError:
    print("⚠️ python-telegram-bot is missing! Install it using: pip install python-telegram-bot")
    exit(1)

from Crypto.Hash import RIPEMD160

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Telegram Bot Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your-default-token")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your-default-chat-id")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    logging.error("❌ Missing Telegram bot token or chat ID. Set them in the .env file.")
    exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Define key search range (default values)
DEFAULT_START_RANGE = int("8000000000000000000000000000000000000000000000000000000000000000", 16)
END_RANGE = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 16)

# File paths
PROGRESS_FILE = "./progress.txt"
FOUND_FILE = "./found/found_keys.txt"
PUZZLE_ADDRESSES_FILE = "./target_addresses.json"

# Load puzzle addresses
try:
    with open(PUZZLE_ADDRESSES_FILE, "r") as f:
        PUZZLE_ADDRESSES = set(json.load(f))  # Using a set for fast lookup
except FileNotFoundError:
    logging.error(f"❌ File not found: {PUZZLE_ADDRESSES_FILE}")
    PUZZLE_ADDRESSES = set()

def send_telegram_message(message):
    """Send a message to the Telegram bot."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info("✅ Telegram message sent successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to send Telegram message: {e}")

def private_key_to_wif(private_key_hex):
    """Convert a private key to Wallet Import Format (WIF)."""
    extended_key = b'\x80' + bytes.fromhex(private_key_hex)
    sha256_1 = hashlib.sha256(extended_key).digest()
    sha256_2 = hashlib.sha256(sha256_1).digest()
    checksum = sha256_2[:4]
    return base58.b58encode(extended_key + checksum).decode()

def private_key_to_address(private_key_hex):
    """Convert private key to a Bitcoin address."""
    private_key_bytes = bytes.fromhex(private_key_hex)
    key = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
    pubkey = key.verifying_key.to_string()

    sha256_bpk = hashlib.sha256(b'\x04' + pubkey).digest()
    ripemd160_bpk = RIPEMD160.new(sha256_bpk).digest()

    network_byte = b'\x00' + ripemd160_bpk
    sha256_nbpk = hashlib.sha256(network_byte).digest()
    sha256_2_nbpk = hashlib.sha256(sha256_nbpk).digest()
    checksum = sha256_2_nbpk[:4]

    return base58.b58encode(network_byte + checksum).decode()

def get_balance(addr):
    """Check the balance of a Bitcoin address."""
    try:
        url = f"https://blockstream.info/api/address/{addr}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        funded_txo_sum = data.get("chain_stats", {}).get("funded_txo_sum", 0)
        spent_txo_sum = data.get("chain_stats", {}).get("spent_txo_sum", 0)
        return funded_txo_sum - spent_txo_sum  # Balance in satoshis
    except requests.exceptions.RequestException as error:
        logging.error(f"Error fetching balance for address {addr}: {error}")
        return 0
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON response for address {addr}")
        return 0

def save_progress(last_key):
    """Save the last checked private key to progress file."""
    with open(PROGRESS_FILE, "w") as f:
        f.write(last_key)

def load_progress():
    """Load the last checked private key from progress file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            last_key = f.read().strip()
            if last_key:
                return int(last_key, 16)
    return DEFAULT_START_RANGE

def brute_force():
    """Iterate over private keys and check for matches."""
    current_key = load_progress()
    attempts = 0

    while current_key <= END_RANGE:
        private_key = hex(current_key)[2:].zfill(64)
        address = private_key_to_address(private_key)
        balance = get_balance(address)

        # Match conditions
        if address in PUZZLE_ADDRESSES or balance > 0:
            message = f"🎉 MATCH FOUND!\nPrivate Key: {private_key}\nAddress: {address}\nBalance: {balance} satoshis"
            logging.info(message)

            with open(FOUND_FILE, "a") as f:
                f.write(f"{private_key} -> {address} | Balance: {balance}\n")

            send_telegram_message(message)

        # Save progress every 1000 attempts
        if attempts % 1000 == 0:
            save_progress(private_key)
            logging.info(f"🔍 Scanned: {private_key} -> {address} | Balance: {balance}")

        attempts += 1
        current_key += 1

brute_force()
