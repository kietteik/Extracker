import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import matplotlib.pyplot as plt
from io import BytesIO

from database import Database
from llm import extract_expense_info

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize database
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = """
Xin chào! Tôi là bot quản lý chi tiêu của bạn 🤖

Các lệnh có sẵn:
/help - Xem hướng dẫn sử dụng
/report - Xem báo cáo chi tiêu
/stats - Xem thống kê chi tiêu theo danh mục

Để ghi nhận chi tiêu, bạn chỉ cần nhắn tin với tôi theo ngôn ngữ tự nhiên.
Ví dụ: "Hôm nay tôi chi 50k ăn phở"
    """
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
🤖 Hướng dẫn sử dụng bot:

1️⃣ Ghi nhận chi tiêu:
- Nhắn tin trực tiếp với bot bằng ngôn ngữ tự nhiên
- Ví dụ: "Chiều nay mua sách 200k"

2️⃣ Xem báo cáo:
/report - Xem báo cáo chi tiêu 7 ngày gần nhất
/report 30 - Xem báo cáo chi tiêu 30 ngày gần nhất

3️⃣ Xem thống kê:
/stats - Xem thống kê theo danh mục 7 ngày gần nhất
/stats 30 - Xem thống kê theo danh mục 30 ngày gần nhất

❓ Cần trợ giúp? Liên hệ admin để được hỗ trợ!
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and extract expense information."""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Extract expense information using LLM
    expense_info = extract_expense_info(text)
    
    if expense_info["amount"] is None:
        await update.message.reply_text("Xin lỗi, tôi không thể xác định được thông tin chi tiêu từ tin nhắn của bạn. 😕")
        return
    
    # Save to database
    db.add_expense(
        user_id=user_id,
        amount=expense_info["amount"],
        description=expense_info["description"],
        category=expense_info["category"],
        raw_text=text
    )
    
    reply = f"""
✅ Đã ghi nhận chi tiêu:
💰 Số tiền: {expense_info['amount']:,.0f}đ
📝 Mô tả: {expense_info['description']}
🏷️ Danh mục: {expense_info['category']}
    """
    await update.message.reply_text(reply)

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate expense report."""
    user_id = update.effective_user.id
    
    # Get number of days from command arguments
    days = 7
    if context.args and context.args[0].isdigit():
        days = int(context.args[0])
    
    start_date = datetime.now() - timedelta(days=days)
    expenses = db.get_expenses(user_id, start_date)
    
    if not expenses:
        await update.message.reply_text(f"Không có chi tiêu nào trong {days} ngày qua.")
        return
    
    total = sum(expense.amount for expense in expenses)
    report_text = f"📊 Báo cáo chi tiêu {days} ngày qua:\n\n"
    
    for expense in expenses:
        report_text += f"- {expense.date.strftime('%d/%m/%Y')}: {expense.amount:,.0f}đ - {expense.description}\n"
    
    report_text += f"\n💰 Tổng chi tiêu: {total:,.0f}đ"
    await update.message.reply_text(report_text)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate expense statistics with pie chart."""
    user_id = update.effective_user.id
    
    # Get number of days from command arguments
    days = 7
    if context.args and context.args[0].isdigit():
        days = int(context.args[0])
    
    start_date = datetime.now() - timedelta(days=days)
    stats_data = db.get_stats(user_id, start_date)
    
    if not stats_data:
        await update.message.reply_text(f"Không có chi tiêu nào trong {days} ngày qua.")
        return
    
    # Create pie chart
    plt.figure(figsize=(10, 7))
    plt.pie(stats_data.values(), labels=stats_data.keys(), autopct='%1.1f%%')
    plt.title(f'Thống kê chi tiêu theo danh mục ({days} ngày qua)')
    
    # Save plot to buffer
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    # Send statistics and plot
    total = sum(stats_data.values())
    stats_text = f"📊 Thống kê chi tiêu {days} ngày qua:\n\n"
    for category, amount in stats_data.items():
        stats_text += f"- {category}: {amount:,.0f}đ ({amount/total*100:.1f}%)\n"
    stats_text += f"\n💰 Tổng chi tiêu: {total:,.0f}đ"
    
    await update.message.reply_photo(buf, caption=stats_text)

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 