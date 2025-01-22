import requests
import time

# Telegram Bot API token and chat ID
api_token = "7541502749:AAHO0ro39ZhMhS8gHFNy9DeKcaE5Ux7CUyU"
chat_id = "5696892272"

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
sorted_bonds = sorted(bonds, key=lambda bond: bond["bonus"], reverse=True)
top_10_bonds = sorted_bonds[:10]

# Build the message
text_message = "🚀 **Danh sách 10 bond có % bonus cao nhất** 🚀\n\n"
text_message += "*Thông tin các bond:* \n"
for index, bond in enumerate(top_10_bonds, start=1):
    bond_name = f"{bond['principalTokenName']}-{bond['payoutTokenName']}"
    contract_address = bond["principalToken"]
    date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())  # Current time
    bonus = f"{bond['bonus']:.2f}%"
    min_price = f"{float(bond['trueBillPrice']) / (10 ** int(bond['principalTokenDecimals'])):,.2f}"
    max_price = f"{float(bond['maxTotalPayout']) / (10 ** int(bond['payoutTokenDecimals'])):,.2f}"
    max_buy = f"{float(bond['maxPayout']) / (10 ** int(bond['payoutTokenDecimals'])):,.2f}"

    text_message += f"Bond #{index}:\n"
    text_message += f"➡️ **Bond Name**: {bond_name}\n"
    text_message += f"➡️ **Contract Address**: {contract_address}\n"
    text_message += f"➡️ **Date-time**: {date_time}\n"
    text_message += f"➡️ **Bonus**: {bonus}\n"
    text_message += f"➡️ **Min Price**: {min_price} USDC\n"
    text_message += f"➡️ **Max Price**: {max_price} GPT\n"
    text_message += f"➡️ **Max Buy**: {max_buy} GPT\n"
    text_message += "─" * 40 + "\n"

# Send the message to Telegram
telegram_url = f"https://api.telegram.org/bot{api_token}/sendMessage"

payload = {
    "chat_id": chat_id,
    "text": text_message,
    "parse_mode": "Markdown",  # Use Markdown for formatting
}

telegram_response = requests.post(telegram_url, data=payload)

# Print Telegram API response
print("Response from Telegram:", telegram_response.text)