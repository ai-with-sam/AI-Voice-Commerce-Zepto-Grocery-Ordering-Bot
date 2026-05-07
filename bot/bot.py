import os
import whisper
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from datetime import datetime

BOT_TOKEN = "8710932649:AAF-ctiM6z9akdspWFr3dXi7hlefSB1HjvU"

model = whisper.load_model("base")


# 🎯 Extract item from voice text
def extract_item(text):
    return text.replace("order", "").replace("buy", "").strip()


# 🛒 Your Playwright function (modified)
async def order_item(item):
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="zepto_user_data",
            headless=False,
            args=["--window-size=1920,1080"],
            viewport=None
        )

        page = browser.new_page()
        page.goto("https://www.zepto.com/")

        page.wait_for_timeout(3000)

        # Search
        page.get_by_test_id("searchBar").click()
        search_box = page.locator("input[placeholder*='Search']").first
        search_box.fill(item)
        search_box.press("Enter")

        page.wait_for_timeout(3000)

        # Add item
        add_button = page.locator(f'(//div/img[@title="{item}"]//following-sibling::button[.="ADD"])[1]')
        add_button.click()

        # Cart
        page.locator("//button[@data-testid='cart-btn']").click()

        # Payment flow
        page.locator("//button//span[contains(text(), 'Click to Pay')]").click()
        page.locator("//div//article[contains(text(), 'UPI')]").click()
        page.locator("//div//article[contains(text(), 'QR Code')]").click()

        page.wait_for_timeout(3000)

        # Screenshot QR
        file_name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=file_name)

        return file_name


# 🎤 Handle voice messages
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()

    audio_path = "voice.ogg"
    await file.download_to_drive(audio_path)

    # Convert to wav (needed for whisper)
    os.system(f"ffmpeg -i {audio_path} voice.wav -y")

    # Transcribe
    result = model.transcribe("voice.wav")
    text = result["text"]

    print("User said:", text)

    item = extract_item(text)

    await update.message.reply_text(f"🛒 Ordering: {item}")

    # Run automation
    screenshot = order_item(item)

    # Send QR
    await update.message.reply_photo(photo=open(screenshot, "rb"))


# 🚀 Run bot
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.VOICE, handle_voice))

print("Bot started...")
app.run_polling()