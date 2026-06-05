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
    url = "https://api.dexscreener.com/latest/dex/tokens/solana"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        pairs = data.get("pairs", [])
        return pairs if pairs else []
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def is_fresh_coin(pair):
    created_at = pair.get("pairCreatedAt")
    if not created_at:
        return False
    created_time = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600
    return age_hours <= 24

def is_already_peaked(pair):
    price_change_1h = pair.get("priceChange", {}).get("h1", 0) or 0
    price_change_5m = pair.get("priceChange", {}).get("m5", 0) or 0
    if price_change_1h > 20 and price_change_5m < -10:
        return True
    return False

def check_pairs():
    pairs = get_solana_pairs()
    if not pairs:
        print("No pairs found, retrying...")
        return
    for pair in pairs:
        pair_address = pair.get("pairAddress", "")
        if pair_address in alerted_pairs:
            continue
        volume = pair.get("volume", {}).get("h1", 0) or 0
        liquidity = pair.get("liquidity", {}).get("usd", 0) or 0
        name = pair.get("baseToken", {}).get("name", "Unknown")
        symbol = pair.get("baseToken", {}).get("symbol", "???")
        price_change_1h = pair.get("priceChange", {}).get("h1", 0) or 0
        price_change_5m = pair.get("priceChange", {}).get("m5", 0) or 0
        pair_url = pair.get("url", "")
        price_usd = pair.get("priceUsd", "N/A")
        if not (volume > 10000 and liquidity > 5000 and price_change_1h > 20):
            continue
        if not is_fresh_coin(pair):
            print(f"Skipping {symbol} - not a fresh coin")
            continue
        if is_already_peaked(pair):
            print(f"Skipping {symbol} - already peaked")
            continue
        alerted_pairs.add(pair_address)
        if price_change_5m > 5:
            momentum = "🔥 Still pumping!"
        elif price_change_5m > 0:
            momentum = "📊 Steady momentum"
        else:
            momentum = "⚠️ Slowing down"
        message = (
            f"🚨 <b>ALERT: {name} (${symbol})</b>\n\n"
            f"💰 Volume (1h): ${volume:,.0f}\n"
            f"💧 Liquidity: ${liquidity:,.0f}\n"
            f"📈 Price Change (1h): {price_change_1h}%\n"
            f"⚡ Last 5 mins: {price_change_5m}% — {momentum}\n"
            f"💵 Price: ${price_usd}\n"
            f"✅ Fresh coin (under 24hrs)\n"
            f"✅ Not peaked yet\n\n"
            f"🔗 {pair_url}"
        )
        send_telegram(message)
        print(f"Alert sent for {symbol}")

print("🤖 Frosty Bot running... Watching Solana pairs 👀")
while True:
    check_pairs()
    time.sleep(60)
