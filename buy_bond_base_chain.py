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

PRIVATE_KEY = "8d2065f47d5e5b15375c0d51d6bab2bc49900d38f548efbe99edb5bf45627c90"
WALLET_ADDRESS = Account.from_key(PRIVATE_KEY).address
print(f"WALLET ADDRESS: {WALLET_ADDRESS}")

BOND_CONTRACT_ADDRESS = input("Enter the Bond Contract Address: ").strip()

AMOUNT_APRROVAL = int(input("Enter the amount of USDC Token to approve: ").strip())

AMOUNT_DEPO = int(input("Enter the amount of Principal Token to buy: ").strip())

USDC_TOKEN_CONTRACT_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

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
    
    return tx_hash
    
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
    
    return tx_hash
    
def wait_for_tx_receipt(web3_chain, tx_hash, max_attempts=10, sleep_time=3):
    """ Chờ giao dịch được xác nhận """
    for attempt in range(max_attempts):
        receipt = web3_chain.eth.get_transaction_receipt(tx_hash)
        if receipt:
            print(f"✅ Transaction {tx_hash} confirmed in block {receipt.blockNumber}")
            return receipt
        print(f"⏳ Waiting for transaction {tx_hash} to confirm... ({attempt + 1}/{max_attempts})")
        time.sleep(sleep_time)
    print(f"❌ Transaction {tx_hash} not confirmed after {max_attempts} attempts.")
    sys.exit()
    
def wait_for_allowance_update(token_contract, wallet_address, spender_address, expected_allowance, max_attempts=10, sleep_time=3):
    """ Chờ allowance được cập nhật """
    for attempt in range(max_attempts):
        allowance = token_contract.functions.allowance(wallet_address, spender_address).call()
        if allowance >= expected_allowance:
            print(f"✅ Allowance updated: {allowance}")
            return allowance
        print(f"⏳ Allowance not updated yet... Checking again ({attempt + 1}/{max_attempts})")
        time.sleep(sleep_time)
    print(f"❌ Allowance did not update after {max_attempts} attempts.")
    sys.exit()

