import requests
import time
import ccxt
from telebot import TeleBot
from flask import Flask

# Telegram Bot Bilgileri
TELEGRAM_BOT_TOKEN = "7583261338:AAHASreSYIaX-6QAXIUflpyf5HnbQXq81Dg"
TELEGRAM_CHAT_ID = "5124859166"
bot = TeleBot(TELEGRAM_BOT_TOKEN)

# Binance API Bağlantısı
exchange = ccxt.binance()

# Flask Web Server
app = Flask(__name__)

@app.route("/")
def home():
    return "Trade Sinyal Botu Çalışıyor 🚀"

# **Fiyat Bilgisi Çekme**
def get_price(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker['last']
    except Exception as e:
        print(f"⚠️ Hata: {symbol} fiyat alınamadı! {e}")
        return None

# **Sinyal Üretme Fonksiyonu**
def generate_signal(symbol):
    try:
        # Güncel fiyatı al
        price = get_price(symbol)
        if price is None:
            return None
        
        # RSI, Bollinger Bands, MACD gibi teknik göstergeler hesaplanacak
        rsi = 55  # Geçici veri, hesaplanacak
        macd = 0.002  # Geçici veri, hesaplanacak
        bollinger = "Üst Bant"  # Geçici veri, hesaplanacak
        
        # Risk Seviyesi
        risk_level = "🟢 Güvenli" if rsi > 50 and macd > 0 else "🟠 Orta Risk" if rsi > 40 else "🔴 Yüksek Risk"
        
        # **Sinyal Şablonu**
        message = (
            f"📢 #{symbol}\n"
            f"Güncel Fiyat: {price} USDT\n"
            f"RSI: {rsi}\n"
            f"MACD: {macd}\n"
            f"Bollinger: {bollinger}\n"
            f"Risk Değerlendirmesi: {risk_level}"
        )
        return message
    except Exception as e:
        print(f"⚠️ Sinyal oluşturulamadı: {e}")
        return None

# **Telegram Mesaj Gönderme**
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("⚠️ Telegram mesajı gönderilemedi!", e)

# **Ana Bot Döngüsü**
def run_bot():
    pairs = [market['symbol'] for market in exchange.load_markets().values() if "/USDT" in market['symbol']]
    while True:
        for pair in pairs:
            signal = generate_signal(pair)
            if signal:
                send_telegram_message(signal)
        time.sleep(1800)  # 30 dakika bekleme süresi

# **Ana Çalıştırma**
if __name__ == "__main__":
    send_telegram_message("🚀 Bot Başlatıldı! Sinyaller paylaşılacak.")
    run_bot()
    
    # Flask Web Server Başlat
    app.run(host="0.0.0.0", port=10000)
