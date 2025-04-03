from web3 import Web3
import requests
import datetime

# Get all min transaction of token based on contract address and token id
def get_mint_transactions(contract_address, token_id, bsc_api_key):
    # convert tokenId to hex (64 chars)
    token_id_hex = hex(token_id)[2:].zfill(64)
    # print(f"Token ID Hex: {token_id_hex}")

    # API get Transfer event (mint/buy)
    api_url = f"https://api.bscscan.com/api?module=logs&action=getLogs&address={contract_address}&fromBlock=0&toBlock=99999999&topic0=0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef&topic3=0x{token_id_hex}&apikey={bsc_api_key}"

    response = requests.get(api_url)
    logs = response.json()

    if response.status_code == 200 and "result" in logs and len(logs["result"]) > 0:
        print(f"✅ Found {len(logs['result'])} transactions matching Token ID {token_id}")

        mint_transactions = [] 

        for log_entry in logs["result"]:
            tx_hash = log_entry["transactionHash"]
            time_stamp = int(log_entry["timeStamp"], 16)
            time_stamp = datetime.datetime.fromtimestamp(time_stamp)
            formatted_time = time_stamp.strftime("%m-%d-%Y %H:%M:%S")
            print(f"Converted Time: {formatted_time}")
            
            topics = log_entry["topics"]
            from_address_transaction = Web3.to_checksum_address("0x" + topics[1][-40:])
            print(f"Address transaction: {from_address_transaction}")

            # Check if this is a mint event (from_address = 0x0000000000000000000000000000000000000000)
            if from_address_transaction == "0x0000000000000000000000000000000000000000":
                print(f"\n✅ Processing transaction: {tx_hash}")

                action = "Add Liquidity"
                time_stamp_formatted = formatted_time
                tx_hash_mint = tx_hash
                
                # API get trannsaction receipt
                receipt_url = f"https://api.bscscan.com/api?module=proxy&action=eth_getTransactionReceipt&txhash={tx_hash}&apikey={bsc_api_key}"

                receipt_response = requests.get(receipt_url)
                receipt_data = receipt_response.json()

                if "result" in receipt_data and receipt_data["result"]:
                    logs = receipt_data["result"]["logs"]

                    for log in logs:
                        contract_address = log["address"]

                        # Get data Transfer(address,address,uint256)
                        topics = log["topics"]
                        if len(topics) == 3:  # Ensure correct event Transfer
                            from_address = Web3.to_checksum_address("0x" + topics[1][-40:])
                            to_address = Web3.to_checksum_address("0x" + topics[2][-40:])
                            value = int(log["data"], 16) 

                            mint_transactions.append({
                                "transaction_hash": tx_hash,
                                "token_contract": contract_address,
                                "from_address": from_address,
                                "to_address": to_address,
                                "value": value / 10**18,  
                                "time_stamp": formatted_time,
                                "action": action
                            })
                else:
                    print(f"❌ No logs found for transaction: {tx_hash}")
            else:
                print(f"❌ This is not a mint event for transaction: {tx_hash}")

        return mint_transactions, action, time_stamp_formatted, tx_hash_mint
    else:
        print("❌ No transactions found for this tokenId")
        return []

