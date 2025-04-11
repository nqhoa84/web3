from web3 import Web3
import json
import requests
import time

API_URLS = {
    'ETH': 'https://api.etherscan.io/api',
    'BAS': 'https://api.basescan.org/api',
    'POL': 'https://api.polygonscan.com/api',
    'BNB': 'https://api.bscscan.com/api',
    'ARB': 'https://api.arbiscan.io/api',
    'LIN': 'https://api.lineascan.build/api',
}

API_KEYS = {
    'ETH': '9BZMQYAZVSVKVURIA3SPKDZEYS2DQ4NARU',
    'BAS': 'WFV28BSE1T9C9Q4XFBKJESD4MXDZ322XXH',
    'POL': 'PM8HRYCQZ4QUWC5RVJNWQVBNTBBEIY4A8F',
    'BNB': '1Q1I7XJZDTVQY7BJ91KNE1PQT6C2DDFWHG',
    'ARB': 'AAZFEQ2R2AYXFHV9YVDX4UJ4NKHA43WJP5',
    'LIN': '15V5YKYIH6RCKW6YNT5NG12FZ7FS8CDVS3',
}

# Kết nối với BSC Node (có thể dùng public node)
bsc_rpc = 'https://bsc-dataseed.binance.org/'
web3 = Web3(Web3.HTTPProvider(bsc_rpc))

# Địa chỉ contract MasterChefV3 (Farm Pool)
farm_address = Web3.to_checksum_address("0x556B9306565093C855AEA9AE92A594704c2Cd59e")

# ABI rút gọn chỉ cần Event
def get_abi(chain, contract_address):
    if chain not in API_URLS or chain not in API_KEYS:
        print(f"❌ No API URL or API Key for {chain}")
        return None
    
    etherscan_url = API_URLS[chain]
    params = {
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
        "apikey": API_KEYS[chain]
    }

    try:
        response = requests.get(etherscan_url, params=params)
        response_json = response.json()

        if response.status_code == 200 and response_json["status"] == "1":
            try:
                abi = json.loads(response_json["result"])
                return abi
            except json.JSONDecodeError:
                print("❌ Error while decoding JSON ABI")
                return None
        else:
            print(f"❌ Don't get ABI: {response_json['result']}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving contract ABI: {e}")
        return None

farm_abi = get_abi("BNB", farm_address)

contract = web3.eth.contract(address=farm_address, abi=farm_abi)

# Event signature hash
event_signature_hash = web3.keccak(text="Deposit(address,uint256)").hex()

# Block range
start_block = 32000000
end_block = web3.eth.block_number
step = 200  # <= giảm xuống nếu vẫn gặp lỗi

staked_token_ids = set()

while start_block < end_block:
    to_block = min(start_block + step - 1, end_block)
    print(f"Fetching logs from block {start_block} to {to_block}...")

    try:
        logs = web3.eth.get_logs({
            "fromBlock": start_block,
            "toBlock": to_block,
            "address": farm_address,
            "topics": [event_signature_hash]
        })

        for log in logs:
            token_id = int(log['topics'][2].hex(), 16)
            staked_token_ids.add(token_id)

    except Exception as e:
        print(f"Error at block {start_block}-{to_block}: {e}")
        time.sleep(1)  # Wait and retry if needed

    start_block += step

print(f"\nFound {len(staked_token_ids)} staked tokenIds")
print("Sample:", list(staked_token_ids)[:10])