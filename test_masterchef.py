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

# Kết nối với Binance Smart Chain
BSC_RPC = "https://bsc-dataseed.binance.org/"
web3 = Web3(Web3.HTTPProvider(BSC_RPC))

# Địa chỉ của MasterChef V3 Contract
MASTER_CHEF_ADDRESS = Web3.to_checksum_address("0x556B9306565093C855AEA9AE92A594704c2Cd59e")  # Thay bằng địa chỉ hợp đồng thực tế

POOL_ADDRESS =  Web3.to_checksum_address("0x06aC8EE32BCdcE6bF2eA82D9Bfb932a84D45BFcb")

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

def get_pancakeswap_reward():
    API_URL = f"https://trading-reward.pancakeswap.com/api/v1/reward/campaignId/20240701/type/rb"
    
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Check error HTTP
        data = response.json()
        
        if "code" in data:
            # print(json.dumps(data, indent=4))  
            return data
        else:
            print("❌ reward data not found")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None

def get_infos_pool(pool_address):
    API_URL = f"https://explorer.pancakeswap.com/api/cached/pools/bsc/{pool_address}"
    
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Check error HTTP
        data = response.json()
        
        if "id" in data: 
            return data
        else:
            print("❌ Pool data not found")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None
    

def get_cake_price_usd():
    API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=pancakeswap-token&vs_currencies=usd"
    response = requests.get(API_URL)
    data = response.json()
    return data["pancakeswap-token"]["usd"]

# ABI của MasterChef V3 Contract
master_chef_abi = get_abi('BNB', MASTER_CHEF_ADDRESS)

# Kết nối với MasterChef contract
masterchef_contract = web3.eth.contract(address=MASTER_CHEF_ADDRESS, abi=master_chef_abi)

# ID của pool bạn muốn kiểm tra
pid = 124  # Thay bằng ID của pool thực tế

position_id = 1547267

# Lấy thông tin về pool
pool_info = masterchef_contract.functions.poolInfo(pid).call()

user_position_infos = masterchef_contract.functions.userPositionInfos(position_id).call()
total_liquidity_position_stake = float(user_position_infos[0]) / 1e18
print(f"✅ Tổng thanh khoản của position đã staking: {total_liquidity_position_stake}")

pool_info = masterchef_contract.functions.poolInfo(pid).call()
total_liquidity_pool_stake = float(pool_info[5]) / 1e18
print(f"✅ Tổng thanh khoản của Pool bao gồm cả in-range và out-of-range: {total_liquidity_pool_stake}")

# Lấy số lượng phần thưởng mỗi giây
cake_per_second, end_time = masterchef_contract.functions.getLatestPeriodInfoByPid(pid).call()

# reward_data = get_pancakeswap_reward()
# # Giá của CAKE (giá thị trường, có thể lấy từ API hoặc giá thực tế)
# reward_price = float(reward_data['data']['rewardPrice']) / 1e18  # Giá CAKE (cần lấy từ nguồn khác)
# print(f"Reward price: {reward_price}")

# Get CAKE price
cake_price_usd = get_cake_price_usd()
print(f"CAKE price: {cake_price_usd}")

total_reward_per_year = float(cake_per_second / 10**30) * (365*24*60*60) * cake_price_usd
print(f"✅ Amount reward per year: {total_reward_per_year}")

# total tokens locked of pool
pool_data = get_infos_pool(POOL_ADDRESS)

tvl_usd = pool_data["tvlUSD"]
print(f"✅ Total Tokens Locked: {tvl_usd}")

# Farm APR of Pool
farm_apr_pool = (total_reward_per_year / float(total_liquidity_pool_stake)) * 100
print(f"✅ Farm APR of Pool: {farm_apr_pool}%")