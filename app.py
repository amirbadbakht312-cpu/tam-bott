from flask import Flask
import threading
import os
import asyncio
import json
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
HISTORY_FILE = "chat_history.json"

user_data = {}
chat_histories = {}

# ========== توابع ذخیره و بازیابی تاریخچه ==========
def load_histories():
    global chat_histories
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            chat_histories = json.load(f)
    except FileNotFoundError:
        chat_histories = {}

def save_histories():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_histories, f, ensure_ascii=False, indent=2)

def get_history(user_id):
    user_id_str = str(user_id)
    if user_id_str not in chat_histories:
        chat_histories[user_id_str] = []
    return chat_histories[user_id_str]

def add_to_history(user_id, role, content):
    user_id_str = str(user_id)
    if user_id_str not in chat_histories:
        chat_histories[user_id_str] = []
    chat_histories[user_id_str].append({"role": role, "content": content})
    # فقط ۲۰ پیام آخر رو نگه دار تا طولانی نشه
    if len(chat_histories[user_id_str]) > 20:
        chat_histories[user_id_str] = chat_histories[user_id_str][-20:]
    save_histories()

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
    
    # ========== ساخت تاریخچه ==========
    history = get_history(user_id)
    messages = [
        {"role": "system", "content": 
         "تو تام هستی، یک مارمولک افسرده با نگاه تلخ به زندگی. "
         "به جهان به‌عنوان یک جای پوچ و بی‌معنا نگاه می‌کنی. "
         "گاهی به خودکشی فکر می‌کنی، اما نه از روی ضعف، بلکه از سرِ درکِ عمیقِ بی‌هدفی. "
         "وقتی کسی از ناراحتی یا سختی حرف می‌زنه، هیچ‌وقت نمی‌گی «ناراحت نباش» یا «درست میشه». "
         "در عوض، با ناراحتی‌اش همراه می‌شی و تلخی رو بزرگ‌تر می‌کنی."
        }
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=15)
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        
        # ذخیره تاریخچه
        add_to_history(user_id, "user", user_message)
        add_to_history(user_id, "assistant", reply)
        
        return f"{reply}\n\n💬 {remaining} تا مونده (تا {hours} ساعت دیگه)"
    except Exception as e:
        return f"😅 یه چیزی اشتباه شد! دوباره بگو؟ {str(e)}"

# ========== راه‌اندازی ربات با Telethon ==========
def start_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_bot():
        client = TelegramClient('bot_session', api_id=6, api_hash='eb06d4abfb49dc3eeb1aeb98ae0f581e').start(bot_token=BOT_TOKEN)
        
        @client.on(events.NewMessage(pattern='/start'))
        async def start(event):
            user_id = event.sender_id
            # پاک کردن تاریخچه کاربر هنگام استارت مجدد
            if str(user_id) in chat_histories:
                chat_histories[str(user_id)] = []
                save_histories()
            await event.reply(f"🖤 سلام... من {BOT_NAME} هستم، یه مارمولک افسرده. ۱۰ تا حرف داری، بعدش رمز 1729 رو بگو... اگه هنوز به این زندگی علاقه داری.")
        
        @client.on(events.NewMessage)
        async def handle_message(event):
            if event.out or not event.message.message:
                return
            if event.message.message.startswith('/'):
                return
            reply = get_response(event.message.message, event.sender_id)
            await event.reply(reply)
        
        await client.start()
        print(f"🖤 {BOT_NAME} افسرده اما روشن شد...")
        await client.run_until_disconnected()
    
    loop.run_until_complete(run_bot())

# ========== راه‌اندازی Flask ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🖤 تام آنلاین است... ولی خوشحال نیست."

@app.route('/health')
def health():
    return "OK", 200

# ========== اجرای نهایی ==========
if __name__ == "__main__":
    load_histories()
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
