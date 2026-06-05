import requests
import time
from datetime import datetime, timezone

BOT_TOKEN = "8947291068:AAFtY-wZ-O86a3C_MgaU7IgavZhhA9IALKg"
CHAT_ID = "7060467753"

alerted_pairs = set()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram error: {e}")

def get_solana_pairs():
    url = "https://api.dexscreener.com/token-boosts/latest/v1"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if isinstance(data, list):
            solana = [p for p in data if p.get("chainId") == "solana"]
            return solana
        return []
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def is_fresh_coin(pair):
    created_at = pair.get("pairCreatedAt")
    if not created_at:
        return True
    created_time = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600
    return age_hours <= 24

def check_pairs():
    pairs = get_solana_pairs()
    if not pairs:
        print("No pairs found, retrying...")
        return
    print(f"Found {len(pairs)} boosted Solana tokens")
    for pair in pairs:
        token_address = pair.get("tokenAddress", "")
        if token_address in alerted_pairs:
            continue
        name = pair.get("description", "Unknown")
        symbol = pair.get("tokenAddress", "???")[:8]
        pair_url = pair.get("url", "")
        alerted_pairs.add(token_address)
        message = (
            f"🚨 <b>BOOSTED TOKEN ALERT</b>\n\n"
            f"📝 {name}\n"
            f"✅ Active on Solana\n\n"
            f"🔗 {pair_url}"
        )
        send_telegram(message)
        print(f"Alert sent for {token_address[:8]}")

print("🤖 Frosty Bot running... Watching Solana pairs 👀")
while True:
    check_pairs()
    time.sleep(60)
