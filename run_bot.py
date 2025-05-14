from telegram.ext import ApplicationBuilder
import os
from dotenv import load_dotenv
from bot import setup_bot

load_dotenv()

def main():
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    setup_bot(application)
    
    # Set webhook
    webhook_url = os.getenv('WEBHOOK_URL', 'https://extracker-04hz.onrender.com/webhook')
    port = int(os.getenv('PORT', 8443))
    
    application.run_webhook(
        listen='0.0.0.0',
        port=port,
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main() 