import requests
import csv
import sys

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

# Get transaction follow action of api url
def get_transactions(chain, module, action, wallet_address, from_block, to_block):
    url = API_URLS[chain]
    params = {
        'module': module,
        'action': action,
        'address': wallet_address,
        'startblock': from_block,
        'endblock': to_block,
        'apikey': API_KEYS[chain]
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Filter data by range of blocknumber
    if data['status'] == '1' and isinstance(data['result'], list):
        return [
            tx for tx in data['result']
            if tx.get('blockNumber') and from_block <= int(tx.get('blockNumber')) <= to_block
        ]
    else:
        print(f"API lỗi hoặc không có giao dịch: {data}")
        return []

# Process transactions and tokens retrieved 
def parse_transactions(wallet_address, chain, from_block, to_block):

    # Get normal transaction, internal transaction, ERC-20 token
    normal_txs = get_transactions(chain, 'account', 'txlist', wallet_address, from_block, to_block)
    internal_txs = get_transactions(chain, 'account', 'txlistinternal', wallet_address, from_block, to_block)
    erc20_token_txs = get_transactions(chain, 'account', 'tokentx', wallet_address, from_block, to_block)

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
        value = float(tx['value']) / (10 ** int(tx['tokenDecimal']))
        token_symbol = tx['tokenSymbol']
        token_address = tx['contractAddress']
        token_direct = 'IN' if tx['to'].lower() == wallet_address.lower() else 'OUT'

        if txhash not in transactions:
            continue

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

    return transactions.values()

if __name__ == "__main__":
    wallet_address, chain, from_block, to_block = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    wallet_transactions = parse_transactions(wallet_address, chain, from_block, to_block)
    print(wallet_transactions)