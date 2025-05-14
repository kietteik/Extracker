from telegram.ext import ApplicationBuilder
import os
from dotenv import load_dotenv
from bot import setup_bot

load_dotenv()

if __name__ == "__main__":
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    setup_bot(application)
    application.run_polling(allowed_updates=["message", "callback_query"]) 