import requests
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from eth_account.messages import encode_defunct
import time
import sys

# Etherscan API Key 
API_KEY_INFURA = "13ceaec149fe450c8b71b4e377aa2b83"

# Api urls of blockchains
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

# RPC URLs
RPC_URLS = {
    'ETH': f'https://mainnet.infura.io/v3/{API_KEY_INFURA}',
    'BNB': f'https://bsc-mainnet.infura.io/v3/{API_KEY_INFURA}',
    'POL': f'https://polygon-mainnet.infura.io/v3/{API_KEY_INFURA}',
    'ARB': f'https://arbitrum-mainnet.infura.io/v3/{API_KEY_INFURA}',
    'BAS': f'https://base-mainnet.infura.io/v3/{API_KEY_INFURA}',
    'LIN': f'https://linea-mainnet.infura.io/v3/{API_KEY_INFURA}'
}

    # 'POL': f'https://polygon-rpc.com/',
    # 'ARB': f'https://arb1.arbitrum.io/rpc',

PRIVATE_KEY = "8d2065f47d5e5b15375c0d51d6bab2bc49900d38f548efbe99edb5bf45627c90"
WALLET_ADDRESS = Account.from_key(PRIVATE_KEY).address

BOND_ID = 12801

# BOND CONTRACT ADDRESS
# BOND_CONTRACT_ADDRESS = [
#     '0x13bc2b0eae7a6d3b4de33a47a9570a3830c3f4be',
#     '0x7B0268f91FCC53C0a4F1D47A38f9Aaa106ACc83e',
#     '0x3e53f156fbe6c3a2fae7ad2e4e83e3d4c493944e',
#     '0x54722ded7d08f557af0bfb4ae24418926b123dcd',
#     '0xe4EB50Ab3C8839C1eF46c9F163F07de7405c05BE',
#     '0xf83144584b3de493c214ee765387312ceb94c196'
# ]

BOND_CONTRACT_ADDRESS = [
    "0x0C2946dC2aFa62E92e0f229739CC911Fe9Ef439d"
]

USDC_TOKEN_CONTRACT_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

BASE_UNISWAP_ROUTER_ADDRESS = "0x2626664c2603336E57B271c5C0b26F421741e481" # Base Uniswap V3 Router
BASE_UNISWAP_QUOTER_ADDRESS = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"  # Uniswap V3 QuoterV2 on Base

web3_instances = {chain: Web3(Web3.HTTPProvider(url)) for chain, url in RPC_URLS.items()}
CHAIN_CACHE = {}

# Get chain name from chainlist api
def get_chain_name(chain_id):
    if chain_id in CHAIN_CACHE:
        return CHAIN_CACHE[chain_id]
    
    url = f"https://chainid.network/chains.json"

    try: 
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        chains = response.json()

        for chain in chains:
            if chain["chainId"] == chain_id:
                chain_name = chain["name"][:3].upper()
                CHAIN_CACHE[chain_id] = chain_name
                return chain_name

        return "Unknown Chain"
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching chain name: {e}")
        return "Unknown"

# Get ABI from Etherscan
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

def find_chain_for_contract(contract_address):
    for chain, web3 in web3_instances.items():
        try:
            if web3.eth.get_code(contract_address) != b'':
                chain_id = web3.eth.chain_id
                chain_name = get_chain_name(chain_id)
                print(f"✅ Contract {contract_address} on chain {chain_name} (Chain ID: {chain_id})")
                return chain, chain_name
            
        except Exception as e:
            continue

    print(f"❌ No find chain for contract {contract_address}")
    return None, None

def call_contract_function(chain, contract_address, function_name, *args):
    if chain not in web3_instances:
        print(f"❌ No RPC found for chain {chain}")
        return None

    try:
        web3 = web3_instances[chain]

        # Inject middleware if chain is POA
        if chain in ['BNB', 'POL', 'ARB', 'BAS', 'LIN']:
            if ExtraDataToPOAMiddleware not in web3.middleware_onion:
                web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Get ABI
        abi = get_abi(chain, contract_address)
        if not abi:
            return None

        # Connect to smart contract
        contract = web3.eth.contract(address=contract_address, abi=abi)

        # Check function exists in ABI
        if function_name not in [func["name"] for func in abi if "name" in func]:
            print(f"❌ Function {function_name} not exists in contract {contract_address}")
            return None

        # Call function on contract and get result
        contract_function = contract.functions[function_name](*args)
        result = contract_function.call()

        return result

    except Exception as e:
        print(f"❌ Error calling {function_name} on {contract_address}: {str(e)}")
        return None
    
