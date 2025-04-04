from web3 import Web3
import requests
import json

API_URLS = {
    'ETH': 'https://api.etherscan.io/api',
    'BAS': 'https://api.basescan.org/api',
    'POL': 'https://api.polygonscan.com/api',
    'BNB': 'https://api.bscscan.com/api',
    'ARB': 'https://api.arbiscan.io/api',
    'LIN': 'https://api.lineascan.build/api',
}

# Api keys of each blockchains
API_KEYS = {
    'ETH': '9BZMQYAZVSVKVURIA3SPKDZEYS2DQ4NARU',
    'BAS': 'WFV28BSE1T9C9Q4XFBKJESD4MXDZ322XXH',
    'POL': 'PM8HRYCQZ4QUWC5RVJNWQVBNTBBEIY4A8F',
    'BNB': '1Q1I7XJZDTVQY7BJ91KNE1PQT6C2DDFWHG',
    'ARB': 'AAZFEQ2R2AYXFHV9YVDX4UJ4NKHA43WJP5',
    'LIN': '15V5YKYIH6RCKW6YNT5NG12FZ7FS8CDVS3',
}

# 1. Kết nối tới BSC
provider = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))

# 2. Địa chỉ pool PancakeSwap V3
pool_address = Web3.to_checksum_address("0x06aC8EE32BCdcE6bF2eA82D9Bfb932a84D45BFcb")  # 👉 THAY bằng địa chỉ thật

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

# 3. ABI rút gọn cần thiết
pool_abi = get_abi("BNB", pool_address)

# 4. Tạo contract object
pool_contract = provider.eth.contract(address=pool_address, abi=pool_abi)

# 5. Tick range từ NFT position
tick_lower = -121400  # 👉 Thay bằng tick của bạn
tick_upper = -107200  # 👉 Thay bằng tick của bạn
tick_spacing = 200   # Thường là 10, 60 hoặc 200 – tuỳ fee tier

# 6. Lấy tick hiện tại
slot0 = pool_contract.functions.slot0().call()
current_tick = slot0[1]
print(f"🎯 Current tick: {current_tick}")

if current_tick < tick_lower or current_tick > tick_upper:
    print("⚠️ Giá hiện tại ngoài phạm vi tick của bạn → không có thanh khoản hoạt động.")
else:
    total_liquidity = 0

    for tick in range(tick_lower, tick_upper + 1, tick_spacing):
        tick_data = pool_contract.functions.ticks(tick).call()
        liquidity_net = tick_data[1]  # liquidityNet (int128)
        total_liquidity += liquidity_net

    print(f"✅ Total active liquidity in your range: {total_liquidity}")
