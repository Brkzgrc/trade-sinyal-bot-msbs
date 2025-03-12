import requests
import pandas as pd
import time
from telebot import TeleBot

# Telegram Bot Bilgileri
TELEGRAM_BOT_TOKEN = "7243733230:AAFw0XxLKiShamQcElSnXc984DdaXGvBoEQ"
TELEGRAM_CHAT_ID = "5124859166"
bot = TeleBot(TELEGRAM_BOT_TOKEN)

# CoinGecko API URL
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Fiyat bilgisini çekmek için fonksiyon
def get_price(symbol):
    try:
        response = requests.get(f"{COINGECKO_API_URL}/simple/price?ids={symbol}&vs_currencies=usd")
        data = response.json()
        return data[symbol]['usd']
    except Exception as e:
        print(f"Hata: {e}")
        return None

# OHLCV verisini çekmek için fonksiyon
def get_ohlcv(symbol):
    try:
        response = requests.get(f"{COINGECKO_API_URL}/coins/{symbol}/market_chart?vs_currency=usd&days=1&interval=hourly")
        data = response.json()
        ohlcv_data = data['prices']  # [timestamp, price]
        df = pd.DataFrame(ohlcv_data, columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
        return df
    except Exception as e:
        print(f"Hata: {e}")
        return None

# Telegram bildirim fonksiyonu
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print("Telegram mesajı gönderilirken hata:", e)

# Sinyal kontrolü
def check_signal(coin):
    df = get_ohlcv(coin)
    if df is None:
        return None

    latest_price = df["close"].iloc[-1]

    # RSI Hesaplama
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    latest_rsi = df["rsi"].iloc[-1]

    # Basit RSI sinyali (Örnek)
    if latest_rsi < 30:
        signal = "BUY"
    elif latest_rsi > 70:
        signal = "SELL"
    else:
        signal = "NO SIGNAL"

    return signal, latest_price, latest_rsi

# Ana loop
def run_bot():
    coins = ["bitcoin", "ethereum", "binancecoin"]
    while True:
        for coin in coins:
            signal, price, rsi = check_signal(coin)
            if signal != "NO SIGNAL":
                message = f"📢 {coin.upper()} Sinyali: {signal}\n💰 Fiyat: {price} USD\n📊 RSI: {rsi:.2f}"
                send_telegram_message(message)
        time.sleep(3600)

# Botu başlat
if __name__ == "__main__":
    send_telegram_message("🚀 Bot Başlatıldı!")
    run_bot()
