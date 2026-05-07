import os
import re
import whisper
import subprocess
import sys
import requests
import sys
import json
from datetime import datetime

from automation.zepto_automation import run_zepto
playwright_instances = {}

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from playwright.sync_api import sync_playwright
# 🔥 Load model (safe)
model = whisper.load_model("base")


# ================= CONFIG =================
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Load Whisper model once
model = whisper.load_model("base")

# Store user state
user_data_store = {}

print("SCRIPT STARTED")

items = None
user_id = None

# ✅ Handle subprocess input safely
if len(sys.argv) > 2:
    import json
    items = json.loads(sys.argv[1])
    user_id = sys.argv[2]

    print("Items:", items)
    print("User:", user_id)


# ================= STEP 1: START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Send me a voice note to order food 🎤"
    )

# ================= STEP 2: VOICE HANDLER =================
import asyncio
from functools import partial

def transcribe_audio(file_path):
    result = model.transcribe(file_path)
    return result

def process_voice_file_partial(file_path):
    import os
    import subprocess

    # ✅ Safe path conversion
    wav_file = os.path.splitext(file_path)[0] + ".wav"

    print(f"[DEBUG] Converting: {file_path} → {wav_file}")

    # 🔥 Run ffmpeg with error check
    subprocess.run(
        ["ffmpeg", "-y", "-i", file_path, wav_file],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("[DEBUG] Conversion done")

    # 🔥 Transcribe
    result = model.transcribe(wav_file)
    text = result["text"]

    print("[DEBUG] Transcribed text:", text)

    # 🔥 Extract items
    items = extract_items(text)

    print("[DEBUG] Extracted items:", items)

    return {
        "text": text,
        "items": items
    }
# ================= ITEM EXTRACTION =================
def extract_items(text):
    text = text.lower()

    # 🔢 words → digits
    number_map = {
        "one": "1", "two": "2", "three": "3",
        "four": "4", "five": "5", "six": "6",
        "seven": "7", "eight": "8", "nine": "9", "ten": "10"
    }

    for word, digit in number_map.items():
        text = re.sub(rf"\b{word}\b", digit, text)

    # 🔥 normalize
    replacements = {
        r"(apple.*(shimla|simla|shima|simula))": "apple shimla",
        r"\bapple\b": "apple shimla",
        r"(milk|milc|mulk)": "Aavin Premium Full Cream Fresh Milk",
        r"(bread|bred|brad)": "white bread",
        r"(egg|eggs|eg)": "eggs",
        r"(banana|bananna|banan)": "banana",
        r"(tomato|tamato|tomoto)": "tomato",
        r"(onion|onoin|onin)": "onion",
        r"(potato|poteto|aloo|poeteto|poatato)": "potato",
        r"(rice|raice|rais)": "rice"
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    # 🧹 cleanup
    text = re.sub(r"(order|buy|get|me|please)", "", text)

    # 🔥 KEY FIX: tokenize instead of greedy regex
    tokens = text.split()

    items = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token.isdigit():
            qty = int(token)

            # next word(s) form item name
            name_parts = []
            i += 1

            while i < len(tokens) and not tokens[i].isdigit():
                name_parts.append(tokens[i])
                i += 1

            name = " ".join(name_parts).strip()

            if name:
                items.append({
                    "name": name.title(),
                    "qty": qty
                })

        else:
            i += 1

    # 🛟 fallback
    if not items:
        items.append({
            "name": text.strip().title(),
            "qty": 1
        })

    return items

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import asyncio

    user_id = update.message.chat_id

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    # 📁 Save audio
    os.makedirs("audio", exist_ok=True)
    ogg_file = f"audio/{user_id}.ogg"

    await file.download_to_drive(ogg_file)

    await update.message.reply_text("🎤 Voice received. Understanding your order...")

    try:
        # 🔥 Only transcribe + extract (NOT full automation)
        result = await asyncio.to_thread(process_voice_file_partial, ogg_file)

        text = result["text"]
        items = result["items"]

        items_text = "\n".join([f"{i['name']} x{i['qty']}" for i in items])

        # 🧠 Store for confirmation
        user_data_store[user_id] = {
            "items": items,
            "audio": ogg_file
        }

        # 📩 Ask confirmation
        await update.message.reply_text(
            f"🧠 You said:\n{text}\n\n"
            f"🛒 Items:\n{items_text}\n\n"
            f"Reply YES to place order or NO to cancel"
        )

    except Exception as e:
        print("Error:", e)
        await update.message.reply_text("Failed to process voice.")

import json
from datetime import datetime

def save_order(data):
    os.makedirs("data", exist_ok=True)

    file_path = "data/orders.json"

    try:
        with open(file_path, "r") as f:
            orders = json.load(f)
    except:
        orders = []

    orders.append(data)

    with open(file_path, "w") as f:
        json.dump(orders, f, indent=2)

# ================= STEP 3: QUANTITY =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text.strip().lower()

    data = user_data_store.get(user_id)

    if not data:
        await update.message.reply_text("No active order. Send voice message.")
        return

    # ✅ CONFIRMATION
    if text in ["yes", "y", "ok", "confirm"]:
        await update.message.reply_text("Placing your order...")

        try:
            items = data["items"]

            await update.message.reply_text("Sending order to automation...")

            payload = {
                "items": items,
                "chat_id": user_id
            }

            # ✅ FIX: store response
            response = requests.post(
                "https://ended-mortally-ipod.ngrok-free.dev/webhook/order-grocery",
                json=payload
            )

            print("n8n response:", response.text)

            print("n8n response:", response.text)

            # ✅ Better handling
            if response.status_code == 200:
                await update.message.reply_text("Order sent successfully!")
                await update.message.reply_text("Processing your order... You will receive updates shortly.")
            else:
                await update.message.reply_text(f"Automation failed ({response.status_code})")

        except Exception as e:
            print("Error:", e)
            await update.message.reply_text("Failed to send order to automation.")

        finally:
            user_data_store.pop(user_id, None)

    # ❌ CANCEL
    elif text in ["no", "n", "cancel"]:
        user_data_store.pop(user_id, None)
        await update.message.reply_text("Order cancelled.")

    else:
        await update.message.reply_text("Reply YES to confirm or NO to cancel.")
    
    

# ================= QUANTITY EXTRACTION =================
def extract_quantity(text):
    match = re.search(r"\d+", text)
    return int(match.group()) if match else 1

# ================= MAIN =================

import asyncio
import pytz
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

def main():
    import asyncio
    from pytz import utc   # 👈 add this

    asyncio.set_event_loop(asyncio.new_event_loop())

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

import subprocess
import asyncio
from functools import partial

def process_voice_file(file_path):

    wav_file = file_path.replace(".ogg", ".wav")

    # Convert to wav
    subprocess.run(["ffmpeg", "-y", "-i", file_path, wav_file])

    # Transcribe
    result = model.transcribe(wav_file)
    text = result["text"]

    items = extract_items(text)

    # Run automation
    total, screenshot = run_zepto(items, "streamlit_user")
    print("Saving order now...")
    # ======== Saves order after successfully placed
    # save_order({
    #     "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    #     "items": items,
    #     "total": total,
    #     "screenshot": screenshot
    # }) 
        
    return {
        "text": text,
        "items": items,
        "total": total,
        "screenshot": screenshot
    }

if __name__ == "__main__":
    print("Starting Telegram bot...")
    main()