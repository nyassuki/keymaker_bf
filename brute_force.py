import ecdsa
import hashlib
import base58
import requests
import random
import os
import json
from Crypto.Hash import RIPEMD160  # Import RIPEMD160 from pycryptodome

# Define key search range (default values)
DEFAULT_START_RANGE = int("8000000000000000000000000000000000000000000000000000000000000000", 16)
END_RANGE = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 16)

# File paths
PROGRESS_FILE = "./progress.txt"
FOUND_FILE = "./found/found_keys.txt"
PUZZLE_ADDRESSES_FILE = "./target_addresses.json"

# Load puzzle addresses from JSON file
with open(PUZZLE_ADDRESSES_FILE, "r") as f:
    PUZZLE_ADDRESSES = json.load(f)

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

    # Use pycryptodome's RIPEMD160 instead of hashlib
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
        print(f"Error fetching balance for address {addr}: {error}")
        return [0, 0, 0]
    except KeyError as error:
        print(f"Error parsing balance data for address {addr}: {error}")
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

        print(f"Checking: {private_key} -> {address} | Balance: {balance}")

        if address in PUZZLE_ADDRESSES or balance > 0:
            print(f"🎉 MATCH FOUND! Private Key: {private_key} -> Address: {address} (Balance: {balance})")
            with open(FOUND_FILE, "a") as f:
                f.write(f"{private_key} -> {address} | Balance: {balance}\n")

        # Save progress every 1000 attempts
        if attempts % 1000 == 0:
            save_progress(private_key)

        attempts += 1
        current_key += 1

brute_force()

