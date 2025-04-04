import asyncio
import json
import time
import requests
import websockets
from web3 import Web3
import datetime

API_KEY_INFURA = "13ceaec149fe450c8b71b4e377aa2b83"

# Infura WebSocket URL (Base Mainnet)
INFURA_WS_URL = f"wss://base-mainnet.infura.io/ws/v3/{API_KEY_INFURA}"

# Telegram Bot Info
TELEGRAM_BOT_TOKEN = "7836597875:AAEbZKTq5OLWoKqRljx4WQXSYY7yMRb5wu4"
TELEGRAM_CHAT_ID = "5696892272"

# Địa chỉ ví cần theo dõi
WATCH_ADDRESS = "0x111111125421cA6dc452d289314280a0f8842A65".lower()

# Kết nối Web3 (dùng HTTP để lấy chi tiết giao dịch)
w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.infura.io/v3/{API_KEY_INFURA}"))

# Gửi tin nhắn Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram: {e}")

# Xử lý giao dịch mới
def handle_transaction(tx_hash, block_number):
    try:
        start_time = time.time()

        # Lấy chi tiết giao dịch (có thể raise nếu không tồn tại)
        tx = w3.eth.get_transaction(tx_hash)

        # Kiểm tra trường 'from' và 'to'
        from_address = tx.get("from", "").lower()
        to_address = tx.get("to")
        to_address = to_address.lower() if to_address else "Contract Creation"

        # Kiểm tra giá trị chuyển
        value = w3.from_wei(tx.get("value", 0), "ether")
        
        # Get TimeStamp
        block = w3.eth.get_block(tx["blockNumber"])
        timestamp = block["timestamp"]
        readable_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # Nếu liên quan đến ví cần theo dõi
        if WATCH_ADDRESS in [from_address, to_address]:
            elapsed_time = (time.time() - start_time) * 1000
            message = (
                f"🚀 *Giao dịch mới liên quan đến {WATCH_ADDRESS}*\n"
                f"🔹 *Block Number:* {block_number}\n"
                f"🔹 *TX Hash:* [0x{tx_hash}](https://basescan.org/tx/0x{tx_hash})\n"
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
        
async def handle_new_block(block_hash):
    try:
        block = w3.eth.get_block(block_hash, full_transactions=True)

        if not block.transactions:
            print(f"ℹ️ Block {block.number} không có giao dịch nào.")
            return

        found = False
        for tx in block.transactions:
            from_address = tx.get("from", "").lower()
            to_address = tx["to"].lower() if tx["to"] else "Contract Creation"

            if WATCH_ADDRESS in [from_address, to_address]:
                found = True
                handle_transaction(tx.hash.hex(), block.number)

        if not found:
            print(f"ℹ️ Block {block.number} không có giao dịch nào liên quan đến {WATCH_ADDRESS}")

    except Exception as e:
        print(f"❌ Lỗi khi xử lý block mới: {e}")

# Lắng nghe giao dịch mới qua WebSocket (Async)
async def listen_for_transactions():
    while True:
        try:
            async with websockets.connect(INFURA_WS_URL) as ws:
                print("🔍 Đang lắng nghe block mới trên Base...")

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
                            await handle_new_block(block_hash)

        except Exception as e:
            print(f"❌ Lỗi WebSocket: {e}")
            await asyncio.sleep(5)

# Chạy chương trình
asyncio.run(listen_for_transactions())
