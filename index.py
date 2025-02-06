import requests
import time
import mysql.connector
from datetime import datetime
import json
from web3 import Web3

# Data config setting connect Mysql
data_config = {
    "host": "localhost",          
    "user": "admin",               
    "password": "admin",  
    "database": "infura_io" 
}

# Etherscan API Key 
API_KEY_TOKEN_ETHERSCAN = "9BZMQYAZVSVKVURIA3SPKDZEYS2DQ4NARU"
API_KEY_INFURA = "13ceaec149fe450c8b71b4e377aa2b83"

# Connect to Ethereum network 
infura_url = f"https://mainnet.infura.io/v3/{API_KEY_INFURA}"
web3 = Web3(Web3.HTTPProvider(infura_url))

# Function to check if a contract is verified
def is_contract_verified(contract_address):
    etherscan_url = "https://api.etherscan.io/api"
    params = {
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
        "apikey": API_KEY_TOKEN_ETHERSCAN
    }

    # Get ABI result for Smart Contract
    response = requests.get(etherscan_url, params=params)

    if response.status_code == 200:
        abi_json = response.json()
        if abi_json["status"] == "1" and abi_json["result"] != "Contract source code not verified":
            return True  # Contract is verified
    return False  # Contract is NOT verified

# Get ABI from Etherscan
def get_abi(contract_address):
    etherscan_url = "https://api.etherscan.io/api"
    params = {
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
        "apikey": API_KEY_TOKEN_ETHERSCAN
    }

    response = requests.get(etherscan_url, params=params)

    if response.status_code == 200:
        abi_json = response.json()
        if abi_json["status"] == "1" and abi_json["result"] != "Contract source code not verified":
            abi = json.loads(abi_json["result"])
            return abi
        else:
            print(f"Error retrieving contract ABI: {abi_json['result']}")
            return None
    else:       
        print(f"Error retrieving contract ABI: {response.status_code}")
        return None

# Connect to database
connection = mysql.connector.connect(**data_config)
cursor = connection.cursor()

# Telegram Bot API token and chat ID
api_token = "7541502749:AAHO0ro39ZhMhS8gHFNy9DeKcaE5Ux7CUyU"
chat_id = "5696892272"

# API URL for bonds
api_url = "https://realtime-api.ape.bond/bonds"

# Fetch data from the bonds API
response = requests.get(api_url)
if response.status_code != 200:
    raise Exception("Failed to fetch data from API.")

data = response.json()
if "bonds" not in data:
    raise Exception("No bonds data available in the API response.")

# Process and sort bonds by % bonus
bonds = data["bonds"]
bonds_verified = [bond for bond in bonds if is_contract_verified(bond["billAddress"])]
sorted_bonds = sorted(bonds_verified, key=lambda bond: bond["bonus"], reverse=True)
top_10_bonds = sorted_bonds[:10]

# Bedtime setting
bedtime_start = "22:00"
bedtime_end = "08:00"

# Set Bedtime for sending message
def set_bedtime():
    now = datetime.now().time()
    start = datetime.strptime(bedtime_start, "%H:%M").time()
    end = datetime.strptime(bedtime_end, "%H:%M").time()

    if start <= now or now  < end:
        return True
    return False

# Check if the ABI contains the event
def has_event(abi, event_name):
    for entry in abi:
        if entry.get("type") == "event" and entry.get("name") == event_name:
            return True
    return False

# Fetch Event logs from the contract
def fetch_event_logs(contract, from_block, to_block, event_name):
    logs = getattr(contract.events, event_name).get_logs(from_block=from_block, to_block=to_block)
    return logs

# Get latest transaction block
def get_latest_tx_block(contract_address):
    try:
        url = f"https://api.etherscan.io/api"
        params = {
            "module": "account",
            "action": "txlist",
            "address": contract_address,
            "startblock": "0",
            "endblock": "latest",
            "sort": "desc",
            "apikey": API_KEY_TOKEN_ETHERSCAN
        }
        response = requests.get(url, params=params)
        response_json = response.json()
        txs = response_json.get("result", [])

        if txs:
            return int(txs[0]["blockNumber"])
    except Exception as e:
        print(f"Error while get latest transactions: {e}")

    return None 
        
# Process and check Approval event
def approval_event_user_token(top_10_bonds):
    for bond in top_10_bonds:
        token_user = bond['billAddress']
        event_name = "Approval"
        print(f"Checking Approval events for principal token {token_user}")

        token_user_abi = get_abi(token_user)
        
        # Check abi exists 
        if token_user_abi is None:
            print(f"Skipping {token_user_abi} because its ABI could not be retrieved.")
            continue
        # Check Approval event exists in abi
        if not has_event(token_user_abi, event_name=event_name):
            print(f"No Approval event found for {token_user} Skipping.")
            continue
        
        # Create contract instance
        token_user_contract = web3.eth.contract(address=Web3.to_checksum_address(token_user), abi=token_user_abi)

        latest_block = get_latest_tx_block(token_user)
        from_block = hex(latest_block)
        to_block = "latest"

        # Fetch the Transfer events from the contract
        approval_logs = fetch_event_logs(token_user_contract, from_block, to_block, event_name=event_name)
        sorted_approval_logs = sorted(approval_logs, key=lambda log: log['blockNumber'], reverse=True)
        limited_approval_logs = sorted_approval_logs[:10]

        # Processing logs of Approval events
        for log in limited_approval_logs:
            args = log.get("args", {})

            # Approved a transfer of tokens, the amount approved, and the recipient of the approval.
            sender = args.get("_owner") or args.get("owner") or args.get("src")
            receiver = args.get("_spender") or args.get("spender") or args.get("dst")
            amount = args.get("_value") or args.get("value") or args.get("wad") or args.get("_amount")

            if amount:
                print(f"{sender} approved {web3.from_wei(amount, 'ether')} tokens for {receiver}")
            else:
                print("Unknown approval event structure")

