import requests
import mysql.connector
from datetime import datetime, time as dt_time, timedelta
import time
import gc  # Garbage Collection

MAX_RETRIES = 10 
RETRY_DELAY = 60 

error_count = 0

# Data config setting
data_config = {
    "host": "itdragons.com",      
    "user": "apebond",               
    "password": "it.d@2025",
    "database": "apebond",
    "port": 3307,
    "ssl_disabled": True
}

# Telegram Bot API token and chat ID
api_token = "7541502749:AAHO0ro39ZhMhS8gHFNy9DeKcaE5Ux7CUyU"
chat_id = "-1002343293739"

# API URL for bonds
api_url = "https://realtime-api.ape.bond/bonds"

# Bebtime setting
bedtime_start = dt_time(23, 30)
bedtime_end = dt_time(7, 0)

# Check if it's bedtime
def set_bedtime():
    now = datetime.now().time()
    if bedtime_start < bedtime_end:
        return bedtime_start <= now < bedtime_end
    else:
        return now >= bedtime_start or now < bedtime_end

# Send Telegram message function
def send_telegram_message(message):
    telegram_url = f"https://api.telegram.org/bot{api_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        response = requests.post(telegram_url, data=payload, timeout=5)
        print(f"Response from Telegram: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send message to Telegram: {e}")

# Sleep to wake up time
def sleep_until_wakeup():
    now = datetime.now()
    wakeup_time = datetime.combine(now.date(), bedtime_end)

    if now.time() >= bedtime_end:
        wakeup_time += timedelta(days=1)

    sleep_seconds = (wakeup_time - now).total_seconds()

    sleep_message = f"💤🤖 Bot is sleeping. Sleep {str(timedelta(seconds=int(sleep_seconds)))} seconds."
    print(sleep_message)
    send_telegram_message(sleep_message)
    time.sleep(sleep_seconds)

# Get chain name from chain ID function
def get_chain_name(chain_id):
    try:
        response = requests.get("https://chainid.network/chains.json", timeout=5)
        chains = response.json()
        for chain in chains:
            if chain['chainId'] == chain_id:
                return chain['name']
    except Exception:
        pass
    return "Unknown Chain"

# Get data from API and process function
def process_bonds():
    try:
        # Connect to database
        connection = mysql.connector.connect(**data_config)
        cursor = connection.cursor()

        # Call API to get list bonds
        response = requests.get(api_url, timeout=5)
        if response.status_code != 200:
            raise Exception(f"❌ API return status code {response.status_code}")

        data = response.json()
        if "bonds" not in data:
            raise Exception("❌ API don't have bonds data")

        # Process list bonds by % bonus
        bonds = data["bonds"]
        sorted_bonds = sorted(bonds, key=lambda bond: bond["bonus"] if bond["bonus"] else float('-inf'), reverse=True)
        top_10_bonds = sorted_bonds[:10]

        # Create message content
        text_message = ""
        for bond in top_10_bonds:
            chain_name = get_chain_name(bond['chainId'])[:3]
            bond_name = bond['payoutTokenName']
            bonus = f"{bond['bonus']:.2f}"

            text_message += f"- {chain_name} {bond_name} {bonus}%\n"

            # Prepare data to save to database
            contract_address = bond["billAddress"]
            date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            min_price = f"{float(bond['trueBillPrice']) / (10 ** int(bond['principalTokenDecimals'])):,.2f}".replace(",", "")
            max_price = f"{float(bond['maxTotalPayout']) / (10 ** int(bond['payoutTokenDecimals'])):,.2f}".replace(",", "")
            max_buy = f"{float(bond['maxPayout']) / (10 ** int(bond['payoutTokenDecimals'])):,.2f}".replace(",", "")

            insert_query = """
                INSERT INTO bond_history (bond_name, contract_address, date_time, bonus, min_price, max_price, max_buy)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            data = (bond_name, contract_address, date_time, bonus, min_price, max_price, max_buy)
            cursor.execute(insert_query, data)

        # Send message to telegram
        if text_message:
            send_telegram_message(text_message)

        # Save data to database
        connection.commit()

    except Exception as e:
        error_message = f"⚠️ *Error happened in process_bonds:* {str(e)}"
        send_telegram_message(error_message)  
        print(error_message)

    finally:
        # Close connection database
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

        # Free up memory
        del bonds, sorted_bonds, top_10_bonds, text_message, data
        gc.collect()

if __name__ == "__main__":
    while True:
        try:
            if set_bedtime():
                sleep_until_wakeup()
            else:
                process_bonds()
                time.sleep(900) 
            error_count = 0
        except Exception as e:
            error_message = f"❗ *Fatal error in main loop:* {str(e)}"
            send_telegram_message(error_message)
            print(error_message)

            error_count += 1
            if error_count >= MAX_RETRIES:
                critical_message = "🚨 *Too many errors! Stopping program.*"
                send_telegram_message(critical_message)
                print(critical_message)
                break  

            time.sleep(RETRY_DELAY) 