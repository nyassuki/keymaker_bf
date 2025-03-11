import os
import requests
import json
from bitcoinlib.keys import Key
from bitcoinlib.networks import Network

# Network (mainnet, testnet, etc.)
network = Network('bitcoin')  # Use 'bitcoin' for mainnet

# Telegram bot details
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = "7615664261"

# Function to send a message to Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")

# Load targets from JSON file
def load_targets():
    try:
        with open("./targets.json", "r") as file:
            targets = json.load(file)
            return targets
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Load preloaded addresses from JSON file
def load_preloaded_addresses():
    try:
        with open("./target_addresses.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Load targets and preloaded addresses
targets = load_targets()
preloaded_addresses = load_preloaded_addresses()
if not targets and not preloaded_addresses:
    print("No targets or preloaded addresses found. Exiting.")
    exit()

# Function to generate a random private key
def generate_private_key():
    return os.urandom(32).hex()

# Function to generate a Bitcoin address from a private key
def generate_address(private_key):
    key = Key(private_key, network=network)
    return key.address()

# Function to check if the private key matches any target conditions
def is_private_key_match(private_key):
    for target in targets:
        if private_key.startswith(target["startwith"]) and private_key.endswith(target["endwith"]):
            return True, target
    return False, None

# Function to check if the address matches any preloaded addresses
def is_address_match(address):
    return address in preloaded_addresses

# Function to save results to a JSON file
def save_to_json(file_name, data):
    try:
        with open(file_name, "r") as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        existing_data = []
    existing_data.append(data)
    with open(file_name, "w") as file:
        json.dump(existing_data, file, indent=4)

# Main function to run the puzzle
def run_puzzle():
    attempts = 0
    print("Starting Bitcoin puzzle...")
    while True:
        private_key = generate_private_key()
        address = generate_address(private_key)
        balance = 0  # Set balance to 0 to avoid API calls
        attempts += 1
        print(f"{private_key}, {address}, {balance} satoshis")

        if is_address_match(address):
            message = f"\U0001F3AF Address match found after {attempts} attempts!\n\U0001F510 Private Key: {private_key}\n\U0001F3E6 Address: {address}\n\U0001F4B0 Balance: {balance} satoshis"
            send_telegram_message(message)
            save_to_json("./found/address_matches.json", {"private_key": private_key, "address": address, "balance": balance})

        private_key_match, target = is_private_key_match(private_key)
        if private_key_match:
            message = f"\U0001F510 Private key match found after {attempts} attempts!\n\U0001F3E6 Address: {address}\n\U0001F4B0 Balance: {balance} satoshis\n\U0001F3AF Target: {target}"
            send_telegram_message(message)
            save_to_json("./found/private_key_matches.json", {"private_key": private_key, "address": address, "balance": balance, "target": target})

        if balance > 0:
            message = f"\U0001F4B0 Balance > 0 found after {attempts} attempts!\n\U0001F510 Private Key: {private_key}\n\U0001F3E6 Address: {address}\n\U0001F4B0 Balance: {balance} satoshis"
            send_telegram_message(message)
            save_to_json("./found/balance_matches.json", {"private_key": private_key, "address": address, "balance": balance})

        if attempts % 1000 == 0:
            print(f"Attempts: {attempts}")

# Run the puzzle
run_puzzle()
