import asyncio
import json
import time
import requests
import websockets
from web3 import Web3
import datetime
from web3.middleware import ExtraDataToPOAMiddleware

API_KEY_INFURA = "13ceaec149fe450c8b71b4e377aa2b83"

# Infura WebSocket URL (Base Mainnet)
INFURA_WS_URL = f"wss://base-mainnet.infura.io/ws/v3/{API_KEY_INFURA}"

# Telegram Bot Info
TELEGRAM_BOT_TOKEN = "7836597875:AAEbZKTq5OLWoKqRljx4WQXSYY7yMRb5wu4"
TELEGRAM_CHAT_ID = "-1002583666142"

# Wallet address to watch
WATCH_ADDRESS = "0x493361D6164093936c86Dcb35Ad03b4C0D032076".lower()

# RPC WebSocket URLs
RPC_WS_URLS = {
    'ETH': f'wss://mainnet.infura.io/ws/v3/{API_KEY_INFURA}',
    'BNB': f'wss://bsc-mainnet.infura.io/ws/v3/{API_KEY_INFURA}',
    'POL': f'wss://polygon-mainnet.infura.io/ws/v3/{API_KEY_INFURA}',
    'ARB': f'wss://arbitrum-mainnet.infura.io/ws/v3/{API_KEY_INFURA}',
    'BAS': f'wss://base-mainnet.infura.io/ws/v3/{API_KEY_INFURA}',
    'LIN': f'wss://linea-mainnet.infura.io/ws/v3/{API_KEY_INFURA}'
}

# RPC HTTPs URLs
RPC_HTTPS_URLS = {
    'ETH': f'https://mainnet.infura.io/v3/{API_KEY_INFURA}',
    'BNB': f'https://bsc-mainnet.infura.io/v3/{API_KEY_INFURA}',
    'POL': f'https://polygon-mainnet.infura.io/v3/{API_KEY_INFURA}',
    'ARB': f'https://arbitrum-mainnet.infura.io/v3/{API_KEY_INFURA}',
    'BAS': f'https://base-mainnet.infura.io/v3/{API_KEY_INFURA}',
    'LIN': f'https://linea-mainnet.infura.io/v3/{API_KEY_INFURA}'
}

SCAN_URLS = {
    'ETH': 'https://etherscan.io/tx/',
    'BNB': 'https://bscscan.com/tx/',
    'POL': 'https://polygonscan.com/tx/',
    'ARB': 'https://arbiscan.io/tx/',
    'BAS': 'https://basescan.org/tx/',
    'LIN': 'https://lineascan.build/tx/'
}

# Connect to Web3 (use HTTP to get detail of transaction)
# w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.infura.io/v3/{API_KEY_INFURA}"))
web3_chain = {chain: Web3(Web3.HTTPProvider(url)) for chain, url in RPC_HTTPS_URLS.items()}

# Send message to Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram: {e}")

# Processing new transaction
def handle_transaction(chain, tx_hash, block_number):
    try:
        web3 = web3_chain[chain]
        
        # Inject middleware if chain is POA
        if chain in ['BNB', 'POL', 'ARB', 'BAS', 'LIN']:
            if ExtraDataToPOAMiddleware not in web3.middleware_onion:
                web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        start_time = time.time()

        # tx = web3.eth.get_transaction(tx_hash)
        # Get transaction detail
        for attempt in range(5):
            try:
                tx = web3.eth.get_transaction(tx_hash)
                if tx.get("blockNumber") is not None:
                    break
                time.sleep(0.5 * (attempt + 1))  # delay increasing
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        else:
            print(f"⚠️ Giao dịch {tx_hash} vẫn chưa có blockNumber sau nhiều lần thử.")
            return

        # Check from and to fields
        from_address = tx.get("from", "").lower()
        to_address = tx.get("to")
        to_address = to_address.lower() if to_address else "Contract Creation"

        # Check value
        value = web3.from_wei(tx.get("value", 0), "ether")
        
        for attempt in range(5):
            try:
                block = web3.eth.get_block(tx["blockNumber"])
                break
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        else:
            print(f"⚠️ Không thể lấy block info cho tx {tx_hash} sau nhiều lần thử.")
            return

        # Get TimeStamp
        timestamp = block["timestamp"]
        readable_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # Check if the transaction involves the watch address
        if WATCH_ADDRESS in [from_address, to_address]:
            elapsed_time = (time.time() - start_time) * 1000
            message = (
                f"🚀 *Giao dịch mới liên quan đến ví {WATCH_ADDRESS}*\n"
                f"🔹 *Block Number:* {block_number}\n"
                f"🔹 *TX Hash:* [0x{tx_hash}]({SCAN_URLS[chain]}/0x{tx_hash})\n"
                f"🔹 *From:* `{from_address}`\n"
                f"🔹 *To:* `{to_address}`\n"
                f"🔹 *Amount:* {value} ETH\n"
                f"🕒 *TimeStamp:* {readable_time}\n"
                f"🕒 *Delay:* {elapsed_time:.2f} ms"
            )
            print(message)
            send_telegram_message(message)

    except Exception as e:
        print(f"❌ Lỗi khi xử lý giao dịch {tx_hash}: {e}")
        
async def handle_new_block(chain, block_hash):
    try:
        web3 = web3_chain[chain]
        
        # Inject middleware if chain is POA
        if chain in ['BNB', 'POL', 'ARB', 'BAS', 'LIN']:
            if ExtraDataToPOAMiddleware not in web3.middleware_onion:
                web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        for attempt in range(5):  # retry 5 times
            try:
                block = web3.eth.get_block(block_hash, full_transactions=True)
                break 
            except Exception as e:
                if attempt < 4:
                    await asyncio.sleep(0.5)  # sleep 0.5s before retry
                else:
                    print(f"❌ Lỗi khi xử lý block mới sau nhiều lần thử: {e}")
                    return

        if not block.transactions:
            print(f"ℹ️ Block {block.number} không có giao dịch nào.")
            return

        found = False
        for tx in block.transactions:
            from_address = tx.get("from", "").lower()
            to_address = tx["to"].lower() if tx["to"] else "Contract Creation"

            if WATCH_ADDRESS in [from_address, to_address]:
                found = True
                handle_transaction(chain, tx.hash.hex(), block.number)

        if not found:
            print(f"ℹ️ Block {block.number} không có giao dịch nào liên quan đến {WATCH_ADDRESS}")

    except Exception as e:
        print(f"❌ Lỗi khi xử lý block mới: {e}")

# Listing for new blocks with Websocket (Async)
async def listen_for_transactions(chain):
    while True:
        try:
            async with websockets.connect(RPC_WS_URLS[chain]) as ws:
                print(f"🔍 Đang lắng nghe block mới trên chain {chain}...")

                subscribe_msg = json.dumps({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_subscribe",
                    "params": ["newHeads"]
                })
                await ws.send(subscribe_msg)

                while True:
                    response = await ws.recv()
                    data = json.loads(response)

                    if "params" in data and "result" in data["params"]:
                        block_data = data["params"]["result"]
                        block_hash = block_data.get("hash")
                        if block_hash:
                            await handle_new_block(chain, block_hash)

        except Exception as e:
            print(f"❌ Lỗi WebSocket: {e}")
            await asyncio.sleep(5)

# Run
asyncio.run(listen_for_transactions("BNB"))
