from web3 import Web3
from eth_utils import keccak, to_bytes, to_hex
from eth_abi import encode
import requests
import json
import math
from list_transactions import get_mint_transactions
from decimal import Decimal

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

RPC_URL = "https://bsc-dataseed.binance.org/" 
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# PancakeSwap:Nonfungible Position Manager V3 contract address(BSC Mainnet)
NPM_ADDRESS = Web3.to_checksum_address("0x46a15b0b27311cedf172ab29e4f4766fbe7f4364")

# PancakeSwap: Masterchef V3 contract address 
MASTERCHEF_ADDRESS = Web3.to_checksum_address("0x556B9306565093C855AEA9AE92A594704c2Cd59e")

# PancakeSwap: Pool contract address
POOL_ADDRESS =  Web3.to_checksum_address("0x06aC8EE32BCdcE6bF2eA82D9Bfb932a84D45BFcb")

# PancakeSwap: Factory V3 contract address
FACTORY_ADDRESS = "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865"

# NFT id of NFT Position Liquidity on PancakeSwap
TOKEN_ID = 1547267

# Get ABI of contract address
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

# Get position status
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

# Get pool data from ABI of PancakeSwap
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

# Get price of tokens
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

# Get apr of pool
def get_pancakeswap_apr_pool_data(pool_address):
    API_URL = f"https://explorer.pancakeswap.com/api/cached/pools/apr/v3/bsc/{pool_address}"
    
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Check error HTTP
        data = response.json()
        
        if "apr24h" in data: 
            return data
        else:
            print("❌ APR of pool data not found")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None

# Convert ticks to prices using the formula: price = 1.0001^tick
def tick_to_price(tick):
    return math.pow(1.0001, tick)

# Calculate the minimum and maximum price range
def calculate_min_max_price(tick_lower, tick_upper):
    min_price = tick_to_price(tick_lower)
    max_price = tick_to_price(tick_upper)
    return min_price, max_price

# Calculate amount token0 and token1 from liquidity in smart contract Position
def get_amounts_from_liquidity(liquidity, sqrt_price_x96, tick_lower, tick_upper):
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

# Get name of token contract address
def get_name_contract_address(pool_address, contract_address):

    pool_data = get_pancakeswap_pool_data(pool_address)
    if pool_data:
        # Kiểm tra nếu contract_address là token0 hoặc token1 trong pool
        if pool_data.get("token0") and pool_data["token0"].get("id") == contract_address:
            return pool_data["token0"].get("name", "Unknown Token Name")
        elif pool_data.get("token1") and pool_data["token1"].get("id") == contract_address:
            return pool_data["token1"].get("name", "Unknown Token Name")
    return "Unknown Token Name"

# Get CAKE price USD
def get_cake_price_usd():
    API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=pancakeswap-token&vs_currencies=usd"
    response = requests.get(API_URL)
    data = response.json()
    return data["pancakeswap-token"]["usd"]

# ABI and Contract instance of PancakeSwap V3 NFT Position Manager contract (BSC Mainnet)
abi_position = get_abi("BNB", NPM_ADDRESS)
contract = w3.eth.contract(address=Web3.to_checksum_address(NPM_ADDRESS), abi=abi_position)

# ABI and contract instance of PancakeSwap V3 Factory contract (BSC Mainnet)
abi_factory = get_abi("BNB", FACTORY_ADDRESS)
factory_contract = w3.eth.contract(address=Web3.to_checksum_address(FACTORY_ADDRESS), abi=abi_factory)

# ABI and contract instance of Masterchef V3 contract (BSC Mainnet)
abi_masterchef = get_abi("BNB", MASTERCHEF_ADDRESS)
masterchef_contract = w3.eth.contract(address=Web3.to_checksum_address(MASTERCHEF_ADDRESS), abi=abi_masterchef)

# ABI and contract instance of Pool contract (BSC Mainnet)
abi_pool = get_abi("BNB", POOL_ADDRESS)
pool_contract = w3.eth.contract(address=Web3.to_checksum_address(POOL_ADDRESS), abi=abi_pool)

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