def transactions_function(chain, contract_address):
    if chain not in web3_instances:
        print(f"❌ No RPC found for chain {chain}")
        return None

    try:
        web3 = web3_instances[chain]

        # Inject middleware if chain is POA
        if chain in ['BNB', 'POL', 'ARB', 'BAS', 'LIN']:
            if ExtraDataToPOAMiddleware not in web3.middleware_onion:
                web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        chain_id = web3.eth.chain_id

        # Get ABI
        abi = get_abi(chain, contract_address)
        if not abi:
            return None

        # Connect to smart contract
        contract = web3.eth.contract(address=contract_address, abi=abi)

        return chain_id, contract

    except Exception as e:
        print(f"❌ Error on {contract_address}: {str(e)}")
        return None

def supports_permit(token_contract):
    try:
        _ = token_contract.functions.DOMAIN_SEPARATOR().call()
        return True
    except:
        return False

def support_deposit_with_permit(bond_contract):
    try:
        _ = bond_contract.functions.depositWithPermit()
        return True
    except:
        return False
    
def can_use_permit(token_contract, bond_contract):
    return supports_permit(token_contract) and support_deposit_with_permit(bond_contract)

def get_implementation_token_address(token_contract_address, chain):
    if chain not in web3_instances:
        print(f"❌ No RPC found for chain {chain}")
        return None
    
    web3 = web3_instances[chain]
    
    # Inject middleware if chain is POA
    if chain in ['BNB', 'POL', 'ARB', 'BAS', 'LIN']:
        if ExtraDataToPOAMiddleware not in web3.middleware_onion:
            web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    proxy_token_contract = web3.eth.contract(address=Web3.to_checksum_address(token_contract_address), abi=get_abi(chain, token_contract_address))
    
    try:
        implementation_address = proxy_token_contract.functions.implementation().call()
        return implementation_address
    except:
        return token_contract_address

def get_usdc_to_principal_rate(uniswap_quoter_contract, amount_approve, usdc_token_contract_address, proxy_token_address):
    try:
        params = {
        "tokenIn": usdc_token_contract_address,
        "tokenOut": proxy_token_address,
        "fee": 3000,  # Pool fee 0.3%
        "amountIn": amount_approve,
        "sqrtPriceLimitX96": 0  # Giá giới hạn, thường đặt là 0 nếu không có yêu cầu cụ thể
        }

        # Gọi hàm với tuple chứa params
        amount_out, _, _ = uniswap_quoter_contract.functions.quoteExactInputSingle(params).call()
        return amount_out
        
    except Exception as e:
        print(f"❌ Lỗi khi lấy tỷ giá swap: {e}")
        return 0


