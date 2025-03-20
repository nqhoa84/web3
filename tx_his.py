import requests
import csv
import sys
import blacklist_tokens
import time

# Api urls of blockchains
API_URLS = {
    'ETH': 'https://api.etherscan.io/api',
    'BAS': 'https://api.basescan.org/api',
    'POL': 'https://api.polygonscan.com/api',
    'BSC': 'https://api.bscscan.com/api',
    'ARB': 'https://api.arbiscan.io/api',
    'LIN': 'https://api.lineascan.build/api',
}

# Api keys of each blockchains
API_KEYS = {
    'ETH': '9BZMQYAZVSVKVURIA3SPKDZEYS2DQ4NARU',
    'BAS': 'WFV28BSE1T9C9Q4XFBKJESD4MXDZ322XXH',
    'POL': 'PM8HRYCQZ4QUWC5RVJNWQVBNTBBEIY4A8F',
    'BSC': '1Q1I7XJZDTVQY7BJ91KNE1PQT6C2DDFWHG',
    'ARB': 'AAZFEQ2R2AYXFHV9YVDX4UJ4NKHA43WJP5',
    'LIN': '15V5YKYIH6RCKW6YNT5NG12FZ7FS8CDVS3',
}

CURRENCY_MAP = {
    'ETH': 'ETH',
    'BSC': 'BNB',
    'POL': 'POL',
    'ARB': 'ARB',
    'BAS': 'ETH',
    'LIN': 'ETH'
}

# Get latest block from chain type
def get_latest_block(chain):
    url = API_URLS[chain]
    params = {
        'module': 'proxy',
        'action': 'eth_blockNumber',
        'apikey': API_KEYS[chain]
    }

    response = requests.get(url, params=params)
    data = response.json()

    if 'result' in data:
        return int(data['result'], 16)
    else:
        print(f"Cannot get latest block: {data}")
        return None

# API Configuration
MAX_TXS_PER_REQUEST = 10000  
MAX_BLOCKS_PER_REQUEST = 100000  
MAX_BLOCKS_PER_BATCH = MAX_BLOCKS_PER_REQUEST * 5  # 500,000 blocks per batch
API_DELAY = 1.0 / 5  # Limit to 5 requests per second

def fetch_transactions(url, params):
    """Sends API request to fetch transactions, handling pagination if necessary."""
    all_transactions = []
    page = 1

    while True:
        params['page'] = page
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1' and isinstance(data.get('result'), list):
                    txs = data['result']

                    if len(txs) == MAX_TXS_PER_REQUEST:
                        print(f"⚠️ Possible missing transactions! Block range {params['startblock']} - {params['endblock']} may need smaller chunks.")

                    if not txs:
                        break  # No more transactions, exit loop

                    all_transactions.extend(txs)
                    print(f"✅ Page {page}: Retrieved {len(txs)} transactions.")

                    if len(txs) < MAX_TXS_PER_REQUEST:
                        break  # If transactions are below limit, stop
                    page += 1  
                else:
                    break  
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            break

        time.sleep(API_DELAY)  # Avoid hitting rate limit

    return all_transactions

def process_block_range(chain, module, action, wallet_address, start_block, end_block):
    """Fetches transaction data from API for a specific block range."""

    url = API_URLS[chain]
    transactions = []
    
    print(f"🟢 Fetching transactions from block {start_block} to {end_block}...")

    params = {
        'module': module,
        'action': action,
        'address': wallet_address,
        'startblock': start_block,
        'endblock': end_block,
        'offset': MAX_TXS_PER_REQUEST,
        'apikey': API_KEYS[chain]
    }

    txs = fetch_transactions(url, params=params)
    if txs:
        transactions.extend(txs)
        print(f"✅ Retrieved {len(txs)} transactions from {start_block} to {end_block}.")
        
    else:
        print(f"⚠️ No transactions found in range {start_block} to {end_block}.")

    time.sleep(API_DELAY)  # Ensure rate limit is respected
    return transactions

def get_transactions(chain, module, action, wallet_address, from_block, to_block):
    """Splits block range into batches (5 segments per batch, each 100,000 blocks) and processes them sequentially."""

    transactions = []
    batch_ranges = []

    current_block = from_block
    while current_block <= to_block:
        batch = []
        for _ in range(5):  # Each batch contains 5 block segments
            if current_block > to_block:
                break
            next_block = min(current_block + MAX_BLOCKS_PER_REQUEST - 1, to_block)
            
            batch.append((current_block, next_block))
            current_block = next_block + 1

        batch_ranges.append(batch)  # Store batch in list

    # Process each batch sequentially
    for i, batch in enumerate(batch_ranges):
        print(f"\n🚀 Processing Batch {i+1}/{len(batch_ranges)} ({len(batch)} block ranges)...\n")

        batch_start_time = time.time()  # Start time for batch

        for b in batch:
            result = process_block_range(chain, module, action, wallet_address, *b)

            if result:
                transactions.extend(result)

        batch_end_time = time.time()  # End time for batch
        batch_duration = batch_end_time - batch_start_time

        # Ensure each batch takes at least 1 second to comply with rate limit
        if batch_duration < 1.0:
            time.sleep(1.0 - batch_duration)

    print(f"\n🎉 Finished fetching transactions. Total: {len(transactions)}")
    return transactions