# Get pool address from Factory Contract
pool_address = factory_contract.functions.getPool(token0, token1, fee).call()
print(f"Pool Address: {pool_address}")

# Get API data of pool
pool_data = get_pancakeswap_pool_data(pool_address)
token0_name = pool_data["token0"]["name"]
token1_name = pool_data["token1"]["name"]
token0_decimal = pool_data["token0"]["decimals"]
token1_decimal = pool_data["token1"]["decimals"]
print(f"Token 0 decimal: {token0_decimal}")
print(f"Token 1 decimal: {token1_decimal}")

# Get current tick
current_tick = pool_data["tick"]
status = get_position_status(liquidity, tick_lower, tick_upper, current_tick, tokens_owed0, tokens_owed1)

# Pool Contract instance
pool_abi = get_abi("BNB", Web3.to_checksum_address(pool_address))
pool_contract = w3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=pool_abi)
slot0 = pool_contract.functions.slot0().call()
sqrt_price_x96 = slot0[0]

# Get Mint transaction
mint_transactions, action, time_stamp_formatted, tx_hash_mint = get_mint_transactions(NPM_ADDRESS, nft_id, API_KEYS["BNB"])

# Price tokens 
price_token_data = get_price_tokens(operator, token0)
print(f"Token0: {token0}")
print(f"Price Operator: {price_token_data[f"56:{operator}"]}")
print(f"Price Token0: {price_token_data[f"56:{token0.lower()}"]}")

print(f"Positons data: {position_data} \n \n")

# Min and max price
min_price, max_price = calculate_min_max_price(tick_lower, tick_upper)

# Amount tokens and total liquidity
amount_token0, amount_token1 = get_amounts_from_liquidity(liquidity, sqrt_price_x96, tick_lower, tick_upper)
amount_token0_decimal = amount_token0 / 10**token0_decimal
amount_token1_decimal = amount_token1 / 10**token1_decimal
price_token0 = Decimal(price_token_data[f"56:{token0.lower()}"]) * amount_token0_decimal
price_token1 = Decimal(price_token_data[f"56:{operator}"] )* amount_token1_decimal
total_liquidity = price_token0 + price_token1

# Amount tokens unclaimed and Unclaimed fees
fees = contract.functions.collect(
    (nft_id, operator, 2**128-1, 2**128-1)
).call()

unclaimed_fee_token0 = fees[0] / 10**token0_decimal
unclaimed_fee_token1 = fees[1] / 10**token1_decimal

price_unclaimed_fee_token0 = unclaimed_fee_token0 * price_token_data[f"56:{token0.lower()}"]
price_unclaimed_fee_token1 = unclaimed_fee_token1 * price_token_data[f"56:{operator}"]
total_unclaimed_fees = price_unclaimed_fee_token0 + price_unclaimed_fee_token1

# Get pool address pip from masterchef V3
pool_address_pip = masterchef_contract.functions.v3PoolAddressPid(pool_address).call()

# Get total staked liquidity of pool
total_staked_liquidity_pool = masterchef_contract.functions.poolInfo(pool_address_pip).call()[5]

# Get staked liquidity of position
staked_liquidity_position = masterchef_contract.functions.userPositionInfos(TOKEN_ID).call()[0]
print(f"✅ Tổng thanh khoản của position: {staked_liquidity_position}")

# Get cake reward per second 
cake_price = get_cake_price_usd()
cake_per_second = masterchef_contract.functions.getLatestPeriodInfo(pool_address).call()[0]
cake_per_second_convert = Decimal(cake_per_second)/10**30
cake_per_year = cake_per_second_convert * (365*24*60*60) * Decimal(cake_price)

rate_position = (Decimal(staked_liquidity_position) / Decimal(total_staked_liquidity_pool))
cake_per_year_position = cake_per_year * rate_position

