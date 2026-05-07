from telegram.ext import Application, MessageHandler, filters
from ai.speech_to_text import convert_voice_to_text
from ai.intent_parser import parse_order
from automation.zepto_bot import order_items
from utils.state_manager import save_order, get_order

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"


async def handle_voice(update, context):
    user_id = update.message.from_user.id

    # Download voice
    voice = await update.message.voice.get_file()
    await voice.download_to_drive("voice.ogg")

    await update.message.reply_text("Processing voice...")

    # Speech → Text
    text = convert_voice_to_text("voice.ogg")
    await update.message.reply_text(f"You said: {text}")

    # Intent
    items = parse_order(text)

    if not items:
        await update.message.reply_text("No items found.")
        return

    save_order(user_id, items)

    await update.message.reply_text(
        f"Items detected: {items}\nReply YES to confirm order."
    )


async def handle_text(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.lower()

    if text == "yes":
        items = get_order(user_id)

        if not items:
            await update.message.reply_text("No pending order.")
            return

        await update.message.reply_text("Placing order...")

        summary = order_items(items)

        await update.message.reply_text("Order placed (Cart Ready)")
        await update.message.reply_text(summary[:1000])  # limit text

    else:
        await update.message.reply_text("Send voice to order.")


def start_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))

    print("Bot started...")
    app.run_polling()