import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import matplotlib.pyplot as plt
from io import BytesIO

from database import Database
from llm import extract_expense_info, format_expense_message, format_amount

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize database
db = Database()

def is_edit_message(text: str) -> bool:
    """Check if the message is trying to edit the last expense."""
    edit_prefixes = [
        'sửa', 'chỉnh', 'đổi', 'sửa thành', 'chỉnh lại', 'đổi thành',
        'sửa lại', 'chỉnh thành', 'đổi lại', 'update', 'cập nhật',
        'thay đổi', 'thay thành'
    ]
    edit_keywords = ['thành', 'lại', 'còn']
    
    text_lower = text.lower()
    # Check for exact prefixes
    if any(text_lower.startswith(prefix) for prefix in edit_prefixes):
        return True
    # Check for edit keywords in the first few words
    first_words = text_lower.split()[:3]
    return any(keyword in first_words for keyword in edit_keywords)

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

Để chỉnh sửa chi tiêu gần nhất, bạn có thể:
- "sửa thành 40k"
- "chỉnh lại thành cà phê sữa 45 nghìn"
- "đổi thành trà sữa 35k"
    """
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
🤖 Hướng dẫn sử dụng bot:

1️⃣ Ghi nhận chi tiêu:
- Nhắn tin trực tiếp với bot bằng ngôn ngữ tự nhiên
- Ví dụ: "Chiều nay mua sách 200k"
- Ví dụ: "Ăn phở bò 45 nghìn"

2️⃣ Chỉnh sửa chi tiêu:
- Để sửa chi tiêu gần nhất, bạn có thể:
  • Sửa số tiền: "sửa thành 40k"
  • Sửa mô tả: "đổi thành cà phê sữa"
  • Sửa cả hai: "chỉnh lại thành trà sữa 35k"
- Bot hiểu nhiều cách diễn đạt khác nhau:
  • "sửa thành...", "đổi thành...", "chỉnh lại..."
  • "cập nhật thành...", "thay đổi thành..."

3️⃣ Xem báo cáo:
/report - Xem báo cáo chi tiêu 7 ngày gần nhất
/report 30 - Xem báo cáo chi tiêu 30 ngày gần nhất

4️⃣ Xem thống kê:
/stats - Xem thống kê theo danh mục 7 ngày gần nhất
/stats 30 - Xem thống kê theo danh mục 30 ngày gần nhất

5️⃣ Danh mục chi tiêu:
- 🍜 Ăn uống (food)
- 🚗 Di chuyển (transport)
- 🛍️ Mua sắm (shopping)
- 🎮 Giải trí (entertainment)
- 📱 Hóa đơn (bills)
- 🏥 Y tế (health)
- 📚 Giáo dục (education)
- 📦 Khác (other)

❓ Cần trợ giúp? Liên hệ admin để được hỗ trợ!
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and extract expense information."""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Check if this is an edit message
    if is_edit_message(text):
        # Get the most recent expense
        recent_expense = db.get_latest_expense(user_id)
        if not recent_expense:
            await update.message.reply_text(
                "❌ Không tìm thấy chi tiêu nào để chỉnh sửa.\n"
                "Hãy ghi nhận một chi tiêu mới trước khi chỉnh sửa."
            )
            return
        
        # Extract new info with context
        current_expense = {
            "amount": recent_expense.amount,
            "description": recent_expense.description,
            "category": recent_expense.category
        }
        expense_info = extract_expense_info(text, current_expense)
        
        if expense_info["amount"] is None and expense_info["description"] == text:
            await update.message.reply_text(
                "❌ Không thể hiểu yêu cầu chỉnh sửa. Vui lòng thử lại với cú pháp:\n"
                "- sửa thành [số tiền mới]\n"
                "- đổi thành [mô tả mới] [số tiền]\n"
                "Ví dụ: sửa thành 45k"
            )
            return
        
        # Show preview of changes
        changes = []
        if expense_info["amount"] != recent_expense.amount:
            changes.append(f"💰 Số tiền: {format_amount(recent_expense.amount)}đ ➡️ {format_amount(expense_info['amount'])}đ")
        if expense_info["description"] != recent_expense.description:
            changes.append(f"📝 Mô tả: {recent_expense.description} ➡️ {expense_info['description']}")
        if expense_info["category"] != recent_expense.category:
            changes.append(f"🏷️ Danh mục: {recent_expense.category} ➡️ {expense_info['category']}")
        
        # Update the expense
        recent_expense.amount = expense_info["amount"] if expense_info["amount"] is not None else recent_expense.amount
        recent_expense.description = expense_info["description"] if expense_info["description"] != text else recent_expense.description
        recent_expense.category = expense_info["category"]
        recent_expense.raw_text = text
        db.session.commit()
        
        # Send confirmation with changes
        confirmation = "✅ Đã cập nhật chi tiêu:\n" + "\n".join(changes)
        await update.message.reply_text(confirmation)
    
    else:
        # Handle new expense
        expense_info = extract_expense_info(text)
        
        if expense_info["amount"] is None:
            await update.message.reply_text("❌ Không thể hiểu thông tin chi tiêu. Vui lòng thử lại.")
            return
        
        # Save to database
        db.add_expense(
            user_id=user_id,
            amount=expense_info["amount"],
            description=expense_info["description"],
            category=expense_info["category"],
            raw_text=text
        )
        
        # Send confirmation
        await update.message.reply_text(format_expense_message(expense_info))

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

def setup_bot(application: Application):
    """Setup bot handlers."""
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return application

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    setup_bot(application)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 