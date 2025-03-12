import requests
import pandas as pd
import time
from telebot import TeleBot
from flask import Flask

# ✅ Telegram Bot Bilgileri
TELEGRAM_BOT_TOKEN = "7583261338:AAHASreSYIaX-6QAXIUflpyf5HnbQXq81Dg"
TELEGRAM_CHAT_ID = "5124859166"
bot = TeleBot(TELEGRAM_BOT_TOKEN)

# ✅ CoinGecko API URL
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# ✅ Flask Web Server
app = Flask(__name__)

@app.route("/")
def home():
    return "Trade Sinyal Botu Çalışıyor 🚀"

# 📌 **Fiyat Alma Fonksiyonu**
def get_price(coin):
    try:
        response = requests.get(f"{COINGECKO_API_URL}/simple/price?ids={coin}&vs_currencies=usd")
        data = response.json()
        return data[coin]["usd"]
    except Exception as e:
        print(f"⚠️ {coin} fiyat alınırken hata oluştu: {e}")
        return None

# 📌 **Telegram Mesaj Gönderme**
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"✅ Telegram Mesajı Gönderildi: {message}")
        else:
            print(f"⚠️ Telegram mesajı başarısız! Hata kodu: {response.status_code}")
    except Exception as e:
        print(f"🚨 Telegram mesajı gönderilemedi! Hata: {e}")

# 📌 **API ve Telegram Testleri**
def test_get_price():
    response = requests.get(f"{COINGECKO_API_URL}/simple/price?ids=bitcoin&vs_currencies=usd")
    return response.status_code == 200

def test_telegram():
    message = "✅ Telegram Bot Testi Başarılı!"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, json=payload)
    return response.status_code == 200

def run_tests():
    print("🚀 Otomatik Testler Başlatılıyor...")
    if not test_get_price():
        print("❌ API testi başarısız! Bot başlatılmıyor.")
        return False
    if not test_telegram():
        print("❌ Telegram testi başarısız! Bot başlatılmıyor.")
        return False
    print("✅ Tüm testler başarılı! Bot başlatılıyor...")
    return True

# 📌 **Bot Çalıştırma (Arka Planda Çalışır)**
def run_bot():
    coins = ["bitcoin", "ethereum", "binancecoin"]
    while True:
        for coin in coins:
            price = get_price(coin)
            if price:
                message = f"📢 {coin.upper()} Güncel Fiyat: {price} USD"
                send_telegram_message(message)
        time.sleep(3600)

# 📌 **Ana Çalıştırma**
if __name__ == "__main__":
    if run_tests():  # **Testler başarılıysa bot başlatılacak**
        send_telegram_message("🚀 Bot Başlatıldı! Fiyat güncellemeleri paylaşılacak.")
        # Botu arka planda başlatmak için ayrı bir thread kullan
        import threading
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.start()

    # Flask Web Server Başlat
    app.run(host="0.0.0.0", port=10000)
