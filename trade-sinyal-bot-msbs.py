import ccxt
import pandas as pd
import datetime
import requests
import tkinter as tk
from tkinter import scrolledtext
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import math

# API bilgileriniz:
TELEGRAM_TOKEN = '7243733230:AAFw0XxLKiShamQcElSnXc984DdaXvBoEQ'
CHAT_ID = '5124859166'

# KAMA hesaplaması (HPotter versiyonu)
def compute_kama(series, length=21, nfastend=0.666, nslowend=0.0645):
    kama = np.zeros(len(series))
    kama[0] = series.iloc[0]
    for i in range(1, len(series)):
        if i < length:
            kama[i] = kama[i-1]
        else:
            nsignal = abs(series.iloc[i] - series.iloc[i-length])
            nnoise = np.sum(np.abs(series.iloc[i-length+1:i+1].values - series.iloc[i-length:i].values))
            nefratio = nsignal / nnoise if nnoise != 0 else 0
            nsmooth = (nefratio * (nfastend - nslowend) + nslowend) ** 2
            kama[i] = kama[i-1] + nsmooth * (series.iloc[i] - kama[i-1])
    return kama

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_adx(data, period=14):
    data['prev_close'] = data['close'].shift(1)
    data['high_low'] = data['high'] - data['low']
    data['high_prev_close'] = (data['high'] - data['prev_close']).abs()
    data['low_prev_close'] = (data['low'] - data['prev_close']).abs()
    data['TR'] = data[['high_low', 'high_prev_close', 'low_prev_close']].max(axis=1)
    data['TR_sma'] = data['TR'].rolling(window=period).mean()
    
    data['plus_dm'] = data['high'] - data['high'].shift(1)
    data['minus_dm'] = data['low'].shift(1) - data['low']
    data['plus_dm'] = data.apply(lambda x: x['plus_dm'] if (x['plus_dm'] > x['minus_dm'] and x['plus_dm'] > 0) else 0, axis=1)
    data['minus_dm'] = data.apply(lambda x: x['minus_dm'] if (x['minus_dm'] > x['plus_dm'] and x['minus_dm'] > 0) else 0, axis=1)
    
    data['plus_dm_sum'] = data['plus_dm'].rolling(window=period).sum()
    data['minus_dm_sum'] = data['minus_dm'].rolling(window=period).sum()
    
    data['plus_di'] = 100 * (data['plus_dm_sum'] / data['TR_sma'])
    data['minus_di'] = 100 * (data['minus_dm_sum'] / data['TR_sma'])
    
    data['dx'] = 100 * abs(data['plus_di'] - data['minus_di']) / (data['plus_di'] + data['minus_di'])
    adx = data['dx'].rolling(window=period).mean()
    return adx

