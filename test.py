from web3 import Web3
import requests
import json
from decimal import Decimal

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

# Kết nối Web3
infura_url = "https://bsc-dataseed.binance.org/"  # Hoặc Infura nếu trên Ethereum
web3 = Web3(Web3.HTTPProvider(infura_url))

# Địa chỉ contract của NonfungiblePositionManager trên BSC
NONFUNGIBLE_POSITION_MANAGER = Web3.to_checksum_address("0x46A15B0b27311cedF172AB29E4f4766fbE7F4364")  # Điền contract đúng của PancakeSwap

POOL_CONTRACT_ADDRESS = Web3.to_checksum_address("0x06aC8EE32BCdcE6bF2eA82D9Bfb932a84D45BFcb")

MASTERCHEF_CONTRACT_ADDRESS = Web3.to_checksum_address("0x556B9306565093C855AEA9AE92A594704c2Cd59e")

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

def get_amounts_from_liquidity(liquidity, sqrt_price_x96, tick_lower, tick_upper):
    """
    Tính toán số lượng token0 và token1 từ thanh khoản (liquidity)
    """
    sqrt_price = Decimal(sqrt_price_x96) / 2**96
    sqrt_price_lower = Decimal(1.0001**tick_lower).sqrt()
    sqrt_price_upper = Decimal(1.0001**tick_upper).sqrt()

    if sqrt_price <= sqrt_price_lower:
        amount0 = liquidity * (sqrt_price_upper - sqrt_price_lower) / (sqrt_price_lower * sqrt_price_upper)
        amount1 = 0
    elif sqrt_price < sqrt_price_upper:
        amount0 = liquidity * (sqrt_price_upper - sqrt_price) / (sqrt_price * sqrt_price_upper)
        amount1 = liquidity * (sqrt_price - sqrt_price_lower)
    else:
        amount0 = 0
        amount1 = liquidity * (sqrt_price_upper - sqrt_price_lower)

    return amount0, amount1

def get_pancakeswap_pool_data(pool_address):
    API_URL = f"https://explorer.pancakeswap.com/api/cached/pools/bsc/{pool_address}"
    
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Check error HTTP
        data = response.json()
        
        if "id" in data:
            # print(json.dumps(data, indent=4))  
            return data
        else:
            print("❌ Pool data not found")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None
    
def get_pancakeswap_apr_pool(pool_address):
    API_URL = f"https://explorer.pancakeswap.com/api/cached/pools/apr/v3/bsc/{pool_address}"
    
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Check error HTTP
        data = response.json()
        
        if "apr24h" in data:
            # print(json.dumps(data, indent=4))  
            return data
        else:
            print("❌ Pool data not found")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None

position_id = 1547267

# ABI rút phí từ position NFT
ABI = get_abi("BNB", NONFUNGIBLE_POSITION_MANAGER)  # Lấy ABI từ Etherscan
pool_abi = get_abi("BNB", POOL_CONTRACT_ADDRESS)

contract = web3.eth.contract(address=NONFUNGIBLE_POSITION_MANAGER, abi=ABI)
pool_contract = web3.eth.contract(address=POOL_CONTRACT_ADDRESS, abi=pool_abi)

pool_data = get_pancakeswap_pool_data(POOL_CONTRACT_ADDRESS)
apr_pool = get_pancakeswap_apr_pool(POOL_CONTRACT_ADDRESS)

apr_24h = apr_pool["apr24h"]
apr_7d = apr_pool["apr7d"]
print(f"APR 24h: {float(apr_24h) * 100}")
print(f"APR 7d: {float(apr_7d) * 100}")

print(f"LP Fee APR of Pool: {float(apr_24h) * 100}")
print(f"LP Fee APR of Pool Farm: {float(apr_7d) * 100}")

liquidity = contract.functions.positions(position_id).call()[7]
print(f"Liquidity: {liquidity}")
# fee = pool_contract.functions.fee().call() / 1e6
pool_liquidity = pool_contract.functions.liquidity().call()
print(f"Pool Liquidity: {pool_liquidity}")
# volume_24h = float(pool_data["volumeUSD24h"])
# tvl = float(pool_data["tvlUSD"])

# fee_24h = volume_24h * 0.01
# print(f"Fee 24h: {fee_24h}")

# fee_per_year = fee_24h * 365
# print(f"Fee per year: {fee_per_year}")

# lp_fee_apr = (fee_per_year / tvl) * 100
# print(f"LP Fee APR: {lp_fee_apr / 100}")

liquidity_shared  = liquidity / pool_liquidity
print(f"Liquidity shared: {liquidity_shared}")

lp_fee_position = liquidity_shared * (float(apr_24h) * 100)
print(f"✅ LP Fee APR of Position: {lp_fee_position}")




# ID của vị thế NFT
# position_id = 1547267  # Thay bằng vị thế cụ thể của bạn

# Gọi hàm collect() ở chế độ view để xem số lượng phí có thể nhận
# fees = contract.functions.collect(
#     (position_id, "0x0000000000000000000000000000000000000000", 2**128-1, 2**128-1)
# ).call()

# token0_fees, token1_fees = fees[0], fees[1]
# print(f"Unclaimed Fees Token0: {token0_fees/1e18}")
# print(f"Unclaimed Fees Token1: {token1_fees/1e18}")

# # ID của vị thế NFT
# position_id = 1547267  # Thay bằng ID thực tế

# # Lấy dữ liệu vị thế
# position = contract.functions.positions(position_id).call()
# slot0 = pool_contract.functions.slot0().call()

# sqrt_price_x96 = slot0[0]

# In ra dữ liệu
# liquidity = position[7]
# token0_address = position[2]
# token1_address = position[3]
# fee = position[4]
# tick_lower = position[5]
# tick_upper = position[6]

# print(f"Liquidity: {liquidity}")
# print(f"Token0: {token0_address}")
# print(f"Token1: {token1_address}")
# print(f"Fee Tier: {fee}")
# print(f"Tick Lower: {tick_lower}, Tick Upper: {tick_upper}")

# print(f"sqrt_price_x96: {sqrt_price_x96}")

# # Tính toán số lượng token
# amount_token0, amount_token1 = get_amounts_from_liquidity(liquidity, sqrt_price_x96, tick_lower, tick_upper)

# print(f"Token0 Amount: {amount_token0/10**18}")
# print(f"Token1 Amount: {amount_token1/10**18}")
