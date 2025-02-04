import requests
from web3 import Web3
import json
import time

API_KEY_INFURA = "13ceaec149fe450c8b71b4e377aa2b83"
SMART_CONTRACT_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
API_KEY_TOKEN_ETHERSCAN = "9BZMQYAZVSVKVURIA3SPKDZEYS2DQ4NARU"

contract_address_checksum = Web3.to_checksum_address(SMART_CONTRACT_ADDRESS)

# Connect to Ethereum network 
infura_url = f"https://mainnet.infura.io/v3/{API_KEY_INFURA}"
web3 = Web3(Web3.HTTPProvider(infura_url))

# Check connection to Ethereum network
if web3.is_connected():
    print("Connected to Ethereum network")
else:
    print("Not connected to Ethereum network")  


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

# Create contract instance
contract = web3.eth.contract(address=contract_address_checksum, abi = get_abi(contract_address_checksum))

# Check if ABI contains Transfer event 
def has_transfer_event(abi):
    for entry in abi:
        if entry.get("type") == "event" and entry.get("name") == "Transfer":
            return True
    return False

if has_transfer_event(contract.abi):

    # Fetch transfer events in the last block
    logs = contract.events.Transfer().get_logs(from_block= web3.eth.block_number - 10000, to_block='latest')
    sorted_logs = sorted(logs, key=lambda log: log['blockNumber'], reverse=True)
    limited_logs = sorted_logs[:10]
    for log in limited_logs:
        print(f"Transfer of {web3.from_wei(log['args']['value'], 'ether')} WETH from {log['args']['from']} to {log['args']['to']}")
else:
    print("The ABI does not contain the Transfer event.")