# Temel 5 indikatör: Bollinger Bands, RSI, MACD, ADX, VWAP
def fetch_signal(symbol):
    try:
        exchange = ccxt.binance({'timeout':30000})
        timeframe = '5m'
        limit = 100
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        data = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
        data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
        
        # Bollinger Bands
        window = 20
        mult = 2
        data['MA20'] = data['close'].rolling(window=window).mean()
        data['std20'] = data['close'].rolling(window=window).std()
        data['UpperBand'] = data['MA20'] + mult * data['std20']
        data['LowerBand'] = data['MA20'] - mult * data['std20']
        
        # VWAP
        data['typical_price'] = (data['high'] + data['low'] + data['close']) / 3
        vol_cumsum = data['volume'].cumsum()
        data['vwap'] = (data['typical_price'] * data['volume']).cumsum() / vol_cumsum
        
        # RSI
        data['rsi'] = compute_rsi(data['close'], period=14)
        
        # MACD
        data['ema12'] = data['close'].ewm(span=12, adjust=False).mean()
        data['ema26'] = data['close'].ewm(span=26, adjust=False).mean()
        data['macd'] = data['ema12'] - data['ema26']
        data['signal_line'] = data['macd'].ewm(span=9, adjust=False).mean()
        macd_buy = data['macd'].iloc[-2] < data['signal_line'].iloc[-2] and data['macd'].iloc[-1] > data['signal_line'].iloc[-1]
        macd_sell = data['macd'].iloc[-2] > data['signal_line'].iloc[-2] and data['macd'].iloc[-1] < data['signal_line'].iloc[-1]
        
        # ADX
        data['adx'] = compute_adx(data, period=14)
        
        # Hacim Onayı
        data['vol_ma'] = data['volume'].rolling(window=20).mean()
        volume_surge = data['volume'].iloc[-1] > 1.2 * data['vol_ma'].iloc[-1]
        
        latest_close = data['close'].iloc[-1]
        if latest_close == 0:
            return f"{symbol}\nSinyal tespit edilemedi."
        latest_upper = data['UpperBand'].iloc[-1]
        latest_lower = data['LowerBand'].iloc[-1]
        latest_rsi = data['rsi'].iloc[-1]
        latest_adx = data['adx'].iloc[-1]
        latest_vwap = data['vwap'].iloc[-1]
        
        # KAMA hesaplaması (6. temel indikatör)
        kama = compute_kama(data['close'], length=21, nfastend=0.666, nslowend=0.0645)
        
        # Şimdi temel 6 indikatör koşullarını belirleyelim:
        # Alım senaryosu: Fiyat üst bandı kırıyor, RSI uygun aralıkta, MACD bullish, ADX > 20, fiyat > VWAP, fiyat > KAMA.
        # Satım senaryosu: Fiyat alt bandı kırıyor, RSI uygun aralıkta, MACD bearish, ADX > 20, fiyat < VWAP, fiyat < KAMA.
        if latest_close > latest_upper:
            cond_bollinger = True
            cond_rsi = (latest_rsi > 45 and latest_rsi < 75)
            cond_macd = macd_buy
            cond_adx = latest_adx > 20
            cond_vwap = (latest_close > latest_vwap)
            cond_kama = (latest_close > kama[-1])
        elif latest_close < latest_lower:
            cond_bollinger = True
            cond_rsi = (latest_rsi < 55 and latest_rsi > 25)
            cond_macd = macd_sell
            cond_adx = latest_adx > 20
            cond_vwap = (latest_close < latest_vwap)
            cond_kama = (latest_close < kama[-1])
        else:
            cond_bollinger = cond_rsi = cond_macd = cond_adx = cond_vwap = cond_kama = False
        
        conditions = [cond_bollinger, cond_rsi, cond_macd, cond_adx, cond_vwap, cond_kama]
        onay_count = sum(1 for cond in conditions if cond)
        
        print(f"{symbol} - İndikatör Onay Sayısı: {onay_count}/6", flush=True)
        
        # Sinyal yalnızca temel 6 indikatörün tamamı onaylanırsa üretilir.
        if onay_count == 6:
            signal = "BUY" if latest_close > latest_upper else "SELL"
        else:
            signal = "NO SIGNAL"
        
        # 4 saatlik RSI hesaplaması (ek bilgi, uyarıda gösterilecek)
        rsi_4h = fetch_tf_rsi(symbol, '4h', period=14)
        optimal_rsi_4h = 26  # Örnek optimal değer
        rsi_marker = "!" if abs(rsi_4h - optimal_rsi_4h) / optimal_rsi_4h >= 0.10 else ""
        
        if signal in ["BUY", "SELL"] and len(data) >= 2:
            previous_close = data['close'].iloc[-2]
            boost_value = ((latest_close - previous_close) / previous_close) * 100
            risk_dot = "🟢" if abs(boost_value) < 1 else ("🟠" if abs(boost_value) < 3 else "🔴")
            entry_price = latest_close
            if signal == "BUY":
                details = (f"🟢 #{symbol}\nAlım Fiyatı: {entry_price:.4f}\nArtış Değeri: {boost_value:+.2f}% {risk_dot}\n"
                           f"Güncel Fiyat: {latest_close:.4f}\nÖnceki Fiyat: {previous_close:.4f}\n"
                           f"İndikatör Onay Sayısı: {onay_count}/6\n4h RSI: {rsi_4h:.2f}{rsi_marker}")
            else:
                details = (f"🔴 #{symbol}\nSatım Fiyatı: {entry_price:.4f}\nArtış Değeri: {boost_value:+.2f}% {risk_dot}\n"
                           f"Güncel Fiyat: {latest_close:.4f}\nÖnceki Fiyat: {previous_close:.4f}\n"
                           f"İndikatör Onay Sayısı: {onay_count}/6\n4h RSI: {rsi_4h:.2f}{rsi_marker}")
        else:
            details = f"{symbol}\nSinyal tespit edilemedi.\n4h RSI: {rsi_4h:.2f}{rsi_marker}"
        
        return details
    except Exception as e:
        print(f"{symbol} için sinyal hesaplanırken hata:", e, flush=True)
        return f"{symbol}\nHATA"

def fetch_tf_rsi(symbol, timeframe='4h', period=14):
    exchange = ccxt.binance({'timeout':30000})
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=period+1)
    df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    rsi_val = compute_rsi(df['close'], period=period)
    return rsi_val.iloc[-1]

def get_usdt_pairs():
    try:
        exchange = ccxt.binance({'timeout':30000})
        markets = exchange.load_markets()
        usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT')]
        return usdt_pairs
    except Exception as e:
        print("get_usdt_pairs() içinde hata:", e, flush=True)
        return []

class AlertApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trade Uyarıları")
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=50, height=15)
        self.text_area.pack(padx=10, pady=10)
        self.display_alert("GUI Test Mesajı")
        self.root.after(0, self.update_signal)

    def display_alert(self, message):
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.see(tk.END)

    def update_signal(self):
        print("update_signal çağrıldı.", flush=True)
        def worker():
            try:
                print("worker başladı.", flush=True)
                usdt_pairs = get_usdt_pairs()
                with ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_pair = {executor.submit(fetch_signal, pair): pair for pair in usdt_pairs}
                    for future in as_completed(future_to_pair):
                        pair = future_to_pair[future]
                        try:
                            signal_message = future.result()
                            print(f"Finished processing {pair}", flush=True)
                            if "BUY" in signal_message or "SELL" in signal_message:
                                self.root.after(0, lambda msg=signal_message: self.process_result(msg))
                        except Exception as inner_e:
                            print(f"Hata {pair} için: {inner_e}", flush=True)
                print("worker bitiyor.", flush=True)
            except Exception as e:
                print("Worker içinde hata:", e, flush=True)
        threading.Thread(target=worker).start()
        self.root.after(30000, self.update_signal)

    def process_result(self, message):
        print("process_result çağrıldı.", flush=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_message = f"{timestamp}\n{message}\n{'-'*80}"
        self.display_alert(final_message)
        send_telegram_message(final_message)
        print("process_result bitiyor, final mesaj:", final_message, flush=True)

if __name__ == "__main__":
    root = tk.Tk()
    # İstenen pencere ayarı: "400x250+4050+20"
    root.geometry("400x250+4050+20")
    app = AlertApp(root)
    root.mainloop()
