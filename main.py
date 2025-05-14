import multiprocessing
import uvicorn
from telegram.ext import ApplicationBuilder
import os
from dotenv import load_dotenv
from web import app
from bot import setup_bot

load_dotenv()

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

def run_telegram_bot():
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    setup_bot(application)
    application.run_polling(allowed_updates=["message", "callback_query"])

def main():
    # Create processes
    web_process = multiprocessing.Process(target=run_web)
    bot_process = multiprocessing.Process(target=run_telegram_bot)

    # Start processes
    web_process.start()
    bot_process.start()

    try:
        # Wait for processes to complete
        web_process.join()
        bot_process.join()
    except KeyboardInterrupt:
        # Handle graceful shutdown
        web_process.terminate()
        bot_process.terminate()
        web_process.join()
        bot_process.join()

if __name__ == "__main__":
    main() 