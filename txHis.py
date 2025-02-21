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
        'apikey': API_KEYS[chain]
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data['status'] == '1':
        return [
            tx for tx in data['result']
            if tx.get('blockNumber') and from_block <= int(tx['blockNumber']) <= to_block
        ]
    else:
        return []

print(get_transactions('ETH', "account", "txlist", "0x1eba9555cbfc3ec0eef8b730854e2af921d633cc", 19186237, 21749118))
print(get_transactions('ETH', "account", "txlistinternal", "0x1eba9555cbfc3ec0eef8b730854e2af921d633cc", 19186237, 21749118))
print(get_transactions('ETH', "account", "tokentx", "0x1eba9555cbfc3ec0eef8b730854e2af921d633cc", 19186237, 21749118))