import requests
import telebot
from flask import Flask, request

# ✅ Telegram Bot Bilgileri
TELEGRAM_BOT_TOKEN = "7583261338:AAHASreSYIaX-6QAXIUflpyf5HnbQXq81Dg"
TELEGRAM_CHAT_ID = "5124859166"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ✅ Flask Web Server
app = Flask(__name__)

@app.route("/")
def home():
    return "Trade Sinyal Botu Çalışıyor 🚀"

# 📌 **Telegram'da `/start` Komutunu Tanımla**
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "✅ Bot çalışıyor! Hoş geldin. 🚀")

# 📌 **Webhook Kullanarak Telegram'dan Mesajları Dinleme**
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

# 📌 **Botu Başlat**
def run_bot():
    bot.infinity_polling()

# 📌 **Ana Çalıştırma**
if __name__ == "__main__":
    # Webhook'u ayarla
    bot.remove_webhook()
    bot.set_webhook(url=f"https://trade-sinyal-bot-msbs.onrender.com/{TELEGRAM_BOT_TOKEN}")

    import threading
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Flask Web Server Başlat
    app.run(host="0.0.0.0", port=10000)
