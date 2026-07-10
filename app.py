from flask import Flask
import threading
import os
import asyncio
from telethon import TelegramClient, events
import requests
from datetime import datetime, timedelta

# ========== تنظیمات ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("GROQ_API_KEY")
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
SECRET_CODE = "1729"
MAX_FREE_MESSAGES = 10
BOT_NAME = "تام"
user_data = {}

# ========== توابع ==========
def get_response(user_message, user_id):
    now = datetime.now()
    
    if user_id not in user_data:
        user_data[user_id] = {"count": 0, "reset_time": now + timedelta(days=1)}
    
    user_info = user_data[user_id]
    
    if now >= user_info["reset_time"]:
        user_info["count"] = 0
        user_info["reset_time"] = now + timedelta(days=1)
    
    if user_message.strip() == SECRET_CODE:
        user_info["count"] = 0
        user_info["reset_time"] = now + timedelta(days=1)
        return f"🎉 آفرین! ۱۰ تا حرف تازه داری 😊"
    
    if user_info["count"] >= MAX_FREE_MESSAGES:
        time_left = user_info["reset_time"] - now
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        return f"🙈 حرفام تموم شد!\n⏳ {hours} ساعت و {minutes} دقیقه دیگه بیا\nیا رمز `1729` رو بگو"
    
    user_info["count"] += 1
    remaining = MAX_FREE_MESSAGES - user_info["count"]
    time_left = user_info["reset_time"] - now
    hours = int(time_left.total_seconds() // 3600)
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": f"تو یک مارمولک هستی به اسم {BOT_NAME}."},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=15)
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        return f"{reply}\n\n💬 {remaining} تا مونده (تا {hours} ساعت دیگه)"
    except:
        return f"😅 یه چیزی اشتباه شد! دوباره بگو؟"

# ========== راه‌اندازی ربات با Telethon ==========
async def run_bot():
    client = TelegramClient('bot_session', api_id=6, api_hash='eb06d4abfb49dc3eeb1aeb98ae0f581e').start(bot_token=BOT_TOKEN)
    
    @client.on(events.NewMessage(pattern='/start'))
    async def start(event):
        await event.reply(f"🦎 سلام! من {BOT_NAME} هستم، یه مارمولک! ۱۰ تا حرف داری، بعدش رمز 1729 رو بگو.")
    
    @client.on(events.NewMessage)
    async def handle_message(event):
        if event.out or not event.message.message:
            return
        if event.message.message.startswith('/'):
            return
        reply = get_response(event.message.message, event.sender_id)
        await event.reply(reply)
    
    await client.start()
    print(f"🦎 {BOT_NAME} در حال اجراست...")
    await client.run_until_disconnected()

# ========== راه‌اندازی Flask ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "ربات تام آنلاین است! 🦎"

@app.route('/health')
def health():
    return "OK", 200

# ========== اجرا ==========
if __name__ == "__main__":
    # ربات رو توی یه thread جداگانه اجرا کن
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def start_bot():
        loop.run_until_complete(run_bot())
    
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