boost_multiplier = masterchef_contract.functions.userPositionInfos(TOKEN_ID).call()[8]

liquidity_position_usd = Decimal(staked_liquidity_position/10**18)
# Position Farm APR
base_farm_apr_position = (cake_per_year_position / liquidity_position_usd) * 100
farm_apr_position = base_farm_apr_position * (Decimal(boost_multiplier)/10**12)
print(f"*** APRs BLOCK ***")
print(f"Position Farm APR: {round(farm_apr_position, 2)}")

# Get apr of pool data
apr_pool_data = get_pancakeswap_apr_pool_data(pool_address)
fee_usd_24h = pool_data["feeUSD24h"]
apr_24h = apr_pool_data["apr24h"]
apr_7d = apr_pool_data["apr7d"]
liquidity_pool_in_range = pool_data["liquidity"]
fee_tier = (Decimal(fee) / 10**6)

# LP Fee APR of Position
fee_per_year_position = (Decimal(fee_usd_24h) * rate_position) * 365
lp_fee_apr_position = (fee_per_year_position / total_liquidity) * 100

print(f"Position LP Fee APR: {round(lp_fee_apr_position, 2)}")
print(f"Combined APR: {round((lp_fee_apr_position + farm_apr_position), 2)} \n")
print(f"Pool LP Fee APR: {round((float(apr_24h) * 100), 2)}")
print(f"Farm pool LP Fee APR: {round((float(apr_7d) * 100), 2)}\n\n")

# Show data
print(f"*** TOKEN INFO BLOCK ***")
print(f"Token 1 address: {pool_data["token0"]["id"]}, Token1 name: {pool_data["token0"]["name"]}")
print(f"Token 2 address: {pool_data["token1"]["id"]}, Token2 name: {pool_data["token1"]["name"]}")
print(f"Status: {status}")
print(f"Fee: {fee}")

print("\n")

print(f"*** LIQUIDITY BLOCK ***")
print(f"Total Liquidity: {round(total_liquidity, 2)}")
print(f"Amount Token 0: {round(amount_token0_decimal)}, Price: {round(price_token0, 2)}")
print(f"Amount Token 1: {round(amount_token1_decimal, 4)}, Price: {round(price_token1, 2)}")

print("\n")

print(f"*** UNCLAIMED FEES BLOCK ***")
print(f"Unclaimed fees: {round(total_unclaimed_fees, 2)}")
print(f"Unclaimed fee token 0: {round(unclaimed_fee_token0)}, Price: {round(price_unclaimed_fee_token0, 2)}")
print(f"Unclaimed fee token 1: {round(unclaimed_fee_token1, 4)}, Price: {round(price_unclaimed_fee_token1, 2)}")

print("\n")

print(f"*** PRICE RANGE BLOCK ***")
print(f"Max Price: {round(1/min_price)}")
print(f"Min Price: {round((1/max_price), 1)}")
print(f"Current Price(INSP per BNB): {round(float(pool_data["token0Price"]), 1)}")
print(f"Current Price(BNB per INSP): {pool_data["token1Price"]}")

print("\n")

print(f"*** TRANSACTION LIQUIDITY BLOCK ***")
print(f"TimeStamp: {time_stamp_formatted}")
print(f"Action: {action}")
print(f"Transaction Hash: {tx_hash_mint}")
for tx in mint_transactions:
    # print(f"Transaction Hash: {tx['transaction_hash']}")
    print(f"Token Contract: {tx['token_contract']}, Token Name: {get_name_contract_address(pool_address, tx['token_contract'])}")
    # print(f"From: {tx['from_address']}")
    # print(f"To: {tx['to_address']}")
    if(tx['token_contract'] == token0.lower()):
        print(f"Amount: {round(float(tx['value']), 1)} tokens")
    if(tx['token_contract'] == token1.lower()):
        print(f"Value: {round(float(tx['value']), 6)} tokens")
    # print(f"TimeStamp: {tx['time_stamp']}")
    # print(f"Action: {tx['action']} \n")