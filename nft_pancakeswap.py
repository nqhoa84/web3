from web3 import Web3
from eth_utils import keccak, to_bytes, to_hex
from eth_abi import encode
import requests
import json
import math

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

RPC_URL = "https://bsc-dataseed.binance.org/"  # Hoặc Infura/NodeReal
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# PancakeSwap V3 NFT Position Manager contract (BSC Mainnet)
CONTRACT_ADDRESS = "0x46a15b0b27311cedf172ab29e4f4766fbe7f4364"  # Cập nhật đúng địa chỉ

# Thông tin của PancakeSwap V3 trên BSC
FACTORY_ADDRESS = "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865"

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

def get_position_status(liquidity, tick_lower, tick_upper, current_tick, tokens_owed0, tokens_owed1):
    if liquidity > 0:
        if tick_lower <= current_tick <= tick_upper:
            return "Active"
        else:
            return "Out of Range"
    elif tokens_owed0 > 0 or tokens_owed1 > 0:
        return "Inactive"
    else:
        return "Closed"

def get_pancakeswap_pool_data(pool_address):
    API_URL = f"https://explorer.pancakeswap.com/api/cached/pools/bsc/{pool_address}"
    
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Check error HTTP
        data = response.json()
        
        if "id" in data:
            print(json.dumps(data, indent=4))  
            return data
        else:
            print("❌ Pool data not found")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None

def get_price_tokens(operator_address, token0_address):
    PRICE_TOKENS_API = f"https://wallet-api.pancakeswap.com/v1/prices/list/56%3A{operator_address}%2C56%3A{token0_address}"
    
    try:
        response = requests.get(PRICE_TOKENS_API)
        response.raise_for_status()  # Check error HTTP
        data = response.json()
        
        if "56:"+operator_address in data:
            print(json.dumps(data, indent=4))  
            return data
        else:
            print("❌ Token price data not found")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None

def tick_to_price(tick):
    """
    Chuyển đổi tick sang giá theo công thức: price = 1.0001^tick
    """
    return math.pow(1.0001, tick)

def calculate_min_max_price(tick_lower, tick_upper):
    min_price = tick_to_price(tick_lower)
    max_price = tick_to_price(tick_upper)
    return min_price, max_price

def amount_tokens(tick_lower, tick_upper, current_tick, liquidity):
    # Calculate min and max price range
    p_lower = tick_to_price(tick_lower)
    p_upper = tick_to_price(tick_upper)
    p_current = tick_to_price(current_tick)

    # Compute token amounts based on whether we are in range or not
    if tick_lower <= current_tick <= tick_upper:
        # In range: Calculate both token0 and token1 amounts
        amount_token0 = liquidity * (math.sqrt(p_upper) - math.sqrt(p_current)) / (math.sqrt(p_upper) * math.sqrt(p_current))
        amount_token1 = liquidity * (math.sqrt(p_current) - math.sqrt(p_lower))
    else:
        # Out of range: Only one token is available
        if current_tick < tick_lower:
            amount_token0 = liquidity * (math.sqrt(p_upper) - math.sqrt(p_lower)) / (math.sqrt(p_upper) * math.sqrt(p_lower))
            amount_token1 = 0
        else:
            amount_token0 = 0
            amount_token1 = liquidity * (math.sqrt(p_upper) - math.sqrt(p_lower))

    # Convert to human-readable format (assuming 18 decimals for both tokens)
    amount_token0 /= (10**18)
    amount_token1 /= (10**18)
    
    return amount_token0, amount_token1

# ABI and Contract instance of PancakeSwap V3 NFT Position Manager contract (BSC Mainnet)
abi_position = get_abi("BNB", CONTRACT_ADDRESS)
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi_position)

# ABI and contract instance of PancakeSwap V3 Factory contract (BSC Mainnet)
abi_factory = get_abi("BNB", FACTORY_ADDRESS)
factory_contract = w3.eth.contract(address=Web3.to_checksum_address(FACTORY_ADDRESS), abi=abi_factory)

# Lấy dữ liệu NFT ID 1547267
nft_id = 1547267
position_data = contract.functions.positions(nft_id).call()

