import os
import requests
import time
import pandas as pd
import ccxt  # Binance API ile veri çekmek için
from datetime import datetime
from telebot import TeleBot  # Telegram botu için

# Telegram Bot Token ve Chat ID
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
bot = TeleBot(TELEGRAM_BOT_TOKEN)

# Binance API Bağlantısı
binance = ccxt.binance()

# CoinMarketCap API Anahtarı (Ekstra analiz için)
CMC_API_KEY = "YOUR_COINMARKETCAP_API_KEY"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

# GUI Kullanım Kontrolü (Render'da False, Lokalde True)
USE_GUI = os.environ.get("RENDER") is None

if USE_GUI:
    import tkinter as tk
    root = tk.Tk()
    root.geometry("400x250+4050+20")
    root.mainloop()
else:
    print("GUI devre dışı, bot Telegram & Log tabanlı çalışıyor...")

# **📌 Teknik İndikatörler Hesaplama Fonksiyonları**
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data):
    short_ema = data.ewm(span=12, adjust=False).mean()
    long_ema = data.ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def calculate_bollinger_bands(data, window=20):
    sma = data.rolling(window=window).mean()
    std = data.rolling(window=window).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    return upper_band, lower_band

def calculate_mavilim_w(data):
    return data.ewm(span=21, adjust=False).mean()  # Basitleştirilmiş versiyon

def calculate_double_ema(data, period=21):
    ema1 = data.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    return (2 * ema1) - ema2

def calculate_kama(data, period=21):
    return data.ewm(span=period, adjust=False).mean()  # Basit versiyon

# **📌 Binance’ten Piyasa Verilerini Çekme**
def get_binance_data(symbol, timeframe='1h'):
    candles = binance.fetch_ohlcv(symbol, timeframe, limit=100)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# **📌 CoinMarketCap’ten Ek Verileri Çekme**
def get_coinmarketcap_data(symbol):
    headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
    params = {'symbol': symbol.replace('/USDT', ''), 'convert': 'USD'}
    response = requests.get(CMC_URL, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        coin = list(data['data'].values())[0]
        return {
            "market_cap": coin['quote']['USD']['market_cap'],
            "volume_24h": coin['quote']['USD']['volume_24h'],
            "circulating_supply": coin['circulating_supply']
        }
    return None

# **📌 Sinyal Üretme**
def analyze_coin(symbol):
    df = get_binance_data(symbol)
    close_prices = df['close']

    # **İndikatör Hesaplamaları**
    rsi = calculate_rsi(close_prices).iloc[-1]
    macd, signal = calculate_macd(close_prices)
    macd_signal = macd.iloc[-1] > signal.iloc[-1]
    upper_band, lower_band = calculate_bollinger_bands(close_prices)
    bollinger_signal = close_prices.iloc[-1] < lower_band.iloc[-1]
    mavilim_signal = close_prices.iloc[-1] > calculate_mavilim_w(close_prices).iloc[-1]
    double_ema_signal = close_prices.iloc[-1] > calculate_double_ema(close_prices).iloc[-1]
    kama_signal = close_prices.iloc[-1] > calculate_kama(close_prices).iloc[-1]

    # **Sinyal Onay Sistemi**
    indicators_confirmed = sum([rsi < 30, macd_signal, bollinger_signal, mavilim_signal, double_ema_signal, kama_signal])
    total_indicators = 6
    confirmation_ratio = f"{indicators_confirmed}/{total_indicators}"

    # **CoinMarketCap Ek Verileri**
    cmc_data = get_coinmarketcap_data(symbol)
    market_cap = cmc_data["market_cap"] if cmc_data else "Bilinmiyor"
    volume_24h = cmc_data["volume_24h"] if cmc_data else "Bilinmiyor"

    # **Sinyal Üretme Kararı**
    if indicators_confirmed >= 5:
        signal_text = f"""
🟢 **ALIM SİNYALİ** 🟢
Coin: {symbol}
Fiyat: {close_prices.iloc[-1]:.4f} USDT
İndikatör Onayı: {confirmation_ratio}
📊 Piyasa Değeri: {market_cap:,} USD
📉 24s Hacim: {volume_24h:,} USD
"""
        bot.send_message(TELEGRAM_CHAT_ID, signal_text)
        print(signal_text)
        with open("trade_signals.log", "a") as log_file:
            log_file.write(signal_text + "\n")
    else:
        print(f"{symbol}: Yetersiz onay ({confirmation_ratio})")

# **📌 Ana Döngü**
def main():
    while True:
        coins = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "ADA/USDT", "BNB/USDT", "SOL/USDT"]
        for coin in coins:
            analyze_coin(coin)
        time.sleep(1800)  # 30 Dakika Arayla Çalıştır

if __name__ == "__main__":
    main()
