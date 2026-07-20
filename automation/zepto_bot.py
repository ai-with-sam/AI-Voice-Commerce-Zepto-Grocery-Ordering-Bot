import os
import re
import whisper
import subprocess
import pytz
from datetime import datetime
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

# ================= STEP 1: START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! Send me a voice note to order food 🎤"
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

    # 🔢 Convert number words → digits
    number_map = {
        "one": "1", "two": "2", "three": "3",
        "four": "4", "five": "5", "six": "6",
        "seven": "7", "eight": "8", "nine": "9", "ten": "10"
    }

    for word, digit in number_map.items():
        text = re.sub(rf"\b{word}\b", digit, text)

    # 🔥 Normalize common speech/whisper variations
    replacements = {
        r"(apple.*(shimla|simla|shima|simula))": "apple washington",
        r"\bapple\b": "apple washington",
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

    # 🧹 Remove filler words
    text = re.sub(r"(order|buy|get|me|please)", "", text)

    items = []

    # 🔍 Case 1: "2 milk"
    matches_1 = re.findall(r"(\d+)\s*([a-zA-Z ]+)", text)

    # 🔍 Case 2: "milk 2"
    matches_2 = re.findall(r"([a-zA-Z ]+?)\s*(\d+)", text)

    used = set()

    for qty, name in matches_1:
        key = name.strip()

        if not key:   # 🚨 FIX: skip empty matches
            continue

        if key not in used:
            items.append({
                "name": key.title(),
                "qty": int(qty)
            })
            used.add(key)

    for name, qty in matches_2:
        key = name.strip()

        if not key:   # 🚨 FIX: skip empty matches
            continue

        if key not in used:
            items.append({
                "name": key.title(),
                "qty": int(qty)
            })
            used.add(key)

    # 🛟 Fallback (no quantity found)
    if not items:
        cleaned = text.strip()
        items.append({
            "name": cleaned.title(),
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
        await update.message.reply_text("❌ Failed to process voice.")

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
    import asyncio

    user_id = update.message.chat_id
    text = update.message.text.strip().lower()

    data = user_data_store.get(user_id)

    if not data:
        await update.message.reply_text("⚠️ No active order. Send voice message.")
        return

    # ✅ CONFIRMATION
    if text in ["yes", "y", "ok", "confirm"]:
        await update.message.reply_text("🛒 Placing your order...")

        try:
            items = data["items"]

            # 🔥 Run automation
            result = await asyncio.to_thread(run_zepto, items, user_id)

            total, cart_ss, total_ss, qr_ss = result

            await update.message.reply_text(f"💰 Total: {total}")

            with open(cart_ss, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption="🛒 Added Items in Cart"
                )

            with open(total_ss, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption="🧾 Total Amount to Pay"
                )

            # Send QR screenshot
            with open(qr_ss, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption="📸 Scan & Pay soon. QR is valid for 3 mins only !"
                )

            await update.message.reply_text("⏳ Waiting for payment...")

        except Exception as e:
            print("Error:", e)
            await update.message.reply_text("❌ Failed to place order.")

        finally:
            user_data_store.pop(user_id, None)

    # ❌ CANCEL
    elif text in ["no", "n", "cancel"]:
        user_data_store.pop(user_id, None)
        await update.message.reply_text("❌ Order cancelled.")

    else:
        await update.message.reply_text("⚠️ Reply YES to confirm or NO to cancel.")
    
    

# ================= QUANTITY EXTRACTION =================
def extract_quantity(text):
    match = re.search(r"\d+", text)
    return int(match.group()) if match else 1

# ================= PLAYWRIGHT AUTOMATION =================
def run_zepto(items, user_id):
        p = sync_playwright().start()
        browser = p.chromium.launch_persistent_context(
            user_data_dir="zepto_user_data",
            headless=False,
            args=["--window-size=1920,1080"],
            viewport=None
        )

        page = browser.new_page()
        page.goto("https://www.zepto.com/")

        page.wait_for_timeout(3000)
        loc_home = page.get_by_text("home", exact=True)

        # Handle location
        try:
            page.locator("text=Select Location").click(timeout=5000)
        except:
            try:
                loc_home.wait_for(timeout=5000)
                loc_home.click()
                print("Clicked Home")
            except:
                print("No location element found")

        page.wait_for_timeout(2000)

        page.locator("(//span[contains(text(),'Home')])[last()]").click()
        page.wait_for_timeout(2000)
        print("Chosen the Home Location")

        try:
            cart_badge = page.locator("//span[@data-testid='cart-items-number']")
            
            if cart_badge.is_visible(timeout=3000):
                print("Cart has existing items. Clearing cart...")
                cart_badge.click()
                while True:
                    minus_btn = page.locator("(//button[contains(@aria-label, 'Remove') and contains(@data-testid, 'minus')])[1]")
                    print(minus_btn)

                    try:
        # 👇 WAIT until button is actually visible
                        minus_btn.wait_for(state="visible", timeout=3000)

                        minus_btn.click()
                        print("Clicked minus button")

                        page.wait_for_timeout(800)  # allow UI update

                    except:
                        print("No more items OR button not visible")
                        
                        # Exit cart
                        #page.locator("//button[contains(@aria-label, 'Back Icon')]").click()
                        page.locator("//div[contains(@class, 'flex')]/button/img[contains(@alt, 'cart back')]").click()
                        break
                            
        except Exception as e:
            print("Cart check skipped:", e)

        page.get_by_test_id("searchBar").click()

        search_box = page.locator("//div/a[contains(@aria-label, 'Search')]")
        for item_data in items:
            item = item_data["name"]
            quantity = item_data["qty"]

            print(f"Adding {item} x{quantity}")

            search_box = page.locator("//div//input[contains(@placeholder, 'Search')]")
            search_box.fill(item)
            search_box.press("Enter")

            page.wait_for_timeout(3000)

            add_button = page.locator(
                f'(//div/img[contains(@title, "{item}")]//following-sibling::button[.="ADD"])[1]'
            )

            add_button.wait_for(timeout=5000)
            add_button.click()

            # 🔥 Handle quantity
            if quantity > 1:
                plus_btn = page.locator("//button[contains(@aria-label, 'Increase quantity')]").first

                for _ in range(quantity - 1):
                    try:
                        plus_btn.wait_for(state="visible", timeout=3000)
                        plus_btn.click()
                        page.wait_for_timeout(500)
                    except:
                        break

            # Small delay before next item
            page.wait_for_timeout(2000)
       # print(add_button.inner_text())

                # Cart
        cart_btn_popup = page.locator("//div[contains(text(), 'Go to Cart')]")
        if(cart_btn_popup.is_visible()):
            cart_btn_popup.click()
        else:
            cart_btn = page.locator("//button[@data-testid='cart-btn']")
    # Wait until visible + stable
            cart_btn.wait_for(state="visible", timeout=5000)
    # Small delay for UI stabilization
            page.wait_for_timeout(1000)
    # Scroll into view (important)
            cart_btn.scroll_into_view_if_needed()
    # Force click (bypass overlay issues)
            cart_btn.click(force=True)
        print("Cart Button clicked")

        page.wait_for_timeout(2000)

        #Get Items Screenshot

        cart_items = page.locator("//div/span[contains(text(), 'Delivering in')]")
        cart_items.wait_for(state="visible")
        cart_items.scroll_into_view_if_needed()

        cart_items_screenshot = f"cart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=cart_items_screenshot)

                # Get total
        total_locator = page.locator(
            "//span[contains(text(), 'Pay')]/parent::button/following-sibling::div//span[last()]"
        )

        total_locator.wait_for(state="visible")
        total_locator.scroll_into_view_if_needed()

        total_amount = total_locator.inner_text()

        total_screenshot = f"total_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=total_screenshot)

        print("Total Payable Amount:", total_amount)

                # Payment
        with page.expect_navigation():
            page.locator("//button//span[contains(text(), 'Click to Pay')]").click()

        print("Navigated to payment page:", page.url)

        # page.wait_for_load_state("networkidle")
        # page.wait_for_timeout(3000)

        #upi_option = page.locator("//div//article[contains(text(), 'UPI')]")
        upi_option = page.locator("//div//h3[contains(text(), 'UPI')]")

        upi_option.wait_for(state="visible", timeout=10000)

        # Scroll into view (VERY IMPORTANT)
        upi_option.scroll_into_view_if_needed()

        # Force click (bypass overlay issues)
        upi_option.click(force=True)

        print("Clicked UPI")

        #qr_option = page.locator("//div//article[contains(text(), 'QR Code')]")
        qr_option = page.locator("//div/span[contains(text(), 'QR Code')]")

        qr_option.wait_for(state="visible", timeout=10000)
        qr_option.scroll_into_view_if_needed()
        qr_option.click(force=True)

        print("Clicked QR Code")

        qr_image = page.locator("//div//span[contains(text(), 'TO PAY')]")
        qr_image.wait_for(state="visible", timeout=10000)
        qr_image.scroll_into_view_if_needed()

        #page.locator("//div//article[contains(text(), 'Scan QR and Pay')]").wait_for()

        # Screenshot
            # Screenshot
        qr_screenshot = f"qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=qr_screenshot)

        # file_name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        # page.screenshot(path=file_name)

        # ✅ Save order right after QR generation
        try:
            os.makedirs("data", exist_ok=True)
            file_path = "data/orders.json"

            try:
                with open(file_path, "r") as f:
                    orders = json.load(f)
            except:
                orders = []

            orders.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "items": items,
                "total": total_amount,
                "cart_screenshot": cart_items_screenshot,
                "total_screenshot": total_screenshot,
                "qr_screenshot": qr_screenshot
            })

            with open(file_path, "w") as f:
                json.dump(orders, f, indent=2)

            print("✅ Order saved successfully")

        except Exception as e:
            print("❌ Failed to save order:", e)

        print("Waiting for user to complete payment...")
        # page.wait_for_load_state("networkidle")
        # page.wait_for_timeout(2000)
        # page.wait_for_selector("text=Order placed", timeout=300000)
        # ========= print("Payment completed!") ================
        playwright_instances[user_id] = {
            "page": page,
            "browser": browser,
            "playwright": p
        }

        return total_amount, cart_items_screenshot, total_screenshot, qr_screenshot

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

if __name__ == "__main__":
    main()
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