import os
import requests
import json
from bitcoinlib.keys import Key
from bitcoinlib.networks import Network

# Network (mainnet, testnet, etc.)
network = Network('bitcoin')  # Use 'bitcoin' for mainnet

# Load targets from JSON file
def load_targets():
    try:
        with open("./targets.json", "r") as file:
            targets = json.load(file)
            print("Targets loaded successfully:")
            for target in targets:
                print(f"Startwith: {target['startwith']}, Endwith: {target['endwith']}")
            return targets
    except FileNotFoundError:
        print("Error: 'targets.json' file not found.")
        return []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in 'targets.json'.")
        return []

# Load preloaded addresses from JSON file
def load_preloaded_addresses():
    try:
        with open("./target_addresses.json", "r") as file:
            addresses = json.load(file)
            print("Preloaded addresses loaded successfully:")
            for address in addresses:
                print(address)
            return addresses
    except FileNotFoundError:
        print("Error: './target_addresses.json' file not found.")
        return []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in 'preloaded_addresses.json'.")
        return []

# Load targets and preloaded addresses
targets = load_targets()
preloaded_addresses = load_preloaded_addresses()

if not targets and not preloaded_addresses:
    print("No targets or preloaded addresses found. Exiting.")
    exit()

# Function to get balance using Blockstream API
def get_balance(addr):
    try:
        url = f"https://blockstream.info/api/address/{addr}"  # Use mainnet if needed
        response = requests.get(url, timeout=10)  # Add a timeout to prevent hanging
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        funded_txo_sum = data['chain_stats']['funded_txo_sum']
        spent_txo_sum = data['chain_stats']['spent_txo_sum']
        balance = funded_txo_sum - spent_txo_sum
        return [balance, funded_txo_sum, spent_txo_sum]
    except requests.exceptions.RequestException as error:
        print(f"Error fetching balance for address {addr}: {error}")
        return [0, 0, 0]  # Return default values on error
    except KeyError as error:
        print(f"Error parsing balance data for address {addr}: {error}")
        return [0, 0, 0]  # Return default values on error

# Function to generate a random private key
def generate_private_key():
    private_key = os.urandom(32).hex()
    return private_key

# Function to generate a Bitcoin address from a private key
def generate_address(private_key):
    key = Key(private_key, network=network)
    address = key.address()
    return address

# Function to check if the private key matches any target conditions
def is_private_key_match(private_key):
    for target in targets:
        starts_with_condition = private_key.startswith(target["startwith"])
        ends_with_condition = private_key.endswith(target["endwith"])
        if starts_with_condition and ends_with_condition:
            return True, target
    return False, None

# Function to check if the address matches any preloaded addresses
def is_address_match(address):
    if address in preloaded_addresses:
        return True
    return False

# Function to save results to a JSON file
def save_to_json(file_name, data):
    try:
        with open(file_name, "r") as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        existing_data = []

    # Append the new data
    existing_data.append(data)

    # Save the updated data to the JSON file
    with open(file_name, "w") as file:
        json.dump(existing_data, file, indent=4)

# Main function to run the puzzle
def run_puzzle():
    attempts = 0
    private_key = None
    address = None

    print("Starting Bitcoin puzzle...")

    while True:
        private_key = generate_private_key()
        address = generate_address(private_key)
        #balance_info = get_balance(address)
        balance = 0 #balance_info[0]
        attempts += 1

        # Print in the specified format: private_key_generated, address_generated, available balance
        print(f"{private_key}, {address}, {balance} satoshis")

        # Check if the address matches any preloaded addresses
        if is_address_match(address):
            print(f"Address match found after {attempts} attempts!")
            print(f"Private Key: {private_key}")
            print(f"Address: {address}")
            print(f"Balance: {balance} satoshis")
            save_to_json("./found/address_matches.json", {
                "private_key": private_key,
                "address": address,
                "balance": balance,
            })

        # Check if the private key matches any target conditions
        private_key_match, target = is_private_key_match(private_key)
        if private_key_match:
            print(f"Private key match found after {attempts} attempts!")
            print(f"Private Key: {private_key}")
            print(f"Address: {address}")
            print(f"Balance: {balance} satoshis")
            print(f"Target: {target}")
            save_to_json("./found/private_key_matches.json", {
                "private_key": private_key,
                "address": address,
                "balance": balance,
                "target": target,
            })

        # Check if the balance is greater than 0
        if balance > 0:
            print(f"Balance > 0 found after {attempts} attempts!")
            print(f"Private Key: {private_key}")
            print(f"Address: {address}")
            print(f"Balance: {balance} satoshis")
            save_to_json("./found/balance_matches.json", {
                "private_key": private_key,
                "address": address,
                "balance": balance,
            })

        if attempts % 1000 == 0:
            print(f"Attempts: {attempts}")

# Run the puzzle
run_puzzle()
