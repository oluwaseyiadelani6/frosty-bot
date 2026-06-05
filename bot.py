import requests
import time
from datetime import datetime, timezone

BOT_TOKEN = "8947291068:AAFtY-wZ-O86a3C_MgaU7IgavZhhA9IALKg"
CHAT_ID = "7060467753"

alerted_pairs = set()
wallet_last_seen = {}

SMART_WALLETS = {
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": "Ansem",
    "DD9iSqQ7aD5HaUoB7ExmBhvs1ThWmqpKLFbZBzQiByAq": "Murad",
    "CuieVDEDtLo7FypDQJBiJqCTGBqXbmHYKQSCRMFNgEbx": "Rayhan"
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram error: {e}")

def get_boosted_pairs():
    url = "https://api.dexscreener.com/token-boosts/latest/v1"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if isinstance(data, list):
            return [p for p in data if p.get("chainId") == "solana"]
        return []
    except Exception as e:
        print(f"Boost fetch error: {e}")
        return []

def get_new_pumpfun_pairs():
    url = "https://api.dexscreener.com/latest/dex/search?q=pumpswap"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        pairs = data.get("pairs", [])
        return [p for p in pairs if p.get("chainId") == "solana"]
    except Exception as e:
        print(f"Pumpfun fetch error: {e}")
        return []

def get_token_details(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        pairs = data.get("pairs", [])
        return pairs[0] if pairs else None
    except:
        return None

def get_wallet_transactions(wallet_address):
    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions?api-key=free&limit=5"
    try:
        response = requests.get(url, timeout=15)
        return response.json() if response.status_code == 200 else []
    except:
        return []

def check_smart_wallets():
    for wallet, name in SMART_WALLETS.items():
        txns = get_wallet_transactions(wallet)
        if not txns or not isinstance(txns, list):
            continue
        latest_sig = txns[0].get("signature", "")
        if not latest_sig:
            continue
        if wallet_last_seen.get(wallet) == latest_sig:
            continue
        wallet_last_seen[wallet] = latest_sig
        for txn in txns[:3]:
            token_transfers = txn.get("tokenTransfers", [])
            for transfer in token_transfers:
                mint = transfer.get("mint", "")
                if not mint or mint in alerted_pairs:
                    continue
                if transfer.get("toUserAccount") == wallet:
                    details = get_token_details(mint)
                    if details:
                        token_name = details.get("baseToken", {}).get("name", "Unknown")
                        symbol = details.get("baseToken", {}).get("symbol", "???")
                        mcap = details.get("marketCap", 0) or 0
                        pair_url = details.get("url", "")
                        alerted_pairs.add(mint)
                        message = (
                            f"🧠 <b>SMART MONEY ALERT!</b>\n\n"
                            f"👤 <b>{name}</b> just bought:\n"
                            f"🪙 {token_name} (${symbol})\n"
                            f"📊 MCAP: ${mcap:,.0f}\n\n"
                            f"🔗 {pair_url}"
                        )
                        send_telegram(message)
                        print(f"🧠 Smart money: {name} bought {symbol}")

def is_fresh_coin(pair):
    created_at = pair.get("pairCreatedAt")
    if not created_at:
        return False
    created_time = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600
    return age_hours <= 6

def process_pair(details, source):
    if not details:
        return
    token_address = details.get("baseToken", {}).get("address", "")
    if not token_address or token_address in alerted_pairs:
        return
    volume = details.get("volume", {}).get("h24", 0) or 0
    liquidity = details.get("liquidity", {}).get("usd", 0) or 0
    mcap = details.get("marketCap", 0) or 0
    name = details.get("baseToken", {}).get("name", "Unknown")
    symbol = details.get("baseToken", {}).get("symbol", "???")
    price_change = details.get("priceChange", {}).get("h1", 0) or 0
    price_change_5m = details.get("priceChange", {}).get("m5", 0) or 0
    pair_url = details.get("url", "")

    if volume < 50000:
        return
    if liquidity < 20000:
        return
    if mcap < 50000:
        return
    if not is_fresh_coin(details):
        return
    if price_change < 20:
        return

    alerted_pairs.add(token_address)

    if price_change_5m > 5:
        momentum = "🔥 Still pumping!"
    elif price_change_5m > 0:
        momentum = "📊 Steady"
    else:
        momentum = "⚠️ Slowing"

    message = (
        f"🚨 <b>{name} (${symbol})</b>\n"
        f"📡 Source: {source}\n\n"
        f"💰 24H Vol: ${volume:,.0f}\n"
        f"💧 Liquidity: ${liquidity:,.0f}\n"
        f"📊 MCAP: ${mcap:,.0f}\n"
        f"📈 1H Change: +{price_change}%\n"
        f"⚡ 5M: {price_change_5m}% — {momentum}\n"
        f"✅ Fresh (under 6hrs)\n\n"
        f"🔗 {pair_url}"
    )
    send_telegram(message)
    print(f"✅ Alert: {symbol} | Vol: ${volume:,.0f} | Source: {source}")

def check_all():
    print("Scanning boosted tokens...")
    boosted = get_boosted_pairs()
    for pair in boosted:
        token_address = pair.get("tokenAddress", "")
        if token_address and token_address not in alerted_pairs:
            details = get_token_details(token_address)
            process_pair(details, "Boosted")

    print("Scanning Pump.fun launches...")
    pumpfun = get_new_pumpfun_pairs()
    for pair in pumpfun:
        process_pair(pair, "Pump.fun")

    print("Checking smart wallets...")
    check_smart_wallets()

print("🤖 Frosty Bot v3 — Boosted + Pump.fun + Smart Wallets 👀")
while True:
    check_all()
    time.sleep(60)
