import requests
import time
import mysql.connector
from datetime import datetime

# Data config setting
data_config = {
    "host": "localhost",          
    "user": "admin",               
    "password": "admin",  
    "database": "infura_io" 
}

# Connect to database
connection = mysql.connector.connect(**data_config)
cursor = connection.cursor()

# Telegram Bot API token and chat ID
api_token = "7541502749:AAHO0ro39ZhMhS8gHFNy9DeKcaE5Ux7CUyU"
chat_id = "371163595"

# API URL for bonds
api_url = "https://realtime-api.ape.bond/bonds"

# Fetch data from the bonds API
response = requests.get(api_url)
if response.status_code != 200:
    raise Exception("Failed to fetch data from API.")

data = response.json()
if "bonds" not in data:
    raise Exception("No bonds data available in the API response.")

# Process and sort bonds by % bonus
bonds = data["bonds"]
sorted_bonds = sorted(bonds, key=lambda bond: bond["bonus"] if bond["bonus"] is not None else float('-inf'), reverse=True)
top_10_bonds = sorted_bonds[:10]

# Bedtime setting
bedtime_start = "18:00"
bedtime_end = "07:00"

# Set Bedtime for sending message
def set_bedtime():
    now = datetime.now().time()
    start = datetime.strptime(bedtime_start, "%H:%M").time()
    end = datetime.strptime(bedtime_end, "%H:%M").time()

    if start <= now or now  < end:
        return True
    return False

# Get Chaine Name
def get_chain_name(chain_id):
    url = f"https://chainid.network/chains.json"
    response = requests.get(url)
    chains = response.json()

    for chain in chains:
        if chain['chainId'] == chain_id:
            return chain['name']

    return "Unknown Chain"

# Schedule send message to Telegram
def schedule_send_message():
    text_message = ""
    for index, bond in enumerate(top_10_bonds, start=1):
        chain_id = bond['chainId']
        bond_name = bond['payoutTokenName']
        contract_address = bond["billAddress"]
        date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())  # Current time
        bonus = f"{bond['bonus']:.2f}"
        min_price = f"{float(bond['trueBillPrice']) / (10 ** int(bond['principalTokenDecimals'])):,.2f}"
        max_price = f"{float(bond['maxTotalPayout']) / (10 ** int(bond['payoutTokenDecimals'])):,.2f}"
        max_buy = f"{float(bond['maxPayout']) / (10 ** int(bond['payoutTokenDecimals'])):,.2f}"

        # Insert data to database
        insert_query = """
            INSERT INTO bond_history (bond_name, contract_address, date_time, bonus, min_price, max_price, max_buy)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        data = (bond_name, contract_address, date_time, bonus, min_price.replace(",",""), max_price.replace(",",""), max_buy.replace(",",""))
        cursor.execute(insert_query, data)

        chain_name = get_chain_name(chain_id)

        text_message += f"- {chain_name[:3]} {bond_name} {bonus}%\n" 

    # Send the message to Telegram
    telegram_url = f"https://api.telegram.org/bot{api_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text_message,
        "parse_mode": "Markdown",  # Use Markdown for formatting
    }

    try:
        telegram_response = requests.post(telegram_url, data=payload)
        print(f"Response from Telegram: {telegram_response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message to Telegram: {e}")
        
    try:
        # Commit changes to the database
        connection.commit()
        print("Data saved successfully.")

    except mysql.connector.Error as e:
        print(f"Error saving data to the database: {e}")

if __name__ == "__main__":
    while True:
        if set_bedtime():
            print("It's bedtime. The message will soon be sent in the morning.")
            time.sleep(300)
            continue 

        schedule_send_message()
        time.sleep(300)