import ecdsa
import hashlib
import base58
import requests
import os
import json
import logging
from telegram import Bot
from Crypto.Hash import RIPEMD160

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Telegram Bot Config
TELEGRAM_BOT_TOKEN = "7413053009:AAGMiHOUPW8l3i2SJERw2kQubG3ICWl6Hdo"
TELEGRAM_CHAT_ID = "7615664261"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Define key search range (default values)
DEFAULT_START_RANGE = int("8000000000000000000000000000000000000000000000000000000000000000", 16)
END_RANGE = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 16)

# File paths
PROGRESS_FILE = "./progress.txt"
FOUND_FILE = "./found/found_keys.txt"
PUZZLE_ADDRESSES_FILE = "./target_addresses.json"

# Load puzzle addresses
with open(PUZZLE_ADDRESSES_FILE, "r") as f:
    PUZZLE_ADDRESSES = json.load(f)

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
        funded_txo_sum = data['chain_stats']['funded_txo_sum']
        spent_txo_sum = data['chain_stats']['spent_txo_sum']
        balance = funded_txo_sum - spent_txo_sum
        return [balance, funded_txo_sum, spent_txo_sum]
    except requests.exceptions.RequestException as error:
        logging.error(f"Error fetching balance for address {addr}: {error}")
        return [0, 0, 0]
    except KeyError as error:
        logging.error(f"Error parsing balance data for address {addr}: {error}")
        return [0, 0, 0]

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
        balance, _, _ = get_balance(address)

        

        if address in PUZZLE_ADDRESSES or balance > 0:
            message = f"🎉 MATCH FOUND! \nPrivate Key: {private_key}\nAddress: {address}\nBalance: {balance} satoshis"
            logging.info(message)

            with open(FOUND_FILE, "a") as f:
                f.write(f"{private_key} -> {address} | Balance: {balance}\n")

            send_telegram_message(message)

        # Save progress every 1000 attempts
        if attempts % 10 == 0:
            save_progress(private_key)
            logging.info(f"Checking: {private_key} -> {address} | Balance: {balance}")

        attempts += 1
        current_key += 1

brute_force()
