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
    url = "https://chainid.network/chains.json"
    for attempt in range(3):  # Try 3 times
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()  
            chains = response.json()
            for chain in chains:
                if chain['chainId'] == chain_id:
                    return chain['name']
        except requests.exceptions.RequestException as e:
            error_message_getchainname = f"⚠️ API error: {e} (Attempt {attempt + 1})"
            print(error_message_getchainname)
            send_telegram_message(error_message_getchainname)
            time.sleep(3) 

    return "Unknown Chain"

# Create database and table if not exist
def create_database_and_table():
    temp_config = data_config.copy()
    temp_config.pop("database")

    try:
        connection = mysql.connector.connect(**temp_config)
        cursor = connection.cursor()

        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall()]

        if data_config['database'] in databases:
            print(f"Database {data_config['database']} already exists.")
        else:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {data_config['database']}")
            print(f"Database {data_config['database']} newly created")
        
        # Clear database list after use
        del databases  

        connection.database = data_config['database']

        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]

        if "bond_history" in tables:
            print("Table bond_history already exists.")
        else:
            create_table_query = """
                CREATE TABLE IF NOT EXISTS bond_history(
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        bond_name VARCHAR(255) NOT NULL,
                        contract_address VARCHAR(255) NOT NULL,
                        date_time DATETIME NOT NULL,
                        bonus DECIMAL(10, 2) NOT NULL,
                        min_price DECIMAL(18, 2) NOT NULL,
                        max_price DECIMAL(18, 2) NOT NULL,
                        max_buy DECIMAL(18, 2) NOT NULL
                ) ENGINE=InnoDB;
            """
            cursor.execute(create_table_query)
            print("Table bond_history newly created")
        
        # Clear table list after use
        del tables 

        connection.commit()

    except mysql.connector.Error as e:
        error_message_sql = f"Error creating database/table: {e}"
        print(error_message_sql)
        send_telegram_message(error_message_sql)
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    
    gc.collect()

# Get data from API and process function
def process_bonds():
    try:
        # Create database and table if not exist
        create_database_and_table()

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
        bonds = data.get("bonds", [])
        sorted_bonds = sorted(bonds, key=lambda bond: float(bond.get("bonus", "-inf")), reverse=True)
        top_10_bonds = sorted_bonds[:10]

        # Create message content
        text_message = ""
        for bond in top_10_bonds:
            chain_name = get_chain_name(bond.get('chainId', 0))[:3]
            bond_name = bond.get('payoutTokenName', 'Unknown')
            bonus_value = float(bond.get("bonus", 0) or 0)
            bonus = f"{bonus_value:.2f}"

            text_message += f"- {chain_name} {bond_name} {bonus}%\n"

            # Lấy thông tin cho database
            contract_address = bond.get("billAddress", "N/A")
            date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

            true_bill_price = float(bond.get('trueBillPrice', 0) or 0)
            principal_decimals = max(1, int(bond.get('principalTokenDecimals', 0) or 1))
            min_price = f"{true_bill_price / (10 ** principal_decimals):.2f}"

            max_total_payout = float(bond.get('maxTotalPayout', 0) or 0)
            payout_decimals = max(1, int(bond.get('payoutTokenDecimals', 0) or 1))
            max_price = f"{max_total_payout / (10 ** payout_decimals):.2f}"

            max_payout = float(bond.get('maxPayout', 0) or 0)
            max_buy = f"{max_payout / (10 ** payout_decimals):.2f}"

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