# Check block range
def is_valid_block_range(chain, from_block, to_block):
    latest_block = get_latest_block(chain)
    
    if latest_block is None:
        print("Cannot get lastest block. Error API or network.")
        return False

    if from_block < 0 or to_block < 0:
        print("from_block and to_block have to >= 0.")
        return False

    if from_block > to_block:
        print("from_block cannot be greater than to_block.")
        return False

    if to_block > latest_block:
        print(f"to_block ({to_block}) cannot greater than latest_block ({latest_block}).")
        return False

    return True

# Process transactions and tokens retrieved 
def parse_transactions(wallet_address, chain, from_block, to_block):

    # Get normal transaction, internal transaction, ERC-20 token
    normal_txs = get_transactions(chain, 'account', 'txlist', wallet_address, from_block, to_block)
    if not normal_txs:
        print("No Normal transactions found!")

    internal_txs = get_transactions(chain, 'account', 'txlistinternal', wallet_address, from_block, to_block)
    if not internal_txs:
        print("No Internal transactions found!")

    erc20_token_txs = get_transactions(chain, 'account', 'tokentx', wallet_address, from_block, to_block)
    if not erc20_token_txs:
        print("No ERC-20 token transactions found!")

    # Initialize transaction object
    transactions = {}

    # Add normal transactions value
    for tx in normal_txs:
         txhash = tx['hash']
         tx_fee = float(tx['gasUsed']) * float(tx['gasPrice']) / 10**18
         native_value = float(tx['value']) / 10**18
         direct = 'IN' if tx['to'].lower() == wallet_address.lower() else 'OUT'

         transactions[txhash] = {
             'block': tx['blockNumber'],
             'txhash': txhash,
             'wallet': wallet_address,
             'tx_fee': tx_fee,
             'native_value': native_value,
             'direct': direct,
             'internal_value': 0,
             'internal_direct': '',
             'tokens': []
         }

    # Add internal transactions value
    for tx in internal_txs:
        txhash = tx['hash']
        value = float(tx['value']) / 10**18
        direction = 'IN' if tx['to'].lower() == wallet_address.lower() else 'OUT'
        
        if txhash in transactions:
            if value > 0:
                transactions[txhash]['internal_value'] = value
                transactions[txhash]['internal_direct'] = direction
        else:
            transactions[txhash] = {
                'block': tx['blockNumber'],
                'txhash': txhash,
                'wallet': wallet_address,
                'tx_fee': 0,
                'native_value': 0,
                'direct': '',
                'internal_value': value,
                'internal_direct': direction,
                'tokens': []
            }

    # Add ERC-20 tokens value
    for tx in erc20_token_txs:
        txhash = tx['hash']
        decimals = int(tx.get('tokenDecimal', 18))
        value = float(tx['value']) / (10 ** decimals) if decimals > 0 else 0
        token_symbol = tx['tokenSymbol']
        token_address = tx['contractAddress']
        token_direct = 'IN' if tx['to'].lower() == wallet_address.lower() else 'OUT'

        if token_address.lower() in map(str.lower, blacklist_tokens.blacklist_tokens):
            continue

        if txhash in transactions:
            # Check if tokens are duplicated and add up the value
            token_found = False
            for token_info in transactions[txhash]['tokens']:
                if token_info[0] == token_symbol and token_info[1] == token_address and token_info[3] == token_direct:
                    token_info[2] += value
                    token_found = True
                    break
            
            if not token_found:
                transactions[txhash]['tokens'].append([
                    token_symbol,
                    token_address,
                    value,
                    token_direct
                ])
        else:
            transactions[txhash] = {
                'block': tx['blockNumber'],
                'txhash': txhash,
                'wallet': wallet_address,
                'tx_fee': 0,
                'native_value': 0,
                'direct': '',
                'internal_value': 0,
                'internal_direct': '',
                'tokens': [
                    [
                        token_symbol,
                        token_address,
                        value,
                        token_direct
                    ]
                ]
            }

    return transactions.values()

# Export data to csv
def export_data_to_csv(transactions, wallet_address, chain, from_block, to_block):
    fileName = f"{wallet_address}_{chain}_{from_block}_{to_block}.csv"

    # Number of tokens existing in a transaction
    if transactions:
        max_tokens = max((len(tx['tokens']) for tx in transactions), default=0)
    else:
        max_tokens = 0

    # Write csv file with transactions data
    with open(fileName, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        header = ["block", "txhash", "wallet", "tx fee", "native value", "direct", "internal value", "internal direct"]
        for i in range(1, max_tokens + 1):
            header.extend([f"token{i}", f"contract address{i}", f"value{i}", f"direct{i}"])
        
        writer.writerow(header)
    
        for tx in transactions:
            row = [
                tx['block'], tx['txhash'], tx['wallet'], tx['tx_fee'], tx['native_value'], tx['direct'], 
                tx['internal_value'], tx['internal_direct']
            ]
            for token in tx['tokens']:
                row.extend([token[0], token[1], token[2], token[3]])

            while len(row) < len(header):
                row.append("")

            writer.writerow(row)

        print(f"CSV export: {fileName}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python script.py <wallet_address> <chain> <from_block> <to_block>")
        sys.exit(1)

    wallet_address, chain, from_block, to_block = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])

    if chain not in API_URLS:
        print(f"Invalid chain: {chain}. Only support chains: {', '.join(API_URLS.keys())}")
        sys.exit(1)
    
    if not is_valid_block_range(chain, from_block, to_block):
        print("Block range is invalid. Stop program!!!")
        sys.exit(1)

    wallet_transactions = parse_transactions(wallet_address, chain, from_block, to_block)
    export_data_to_csv(wallet_transactions, wallet_address, chain, from_block, to_block)