if __name__ == "__main__":

    for chain, web3 in web3_instances.items():
        try: 
            chain_id = web3.eth.chain_id
            print(f"✅ Connect to {chain} (Chain ID: {chain_id})")
        except Exception as e:
            print(f"❌ Error connecting to {chain}: {str(e)}")
    
    usdc_token_contract_address = Web3.to_checksum_address(USDC_TOKEN_CONTRACT_ADDRESS.lower())
    usdc_chain, usdc_chain_name = find_chain_for_contract(usdc_token_contract_address)
    
    bond_contract_address = Web3.to_checksum_address(BOND_CONTRACT_ADDRESS.lower())
    bond_chain, bond_chain_name = find_chain_for_contract(bond_contract_address)
    
    web3_chain = web3_instances[bond_chain]

    bond_chain_id, bond_contract = transactions_function(bond_chain, bond_contract_address)
    
    # Get USDC token contract
    implementation_usdc_token_contract_address = get_implementation_token_address(usdc_token_contract_address, bond_chain)
    implementation_usdc_token_abi = get_abi(bond_chain, implementation_usdc_token_contract_address)
    usdc_token_contract = web3_chain.eth.contract(address=usdc_token_contract_address, abi=implementation_usdc_token_abi)
    
    # Get proxy principal token address
    proxy_token_address = bond_contract.functions.principalToken().call()
    token_chain, token_chain_name = find_chain_for_contract(proxy_token_address)
    
    # Get contract of implementation token from proxy principal token
    implementation_token_address = get_implementation_token_address(proxy_token_address, token_chain)
    implementation_token_abi = get_abi(token_chain, implementation_token_address)
    token_contract = web3_chain.eth.contract(address=proxy_token_address, abi=implementation_token_abi)
    
    usdc_decimals = usdc_token_contract.functions.decimals().call()
    principal_decimals = token_contract.functions.decimals().call()
            
    print(f"USDC decimals: {usdc_decimals}")
    print(f"Principal decimals: {principal_decimals}")
            
    amount_approve = AMOUNT_APRROVAL * (10**principal_decimals)
    amount_deposit = AMOUNT_DEPO * (10**principal_decimals)
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
    
    if bond_contract and token_contract:
        if can_use_permit(token_contract, bond_contract):
        
            wallet_addr = Web3.to_checksum_address(WALLET_ADDRESS)
            bond_addr = Web3.to_checksum_address(BOND_CONTRACT_ADDRESS)
            proxy_addr = Web3.to_checksum_address(implementation_token_address)

            # Lấy nonce hiện tại
            nonce = token_contract.functions.nonces(WALLET_ADDRESS).call()
            deadline = int(time.time()) + 3600
            
            chain_id_permit = web3_chain.eth.chain_id
            token_name = token_contract.functions.name().call()
            token_version = token_contract.functions.version().call()
            
            print(f"Chain ID: {chain_id_permit}")
            print(f"Token Name: {token_name}")
            print(f"Token Version: {token_version}")
            print(f"Nonces: {nonce}")
            print(f"Verifying Contract: {proxy_addr}")
            
            print(f"Wallet Address: {wallet_addr}")
            print(f"Proxy Token Address: {proxy_addr}")
            print(f"Bond Contract Address: {bond_addr}")

            proxy_domain_separator = token_contract.functions.DOMAIN_SEPARATOR().call()
            implementation_token_contract = web3_chain.eth.contract(address=implementation_token_address, abi=implementation_token_abi)
            implementation_domain_separator = implementation_token_contract.functions.DOMAIN_SEPARATOR().call()

            print(f"✅ DOMAIN_SEPARATOR từ Proxy Token: {proxy_domain_separator.hex()}")
            print(f"✅ DOMAIN_SEPARATOR từ Implementation Token: {implementation_domain_separator.hex()}")

            # DOMAIN_TYPEHASH = Web3.to_bytes(
            #     hexstr="0x8b73c3c69bb8fe3d512ecc4cf759cc79239f7b179b0ffacaa9a75d522b39400f"
            # )

            # calculated_domain_separator = Web3.solidity_keccak(
            #     ["bytes32", "bytes32", "bytes32", "uint256", "address"],
            #     [
            #         DOMAIN_TYPEHASH,
            #         Web3.keccak(text=token_name),
            #         Web3.keccak(text=token_version),
            #         chain_id_permit,
            #         proxy_addr  # Verifying contract address
            #     ]
            # )

            # print(f"📝 Recalculated DOMAIN_SEPARATOR: {proxy_domain_separator.hex()}")
            # print(f"✅ On-chain DOMAIN_SEPARATOR: {implementation_domain_separator.hex()}")

            on_chain_permit_typehash = token_contract.functions.PERMIT_TYPEHASH().call()
            print(f"✅ On-chain PERMIT_TYPEHASH: {on_chain_permit_typehash.hex()}")
            
            PERMIT_TYPEHASH = Web3.to_bytes(
                hexstr="0x6e71edae12b1b97f4d1f60370fef10105fa2faae0126114a169c64845d6126c9"
            )

            struct_hash = Web3.solidity_keccak(
                ["bytes32", "address", "address", "uint256", "uint256", "uint256"],
                [
                    PERMIT_TYPEHASH,
                    wallet_addr,
                    bond_addr,
                    int(amount_approve),
                    int(nonce),
                    int(deadline),
                ]
            )
            
            print(f"✅ Permit typehash: {PERMIT_TYPEHASH.hex()}")

            eip712_hash = Web3.solidity_keccak(
                ["bytes32", "bytes32"],
                [implementation_domain_separator, struct_hash]  # Sử dụng Implementation Token DOMAIN_SEPARATOR
            )

            signer_address = Account.from_key(PRIVATE_KEY).address
            print(f"Signer address: {signer_address}")
            assert signer_address.lower() == wallet_addr.lower(), "⚠️ Private key không khớp với Wallet Address!"

            
            # Ký bằng private key
            message = encode_defunct(eip712_hash)
            signed_message = Account.sign_message(message, private_key=PRIVATE_KEY)

            # Lấy r, s, v
            r = signed_message.r
            s = signed_message.s
            v = signed_message.v

            # Đảm bảo v thuộc {27, 28}
            if v < 27:
                v += 27
            
            print(f"📝 Signature v: {v}")
            print(f"📝 Signature r: {hex(r)}")
            print(f"📝 Signature s: {hex(s)}")

            # Đóng gói chữ ký
            signature_bytes = (r.to_bytes(32, byteorder="big") + s.to_bytes(32, byteorder="big") + v.to_bytes(1, byteorder="big"))

            # Gửi giao dịch `permit`
            try:
                tx = implementation_token_contract.functions.permit(
                    wallet_addr, bond_addr, int(amount_approve), int(deadline), signature_bytes
                ).transact({"from": wallet_addr})
                print("✅ Permit transaction sent:", tx.hex())
            except Exception as e:
                print("❌ Permit failed on implementation token:", str(e))
            
            # sign_tx_permit = web3_chain.eth.account.sign_transaction(tx_permit, private_key=PRIVATE_KEY)
            # tx_hash_permit = web3_chain.eth.send_raw_transaction(sign_tx_permit.raw_transaction)
            # print(f"Permit Tx Hash: {web3_chain.to_hex(tx_hash_permit)}")
            
            # web3_chain.eth.wait_for_transaction_receipt(web3_chain.to_hex(tx_hash_permit))
            
            # gas_estimated_deposit = bond_contract.functions.deposit(
            #     amount_approve, max_price, WALLET_ADDRESS
            # ).estimate_gas({"from": WALLET_ADDRESS})
            # print(f"Estimated deposit gas: {gas_estimated_deposit}")
            
            # tx_deposit = bond_contract.functions.deposit(amount_approve).build_transaction({
            #     "from": WALLET_ADDRESS,
            #     "nonce": web3_chain.eth.get_transaction_count(WALLET_ADDRESS),
            #     "gas": gas_estimated_deposit,
            #     "gasPrice": web3_chain.eth.gas_price
            # })
            
            # sign_tx_deposit = web3_chain.eth.sign_transaction(tx_deposit, private_key=PRIVATE_KEY)
            # tx_hash_deposit = web3_chain.eth.send_raw_transaction(sign_tx_deposit.raw_transaction)
            # print(f"Deposit With Tx Permit Hash: {web3_chain.to_hex(tx_hash_deposit)}")
            
        else:
            tx_hash = None
            
            if balance_wallet < amount_approve:
                print("❌ Not enough tokens to buy bond.")
                sys.exit()

            if allowance_token >= amount_approve:
                print("✅ Allowance is sufficient, skipping approval.")
            else:
                print("🔄 Approving token for bond contract...")
                tx_hash = approve_token(token_contract, bond_contract_address, amount_approve, web3_chain, gas_price)
                time.sleep(10)  
                
                print(f"Tx Hash: {web3_chain.to_hex(tx_hash)}")
                
            if tx_hash is not None:
                wait_for_tx_receipt(web3_chain, web3_chain.to_hex(tx_hash))
                
                wait_for_allowance_update(token_contract, WALLET_ADDRESS, bond_contract_address, amount_approve)
            
            allowance_token_after = token_contract.functions.allowance(WALLET_ADDRESS, bond_contract_address).call()
            print(f"Allowance after approve: {allowance_token_after}")
            
            if amount_deposit > allowance_token_after:
                print("❌ Not enough tokens allowanced to buy bond.")
                sys.exit()
            else: 
                print("⚡ Depositing bond...")
                deposit_bond(bond_contract, amount_deposit, max_price, web3_chain, gas_price)

            print("⏳ Waiting 20 minutes before revoking approval...")
            time.sleep(60)  

            print("🚫 Revoking token approval...")
            approve_token(token_contract, bond_contract_address, amount_revoke, web3_chain, gas_price)
            print("✅ Token approval revoked.")
            
            wait_for_allowance_update(token_contract, WALLET_ADDRESS, bond_contract_address, amount_deposit)
            
            allowance_token_after = token_contract.functions.allowance(WALLET_ADDRESS, bond_contract_address).call()
            print(f"Allowance after approve: {allowance_token_after}")
        
    else: 
        print("Error")