import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import matplotlib.pyplot as plt
from io import BytesIO
import re

from database import Database
from llm import analyze_message, MessageIntent, format_expense_message, format_amount

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize database
db = Database()

def is_similar_to_command(text: str) -> tuple[bool, str]:
    """Check if text is similar to a known command."""
    commands = {
        "report": r"^/rep[oóòỏõọôồốổỗộơớờởỡợ]?[rt]t?$",
        "stats": r"^/st[aáàảãạăắằẳẵặâấầẩẫậ]?ts?$",
        "help": r"^/h[eéèẻẽẹ]?lp?$",
        "start": r"^/st[aáàảãạăắằẳẵặâấầẩẫậ]?[rt]t?$"
    }
    
    for cmd, pattern in commands.items():
        if re.match(pattern, text.lower()):
            if text.lower() == f"/{cmd}":
                return False, cmd  # Exact match
            return True, cmd  # Similar match
    return False, ""

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages using LLM for intent analysis."""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Check if this is a misspelled command first
    is_misspelled, actual_command = is_similar_to_command(text)
    if is_misspelled:
        await update.message.reply_text(
            f"❌ Lệnh không hợp lệ. Có phải bạn muốn dùng lệnh /{actual_command}?\n"
            f"Gõ /help để xem danh sách lệnh và hướng dẫn sử dụng."
        )
        return
    
    # Get the most recent expense for context
    recent_expense = None
    intent, data = analyze_message(text)
    
    if intent == MessageIntent.GREETING:
        message = "👋 Chào bạn! Tôi là bot quản lý chi tiêu."
        if data.get("should_show_help", False):
            message += "\nBạn có thể ghi nhận chi tiêu bằng cách nhắn tin trực tiếp với tôi.\n"
            message += "Ví dụ: 'Ăn phở 50k' hoặc 'Mua sách 200 nghìn'\n"
            message += "Gõ /help để xem hướng dẫn chi tiết."
        await update.message.reply_text(message)
        return
    
    elif intent == MessageIntent.QUESTION:
        topic = data.get("topic", "other")
        if topic == "expenses":
            message = "💡 Để ghi nhận chi tiêu, bạn chỉ cần nhắn tin với số tiền, ví dụ:\n"
            message += "- Ăn phở 50k\n"
            message += "- Mua sách 200 nghìn\n"
            message += "- Đổ xăng 100k"
        elif topic == "commands":
            message = "📝 Các lệnh có sẵn:\n"
            message += "/help - Xem hướng dẫn sử dụng\n"
            message += "/report - Xem báo cáo chi tiêu\n"
            message += "/stats - Xem thống kê chi tiêu theo danh mục"
        elif topic == "categories":
            message = "🏷️ Các danh mục chi tiêu:\n"
            message += "- 🍜 Ăn uống (food)\n"
            message += "- 🚗 Di chuyển (transport)\n"
            message += "- 🛍️ Mua sắm (shopping)\n"
            message += "- 🎮 Giải trí (entertainment)\n"
            message += "- 📱 Hóa đơn (bills)\n"
            message += "- 🏥 Y tế (health)\n"
            message += "- 📚 Giáo dục (education)\n"
            message += "- 📦 Khác (other)"
        else:
            message = "❓ Bạn cần giúp đỡ? Hãy thử các lệnh sau:\n"
            message += "/help - Xem hướng dẫn sử dụng\n"
            message += "/report - Xem báo cáo chi tiêu\n"
            message += "/stats - Xem thống kê chi tiêu theo danh mục"
        
        if data.get("should_show_help", False):
            message += "\n\nGõ /help để xem hướng dẫn chi tiết hơn."
        
        await update.message.reply_text(message)
        return
    
    elif intent == MessageIntent.EDIT_EXPENSE:
        recent_expense = db.get_latest_expense(user_id)
        if not recent_expense:
            await update.message.reply_text(
                "❌ Không tìm thấy chi tiêu nào để chỉnh sửa.\n"
                "Hãy ghi nhận một chi tiêu mới trước khi chỉnh sửa."
            )
            return
        
        if data.get("needs_clarification", False):
            await update.message.reply_text(data["clarification_question"])
            return
        
        # Update the expense
        changes = []
        if data["amount"] is not None and data["amount"] != recent_expense.amount:
            changes.append(f"💰 Số tiền: {format_amount(recent_expense.amount)}đ ➡️ {format_amount(data['amount'])}đ")
            recent_expense.amount = data["amount"]
            
        if data["description"] is not None and data["description"] != recent_expense.description:
            changes.append(f"📝 Mô tả: {recent_expense.description} ➡️ {data['description']}")
            recent_expense.description = data["description"]
            
        if data["category"] is not None and data["category"] != recent_expense.category:
            changes.append(f"🏷️ Danh mục: {recent_expense.category} ➡️ {data['category']}")
            recent_expense.category = data["category"]
        
        recent_expense.raw_text = text
        db.session.commit()
        
        # Send confirmation with changes
        if changes:
            confirmation = "✅ Đã cập nhật chi tiêu:\n" + "\n".join(changes)
            if data.get("confidence", 1.0) < 0.7:
                confirmation += "\n\n❓ Nếu thông tin trên không chính xác, bạn có thể chỉnh sửa lại."
            await update.message.reply_text(confirmation)
        else:
            await update.message.reply_text("❓ Không có thông tin nào được thay đổi.")
    
    elif intent == MessageIntent.ADD_EXPENSE:
        if data.get("needs_clarification", False):
            await update.message.reply_text(data["clarification_question"])
            return
            
        if data["amount"] is None:
            await update.message.reply_text(
                "❌ Không thể hiểu số tiền chi tiêu. Vui lòng thử lại với cú pháp:\n"
                "- [Mô tả] [Số tiền]\n"
                "Ví dụ:\n"
                "- Ăn phở 50k\n"
                "- Mua sách 200 nghìn\n"
                "- Đổ xăng 100k"
            )
            return
        
        # Save to database
        expense = db.add_expense(
            user_id=user_id,
            amount=data["amount"],
            description=data["description"],
            category=data["category"],
            raw_text=text
        )
        
        # Send confirmation
        await update.message.reply_text(format_expense_message(data))
    
    elif intent == MessageIntent.UNCLEAR:
        if data.get("clarification_question"):
            message = data["clarification_question"]
        else:
            message = "Xin lỗi bạn, mình chưa hiểu rõ ý bạn lắm. Bạn có thể nói rõ hơn được không?"
        await update.message.reply_text(message)
        return
    
    else:  # ADD_EXPENSE intent but no amount
        await update.message.reply_text(
            "❌ Không thể hiểu số tiền chi tiêu. Vui lòng thử lại với cú pháp:\n"
            "- [Mô tả] [Số tiền]\n"
            "Ví dụ:\n"
            "- Ăn phở 50k\n"
            "- Mua sách 200 nghìn\n"
            "- Đổ xăng 100k"
        )

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