def swap_usdc_to_principal_token(chain, principal_token_address, token_contract_address,usdc_contract, gas_price, amount_in):
    if chain not in web3_instances:
        print(f"❌ No RPC found for chain {chain}")
        return None
    
    print(f"🔄 Swapping {amount_in / 10**6} USDC to {principal_token_address}...")
    
    web3 = web3_instances[chain]

        # Inject middleware if chain is POA
    if chain in ['BNB', 'POL', 'ARB', 'BAS', 'LIN']:
        if ExtraDataToPOAMiddleware not in web3.middleware_onion:
            web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Get abi of Uniswap Router
    uniswap_abi = get_abi(chain, BASE_UNISWAP_ROUTER_ADDRESS)
    
    uniswap_router = web3.eth.contract(address=BASE_UNISWAP_ROUTER_ADDRESS, abi=uniswap_abi)
    
    gas_estimate_approve = usdc_contract.functions.approve(
        BASE_UNISWAP_ROUTER_ADDRESS,
        amount_in
    ).estimate_gas({
        "from": WALLET_ADDRESS
    })
    
    approve_tx = usdc_contract.functions.approve(
        BASE_UNISWAP_ROUTER_ADDRESS,
        amount_in
    ).build_transaction({
        "from": WALLET_ADDRESS,
        "gas": gas_estimate_approve,
        "gasPrice": gas_price,
        "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS)
    })
    
    signed_approve_tx = web3.eth.account.sign_transaction(approve_tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_approve_tx.raw_transaction)
    print(f"✅ Approved USDC to Uniswap Router in {chain}...")
    
    time.sleep(5)
    
    gas_estimate = uniswap_router.functions.exactInputSingle(
    {
        "tokenIn": token_contract_address,
        "tokenOut": principal_token_address,
        "fee": 3000,  # Fee 0.3% (Uniswap V3)
        "recipient": WALLET_ADDRESS,
        "deadline": int(time.time()) + 60,
        "amountIn": amount_in,
        "amountOutMinimum": 0,
        "sqrtPriceLimitX96": 0
    }).estimate_gas({"from": WALLET_ADDRESS})
    print(f"Gas estimate: {gas_estimate}")
    
    tx = uniswap_router.functions.exactInputSingle({
        "tokenIn": token_contract_address,
        "tokenOut": principal_token_address,
        "fee": 3000,  # Fee 0.3% (Uniswap V3)
        "recipient": WALLET_ADDRESS,
        "deadline": int(time.time()) + 60,
        "amountIn": amount_in,
        "amountOutMinimum": 0,
        "sqrtPriceLimitX96": 0
    }).build_transaction({
        "from": WALLET_ADDRESS,
        "gas": gas_estimate,
        "gasPrice": gas_price,
        "nonce": web3.eth.get_transaction_count(WALLET_ADDRESS)
    })
    
    # Sign and send transaction
    signed_txn = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Swap Tx Hash: {web3.to_hex(tx_hash)}")
    
    # Wait for transaction to be confirmed
    web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✅ Swap USDC to {principal_token_address} complete!")

def approve_token(token_contract, spender, amount, web3_chain, gas_price):
    gas_estimate_approve = token_contract.functions.approve(
        spender, amount
    ).estimate_gas({"from": WALLET_ADDRESS})
    print(f"Gas estimate approve: {gas_estimate_approve}")

    # Approve token
    tx_approve = token_contract.functions.approve(spender, amount).build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": web3_chain.eth.get_transaction_count(WALLET_ADDRESS),
        "gas": gas_estimate_approve,
        "gasPrice": gas_price,
        "chainId": web3_chain.eth.chain_id
    })
    signed_tx = web3_chain.eth.account.sign_transaction(tx_approve, private_key=PRIVATE_KEY)
    tx_hash = web3_chain.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Approve Tx Hash: {web3_chain.to_hex(tx_hash)}")
    
def deposit_bond(bond_contract, amount, max_price, web3_chain, gas_price):
    gas_estimate_deposit = bond_contract.functions.deposit(
        amount, max_price, WALLET_ADDRESS
    ).estimate_gas({"from": WALLET_ADDRESS})
    print(f"Gas estimate deposit: {gas_estimate_deposit}")

    # Call deposit to buy bond
    tx = bond_contract.functions.deposit(amount, max_price, WALLET_ADDRESS).build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": web3_chain.eth.get_transaction_count(WALLET_ADDRESS),
        "gas": gas_estimate_deposit,
        "gasPrice": gas_price,
        "chainId": web3_chain.eth.chain_id
    })

    signed_tx = web3_chain.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3_chain.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Deposit Transaction Hash: {web3_chain.to_hex(tx_hash)}")

