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

def track_bond_bill_event_contract(top_10_bonds):

        # Save data of BillCreated Events
        bill_created_data = {}

        for bond in top_10_bonds:

            # Event name
            billCreated_name = "BillCreated"
            billClaimed_name = "BillClaimed"

            # Get Contract ABI 
            contract_address = bond["billAddress"]
            bond_name = bond["principalTokenName"] +"-"+ bond["payoutTokenName"]
            payout_token_name = bond["payoutTokenName"]
            user_token_name = bond["principalTokenName"]

            contract_abi = get_abi(contract_address)

            print(f"🔍 Checking BillCreated and BillClaimed events for Bond contract {contract_address}: {bond_name}")

            # Check exist ABI and event
            if contract_abi is None:
                print(f"⚠️ Skipping {contract_address} because its ABI could not be retrieved.")
                continue
            if not has_event(contract_abi, event_name=billCreated_name) or not has_event(contract_abi, event_name=billClaimed_name): 
                print(f"⚠️ No BillCreated or BillClaimed event found for {contract_address} Skipping.")
                continue
            
            # Create contract instance
            contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=contract_abi)

            latest_block = get_latest_tx_block(contract_address)
            print(latest_block)
            from_block = 0
            to_block = "latest"

            # Fetch the BillCreated events from the contract
            billCreated_logs = fetch_event_logs(contract, from_block, to_block, event_name=billCreated_name)
            sorted_billCreated_logs = sorted(billCreated_logs, key=lambda log: log['blockNumber'], reverse=True)
            limited_billCreated_logs = sorted_billCreated_logs[:10]
            for log in sorted_billCreated_logs:
                args = log.get("args", {})

                billId = args.get("billId")
                deposit = Web3.from_wei(args.get("deposit"), "ether")
                payout = Web3.from_wei(args.get("payout"), "ether")
                expires = args.get("expires")
                vesting_until_time = datetime.utcfromtimestamp(expires)

                if billId is not None:
                    bill_created_data[args.get("billId")] = {
                        "deposit": deposit,
                        "payout": payout,
                        "expires": vesting_until_time
                    }

            # Fetch the BillClaimed events from the contract
            billClaimed_logs = fetch_event_logs(contract, from_block, to_block, event_name=billClaimed_name)
            sorted_billClaimed_logs = sorted(billClaimed_logs, key=lambda log: log['blockNumber'], reverse=True)
            limited_billClaimed_logs = sorted_billClaimed_logs[:10]
            found_bill = False
            for log in sorted_billClaimed_logs:
                args = log.get("args", {})
                
                billId = args.get("billId")
                recipient = args.get("recipient")
                remaining = Web3.from_wei(args.get("remaining"), "ether")
                payout = Web3.from_wei(args.get("payout"), "ether")

                if billId in bill_created_data and billId is not None:
                    found_bill = True

                    bill_info = bill_created_data[billId]

                    print(f"🔥 Bond Purchased & Claimed! 🔥")
                    print(f"🆔 Bond ID: {billId}") # Unique Bond Id  was purchased
                    print(f"👤 Buyer: {recipient}") # Ethereum address of the buyer who purchased and later claimed the bond
                    print(f"💰 Deposit: {bill_info['deposit']} {user_token_name}") # This is the amount of USDC to (or other token) used to buy bond 
                    print(f"🎁 Payout BillCreated: {bill_info['payout']} {payout_token_name}") # The total payout amount for the bond (wei or eth)
                    print(f"🎁 Payout BillClaimed: {payout} {payout_token_name}") # The actual amount of the payout claimed at the time (may be lower than the original payout from BillCreated if there are vesting rules or partial claims))
                    print(f"⏳ Vesting Until: {bill_info['expires']}") # The timestamp when the bond's vesting ends
                    print(f"✅ Bond Claimed! Remaining: {remaining} {payout_token_name}") # The remaining amount that has yet to be claimed (or the remaining payout if partial claims are allowed).
                    print(f"\n")

            if not found_bill:
                print(f"⚠️ Not found BillClaim info for any Bill ID in contract {contract_address}")   

# Fetch the UpdateClaimApproval from the contract
def approval_event_contract(top_10_bonds):
    for bond in top_10_bonds:
        contract_address = bond["billAddress"]
        event_name = "UpdateClaimApproval"

        abi = get_abi(contract_address)

        if abi is None:
            print(f"⚠️ Skipping {contract_address} because its ABI could not be retrieved.")
            continue

        # Check if "UpdateClaimApproval" event exists in ABI
        if not has_event(abi, event_name=event_name):
            print(f"⚠️ No UpdateClaimApproval event found in contract {contract_address}. Skipping.")
            continue

        # Contract initialization
        contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

        latest_block = web3.eth.block_number
        from_block = 0
        to_block = "latest"

        print(f"🔍 Checking UpdateClaimApproval events from block {from_block} to {to_block}...")

        try:
            # Verify event existence in contract before calling it
            if hasattr(contract.events, event_name):
                approval_event = contract.events.UpdateClaimApproval()
                approval_logs = approval_event.get_logs(from_block=from_block, to_block=to_block)

                if not approval_logs:
                    print("✅ No approval events found in the given range.")
                    continue

                for log in approval_logs:
                    args = log.get("args", {})

                    owner = args.get("owner")
                    approved_account = args.get("approvedAccount")
                    approved = args.get("approved")

                    print(f"✅ Owner: {owner}, Approved Account: {approved_account}, Approved: {approved}")
            else:
                print(f"⚠️ The contract does not have an UpdateClaimApproval event.")
        except Exception as e:
            print(f"❌ Error fetching approval events: {e}")

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

        for log in sorted_transfer_logs:
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
        
        # print(" *** Show Transfer *** ")
        # transfer_event_user_token(top_10_bonds)
            
        # print(" *** Show Approval *** ")
        # approval_event_user_token(top_10_bonds)

        print(" *** Monitor User bought Bond *** ")
        track_bond_bill_event_contract(top_10_bonds)

        print("*** UpdateClaimApproval event")
        approval_event_contract(top_10_bonds)
        
        schedule_send_message()
        time.sleep(600)