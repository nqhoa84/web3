import requests
from web3 import Web3
import json
import time

API_KEY_INFURA = "13ceaec149fe450c8b71b4e377aa2b83"
SMART_CONTRACT_ADDRESS = "0xc2132d05d31c914a87c6611c10748aeb04b58e8f"
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

# Connect to Smart contract
etherscan_url = "https://api.etherscan.io/api"
params = {
    "module": "contract",
    "action": "getabi",
    "address": contract_address_checksum,
    "apikey": API_KEY_TOKEN_ETHERSCAN
}

# Get ABI result for Smart contract
response = requests.get(etherscan_url, params=params)

if response.status_code == 200:
    abi_json = response.json()
    if abi_json["status"] == "1":
        abi = json.loads(abi_json["result"])
    else:
        print(f"Error retrieving contract ABI: {abi_json['result']}")
        exit()
else:
    print(f"Error retrieving contract ABI: {response.status_code}")
    exit()

# Create contract instance
contract = web3.eth.contract(address=contract_address_checksum, abi = abi)

# Check if ABI contains Transfer event 
def has_transfer_event(abi):
    for entry in abi:
        if entry.get("type") == "event" and entry.get("name") == "Transfer":
            return True
    return False

if has_transfer_event(abi):

    # Fetch transfer events in the last block
    logs = contract.events.Transfer().get_logs(from_block= web3.eth.block_number - 9999999, to_block='latest')

    limited_logs = logs[:10]
    for log in limited_logs:
        print(f"Transfer of {web3.from_wei(log.args._amount, 'ether')} WETH from {log.args._from} to {log.args._to}")
else:
    print("The ABI does not contain the Transfer event.")