operator = Web3.to_checksum_address(position_data[1])
token0 = Web3.to_checksum_address(position_data[2])
token1 = Web3.to_checksum_address(position_data[3])
fee = position_data[4]
liquidity = position_data[7]
tick_lower = position_data[5]
tick_upper = position_data[6]
tokens_owed0 = position_data[10]
tokens_owed1 = position_data[11]

fee_growth0 = position_data[8]
fee_growth1 = position_data[9]
print(f"fee growth 0: {fee_growth0}, fee growth 1: {fee_growth1}")

# Lấy địa chỉ pool từ Factory Contract
pool_address = factory_contract.functions.getPool(token0, token1, fee).call()
print(f"Pool Address: {pool_address}")

# Get API data of pool
pool_data = get_pancakeswap_pool_data(pool_address)

# Get current tick
current_tick = pool_data["tick"]
status = get_position_status(liquidity, tick_lower, tick_upper, current_tick, tokens_owed0, tokens_owed1)

# Pool Contract instance
pool_abi = get_abi("BNB", Web3.to_checksum_address(pool_address))
pool_contract = w3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=pool_abi)

fee_growth_outside0_lower = pool_contract.functions.ticks(tick_lower).call()[2]
fee_growth_outside0_upper = pool_contract.functions.ticks(tick_upper).call()[2]
fee_growth_outside1_lower = pool_contract.functions.ticks(tick_lower).call()[3]
fee_growth_outside1_upper = pool_contract.functions.ticks(tick_upper).call()[3]
print(f"fee growth outside 0 lower: {fee_growth_outside0_lower}, fee growth outside 0 upper: {fee_growth_outside0_upper}")
print(f"fee growth outside 1 lower: {fee_growth_outside1_lower}, fee growth outside 1 upper: {fee_growth_outside1_upper}")

fee_growth_global0 = pool_contract.functions.feeGrowthGlobal0X128().call()
fee_growth_global1 = pool_contract.functions.feeGrowthGlobal1X128().call()
print(f"fee growth global 0: {fee_growth_global0}, fee growth global 1: {fee_growth_global1}")


fee_growth_inside0 = fee_growth_global0 - fee_growth_outside0_lower - fee_growth_outside0_upper
fee_growth_inside1 = fee_growth_global1 - fee_growth_outside1_lower - fee_growth_outside1_upper

    
print(f"Fee inside 0: {fee_growth_inside0}")
print(f"Fee inside 1: {fee_growth_inside1}")

unclaimed_fee0 = (fee_growth_inside0 - fee_growth0) * liquidity / (2**128)
unclaimed_fee1 = (fee_growth_inside1 - fee_growth1) * liquidity / (2**128)

# Price tokens 
price_token_data = get_price_tokens(operator, token0)
print(f"Token0: {token0}")
print(f"Price Operator: {price_token_data[f"56:{operator}"]}")
print(f"Price Token0: {price_token_data[f"56:{token0.lower()}"]}")

print(f"Positons data: {position_data} \n \n")

# Min and max price
min_price, max_price = calculate_min_max_price(tick_lower, tick_upper)

# Amount tokens and total liquidity
amount_token0, amount_token1 = amount_tokens(tick_lower, tick_upper, current_tick, liquidity)
price_token0 = price_token_data[f"56:{token0.lower()}"] * amount_token0
price_token1 = price_token_data[f"56:{operator}"] * amount_token1
total_liquidity = price_token0 + price_token1

# Show get data
print(f"Token1 address: {pool_data["token0"]["id"]}, Token1 name: {pool_data["token0"]["name"]}")
print(f"Token2 address: {pool_data["token1"]["id"]}, Token2 name: {pool_data["token1"]["name"]}")
print(f"Status: {status}")
print(f"Fee: {fee}")
print(f"Max Price: {(1/min_price):.2f}")
print(f"Min Price: {(1/max_price):.2f}")
print(f"Current Price(INSP per BNB): {pool_data["token0Price"]}")
print(f"Current Price(BNB per INSP): {pool_data["token1Price"]}")

print(f"Amount Token0: {amount_token0}, Price: {price_token0}")
print(f"Amount Token1: {amount_token1}, Price: {price_token1}")

print(f"Total Liquidity: {total_liquidity}")

print(f"Unclaimed fee token0: {unclaimed_fee0}")
print(f"Unclaimed fee token1: {unclaimed_fee1}")