# Process and check transfer event
def transfer_event_user_token(top_10_bonds):
    for bond in top_10_bonds:
        user_token = bond['principalToken']
        event_name = "Transfer"
        print(f"Checking Transfer events for principal token: {user_token}")
        
        token_abi = get_abi(user_token)
        
        if token_abi is None:
            print(f"Skipping {user_token} because its ABI could not be retrieved.")
            continue
        
        if not has_event(token_abi, event_name=event_name):
            print(f"No Transfer event found for {user_token} Skipping.")
            continue
        
        token_contract = web3.eth.contract(address=Web3.to_checksum_address(user_token), abi=token_abi)

        latest_block = get_latest_tx_block(user_token)
        from_block = hex(latest_block)
        to_block = "latest"
        
        # Fetch the Transfer events from the contract
        transfer_logs = fetch_event_logs(token_contract, from_block, to_block, event_name=event_name)
        sorted_transfer_logs = sorted(transfer_logs, key=lambda log: log['blockNumber'], reverse=True)
        limited_transfer_logs = sorted_transfer_logs[:10]

        for log in limited_transfer_logs:
            args = log.get("args", {})

            amount = args.get("_value") or args.get("value") or args.get("wad")
            sender = args.get("_from") or args.get("from") or args.get("src")
            receiver = args.get("_to") or args.get("to") or args.get("dst")

            if amount:
                print(f"Transfer of {web3.from_wei(amount, 'ether')} WETH from {sender} to {receiver}")
            else:
                print("Unknown transfer event structure")

        
# Schedule send message and save to database to Telegram
def schedule_send_message():
    # Build the message
    text_message = "🚀 **Danh sách 10 bond có % bonus cao nhất** 🚀\n\n"
    text_message += "*Thông tin các bond:* \n"
    for index, bond in enumerate(top_10_bonds, start=1):
        bond_name = f"{bond['principalTokenName']}-{bond['payoutTokenName']}"
        contract_address = bond["billAddress"]
        user_token = bond["principalToken"]
        payout_token = bond['payoutToken']
        date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())  # Current time
        bonus = f"{bond['bonus']:.2f}"
        min_price = f"{float(bond['trueBillPrice']) / (10 ** int(bond['principalTokenDecimals'])):,.2f}"
        max_price = f"{float(bond['maxTotalPayout']) / (10 ** int(bond['payoutTokenDecimals'])):,.2f}"
        max_buy = f"{float(bond['maxPayout']) / (10 ** int(bond['payoutTokenDecimals'])):,.2f}"

        # Insert data to database
        insert_query = """
            INSERT INTO bond_history (bond_name, contract_address, date_time, bonus, min_price, max_price, max_buy)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        data = (bond_name, contract_address, date_time, bonus, min_price.replace(",",""), max_price.replace(",",""), max_buy.replace(",",""))
        cursor.execute(insert_query, data)

        text_message += f"Bond #{index}:\n"
        text_message += f"➡️ **Bond Name**: {bond_name}\n"
        text_message += f"➡️ **Contract Address**: {contract_address}\n"
        text_message += f"➡️ **User Token**: {user_token}\n"
        text_message += f"➡️ **Payout Token**: {payout_token}\n"
        text_message += f"➡️ **Date-time**: {date_time}\n"
        text_message += f"➡️ **Bonus**: {bonus}%\n"
        text_message += f"➡️ **Min Price**: {min_price} USDC\n"
        text_message += f"➡️ **Max Price**: {max_price} GPT\n"
        text_message += f"➡️ **Max Buy**: {max_buy} GPT\n"
        text_message += "─" * 40 + "\n"

    # Send the message to Telegram
    telegram_url = f"https://api.telegram.org/bot{api_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text_message,
        "parse_mode": "Markdown",  # Use Markdown for formatting
    }

    try:
        telegram_response = requests.post(telegram_url, data=payload)
        print(f"Response from Telegram: {telegram_response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message to Telegram: {e}")
        
    try:
        # Commit changes to the database
        connection.commit()
        print("Data saved successfully.")

    except mysql.connector.Error as e:
        print(f"Error saving data to the database: {e}")   


if __name__ == "__main__":
    while True:
        if set_bedtime():
            print("It's bedtime. The message will soon be sent in the morning.")
            time.sleep(600)
            continue 
        
        print(" *** Show Transfer *** ")
        transfer_event_user_token(top_10_bonds)
            
        print(" *** Show Approval *** ")
        approval_event_user_token(top_10_bonds)

        schedule_send_message()
        time.sleep(600)