if __name__ == "__main__":

    for chain, web3 in web3_instances.items():
        try: 
            chain_id = web3.eth.chain_id
            print(f"✅ Connect to {chain} (Chain ID: {chain_id})")
        except Exception as e:
            print(f"❌ Error connecting to {chain}: {str(e)}")
    
    base_uniswap_router_address = Web3.to_checksum_address(BASE_UNISWAP_ROUTER_ADDRESS.lower())
    base_uniswap_quoter_address = Web3.to_checksum_address(BASE_UNISWAP_ROUTER_ADDRESS.lower())
    
    usdc_token_contract_address = Web3.to_checksum_address(USDC_TOKEN_CONTRACT_ADDRESS.lower())
    usdc_chain, usdc_chain_name = find_chain_for_contract(usdc_token_contract_address)
    
    bond_contract_address = Web3.to_checksum_address(BOND_CONTRACT_ADDRESS[0].lower())
    bond_chain, bond_chain_name = find_chain_for_contract(bond_contract_address)
    
    web3_chain = web3_instances[bond_chain]

    bond_chain_id, bond_contract = transactions_function(bond_chain, bond_contract_address)
    
    # Get USDC token contract
    implementation_usdc_token_contract_address = get_implementation_token_address(usdc_token_contract_address, bond_chain)
    implementation_usdc_token_abi = get_abi(bond_chain, implementation_usdc_token_contract_address)
    usdc_token_contract = web3_chain.eth.contract(address=usdc_token_contract_address, abi=implementation_usdc_token_abi)
    
    # Get principal token address
    proxy_token_address = bond_contract.functions.principalToken().call()
    token_chain, token_chain_name = find_chain_for_contract(proxy_token_address)
    
    # Get principal token contract with proxy token and implementation token
    implementation_token_address = get_implementation_token_address(proxy_token_address, token_chain)
    implementation_token_abi = get_abi(token_chain, implementation_token_address)
    token_contract = web3_chain.eth.contract(address=proxy_token_address, abi=implementation_token_abi)
    
    # Get Token contract of base uniswap quoter address
    base_uniswap_quoter_abi = get_abi(bond_chain, base_uniswap_quoter_address)
    base_uniswap_quoter_contract = web3_chain.eth.contract(address=base_uniswap_quoter_address, abi=base_uniswap_quoter_abi)
    
    if bond_contract and token_contract:
        if can_use_permit(token_contract, bond_contract):
            amount = 10**6
            nonce = token_contract.functions.nonces(WALLET_ADDRESS).call()
            deadline = int(time.time()) + 300

            # EIP-712 cấu trúc message
            domain = {
                "name": "TokenName",
                "version": "1",
                "chainId": web3_chain.eth.chain_id,
                "verifyingContract": proxy_token_address
            }

            permit_struct = {
                "owner": WALLET_ADDRESS,
                "spender": bond_contract_address,
                "value": amount,
                "nonce": nonce,
                "deadline": deadline
            }

            domain_name_hash = Web3.keccak(text=domain["name"])

            # Create message hash by EIP-712
            message = encode_defunct(web3_chain.solidity_keccak(
                ["bytes32", "address", "address", "uint256", "uint256", "uint256"],
                [domain_name_hash, WALLET_ADDRESS, bond_contract_address, amount, nonce, deadline]
            ))

            # Sign message by private key
            signed_message = web3_chain.eth.account.sign_message(message, private_key=PRIVATE_KEY)

            v, r, s = signed_message.v, signed_message.r, signed_message.s
            print(f"Permit Signature (v, r, s): {v}, {hex(r)}, {hex(s)}")

            gas_estimate_permit = bond_contract.functions.depositWithPermit(
                amount,  
                bond_contract_address,  
                WALLET_ADDRESS, 
                deadline,  
                v, r, s  
            ).estimate_gas({"from": WALLET_ADDRESS})

            gas_price = web3_chain.eth.gas_price

            # Call depositWithPermit()
            tx = bond_contract.functions.depositWithPermit(
                amount, 
                bond_contract_address,  
                WALLET_ADDRESS,  
                deadline,  
                v, r, s  # Chữ ký từ bước trước
            ).build_transaction({
                "from": WALLET_ADDRESS,
                "nonce": web3_chain.eth.get_transaction_count(WALLET_ADDRESS),
                "gas": gas_estimate_permit,
                "gasPrice": gas_price
            })

            # Ký giao dịch
            signed_tx = web3_chain.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            tx_hash = web3_chain.eth.send_raw_transaction(signed_tx.raw_transaction)

            print(f"Deposit With Permit Tx Hash: {web3_chain.to_hex(tx_hash)}")

        else:
            usdc_decimals = usdc_token_contract.functions.decimals().call()
            principal_decimals = token_contract.functions.decimals().call()
            
            print(f"USDC decimals: {usdc_decimals}")
            print(f"Principal decimals: {principal_decimals}")
            
            amount_approve = 1 * (10**principal_decimals)
            amount_revoke = 0
            
            slippage_tolerance = 0  # 0% slippage
            true_bill_price = bond_contract.functions.trueBillPrice().call()
            max_price = int(true_bill_price * (1 + slippage_tolerance))
            
            print(f"amount: {amount_approve}, max price: {max_price}")
            
            gas_price = web3_chain.eth.gas_price
            
            balance_wallet = token_contract.functions.balanceOf(WALLET_ADDRESS).call()
            allowance_token = token_contract.functions.allowance(WALLET_ADDRESS, bond_contract_address).call()
            
            print(f"Allowance: {allowance_token}")
            print(f"Balance wallet: {balance_wallet}")
            
            # balance_wallet_scaled = balance_wallet / (10**(principal_decimals - 6))
            # allowance_usdc_token = usdc_token_contract.functions.allowance(WALLET_ADDRESS, base_uniswap_router_address).call()
            
            # print(f"Implementation token address: {implementation_token_address}")
            
            # estimated_principal = get_usdc_to_principal_rate(base_uniswap_quoter_contract, amount_approve, usdc_token_contract_address, proxy_token_address)
            # print(f"Estimated principal by amount USDC: {estimated_principal}")
            
            # if proxy_token_address != usdc_token_contract_address:
            #     if balance_wallet < amount_approve:
            #         print(f"⚠️ Not enough {proxy_token_address}, need to swap from USDC...")
            #         swap_usdc_to_principal_token(bond_chain, proxy_token_address, usdc_token_contract_address, usdc_token_contract, gas_price, amount_approve)
            # else:
            #     print("Token is USDC, no need to swap.")

            # if balance_wallet < amount_approve:
            #     print("❌ Not enough tokens to buy bond.")
            #     sys.exit()

            if allowance_token >= amount_approve:
                print("✅ Allowance is sufficient, skipping approval.")
            else:
                print("🔄 Approving token for bond contract...")
                approve_token(token_contract, bond_contract_address, amount_approve, web3_chain, gas_price)
                time.sleep(10)  
                
            # print("⚡ Depositing bond...")
            # deposit_bond(bond_contract, amount_approve, max_price, web3_chain, gas_price)

            # print("⏳ Waiting 20 minutes before revoking approval...")
            # time.sleep(30)  

            # print("🚫 Revoking token approval...")
            # approve_token(token_contract, bond_contract_address, amount_revoke, web3_chain, gas_price)
            # print("✅ Token approval revoked.")
        
    else: 
        print("Error")
    
    
    
    
    
    
    # for contract_address in BOND_CONTRACT_ADDRESS:
    #     chain, chain_name = find_chain_for_contract(contract_address.lower())
    #     if chain and chain_name:
    #         bond_contract_address = contract_address.lower()

    #         chain_id, contract_instance = transactions_function(chain, bond_contract_address)

    #         web3_chain = web3_instances[chain]

    #         wallet_address = web3_chain.eth.account.from_key(PRIVATE_KEY).address

    #         balance = web3_chain.eth.get_balance(wallet_address)

    #         print(f"Số dư ví ({wallet_address}): {Web3.from_wei(balance, 'ether')} ETH {chain_id}")

    #         WALLET_ADDRESS = web3_chain.eth.account.from_key(PRIVATE_KEY).address 
            
    #         gas_estimate = contract_instance.functions.redeem(BOND_ID).estimate_gas({'from': WALLET_ADDRESS})
    #         gas_price = web3_chain.eth.gas_price  # Lấy gas price hiện tại từ mạng

    #         print(f"Gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
    #         print(f"Gas estimate: {Web3.from_wei(gas_estimate, 'gwei')} gwei")

    #         redeem_txn = contract_instance.functions.redeem(BOND_ID).build_transaction({
    #             'from': WALLET_ADDRESS,
    #             'nonce': web3_chain.eth.get_transaction_count(WALLET_ADDRESS),
    #             'gas': gas_estimate,  # Điều chỉnh Gas Limit
    #             'gasPrice': gas_price,
    #             'chainId': web3_chain.eth.chain_id
    #         })

    #         signed_txn = web3_chain.eth.account.sign_transaction(redeem_txn, private_key=PRIVATE_KEY)

    #         tx_hash = web3_chain.eth.send_raw_transaction(signed_txn.raw_transaction)

    #         print(f"✅ Giao dịch redeem đã gửi: {web3_chain.to_hex(tx_hash)}")

    #         receipt = web3_chain.eth.wait_for_transaction_receipt(tx_hash)
    #         if receipt.status == 1:
    #             print("🎉 Claim bond thành công!")
    #         else:
    #             print("❌ Giao dịch thất bại.")