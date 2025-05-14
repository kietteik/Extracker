import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from enum import Enum

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class MessageIntent(Enum):
    ADD_EXPENSE = "add_expense"
    EDIT_EXPENSE = "edit_expense"
    GREETING = "greeting"
    QUESTION = "question"
    UNCLEAR = "unclear"

def analyze_message(text: str, previous_expense=None):
    """
    Analyze message intent and extract relevant information using LLM.
    Returns a tuple of (intent, data).
    """
    system_prompt = """Bạn là trợ lý phân tích tin nhắn cho bot quản lý chi tiêu. 
Nhiệm vụ của bạn là phân tích ý định và nội dung tin nhắn của người dùng.

Các loại tin nhắn có thể có:
1. Ghi nhận chi tiêu mới (add_expense)
2. Chỉnh sửa chi tiêu (edit_expense)
3. Lời chào hoặc xã giao (greeting)
4. Câu hỏi hoặc cần trợ giúp (question)
5. Không rõ ý định (unclear)

Với mỗi loại tin nhắn, hãy trả về thông tin phù hợp theo định dạng JSON:

1. Ghi nhận chi tiêu:
{
    "intent": "add_expense",
    "data": {
        "amount": số tiền (hoặc null nếu không xác định được),
        "description": "mô tả chi tiêu",
        "category": "danh mục",
        "confidence": 0.0 đến 1.0,
        "needs_clarification": true/false,
        "clarification_question": "câu hỏi làm rõ (nếu cần)"
    }
}

2. Chỉnh sửa chi tiêu:
{
    "intent": "edit_expense",
    "data": {
        "amount": số tiền mới (hoặc null nếu giữ nguyên),
        "description": "mô tả mới (hoặc null nếu giữ nguyên)",
        "category": "danh mục mới (hoặc null nếu giữ nguyên)",
        "confidence": 0.0 đến 1.0,
        "needs_clarification": true/false,
        "clarification_question": "câu hỏi làm rõ (nếu cần)"
    }
}

3. Lời chào:
{
    "intent": "greeting",
    "data": {
        "should_show_help": true/false
    }
}

4. Câu hỏi:
{
    "intent": "question",
    "data": {
        "topic": "chủ đề câu hỏi (expenses/commands/categories/other)",
        "should_show_help": true/false
    }
}

5. Không rõ ý định:
{
    "intent": "unclear",
    "data": {
        "possible_intents": ["danh sách các ý định có thể"],
        "clarification_question": "câu hỏi làm rõ theo ngữ cảnh"
    }
}

Quy tắc xử lý:
1. Số tiền:
   - Hỗ trợ đơn vị: k, nghìn, ngàn, triệu, tr, đồng, vnd, $
   - Tự động nhân với 1000 cho 'k' hoặc 'nghìn'
   - Tự động nhân với 1000000 cho 'tr' hoặc 'triệu'
   - Làm tròn đến hàng nghìn

2. Danh mục:
   - food: ăn uống, đồ ăn, thức ăn, cafe, trà sữa, nhà hàng
   - transport: di chuyển, xăng, grab, taxi, xe bus, gửi xe
   - shopping: mua sắm, quần áo, giày dép, phụ kiện
   - entertainment: giải trí, xem phim, du lịch, game
   - bills: hóa đơn, điện, nước, internet, điện thoại
   - health: khám bệnh, thuốc, bảo hiểm, y tế
   - education: học phí, sách vở, khóa học
   - other: các khoản khác

3. Độ tin cậy (confidence):
   - 1.0: Chắc chắn về thông tin
   - 0.7-0.9: Khá chắc chắn
   - 0.4-0.6: Không chắc chắn, có thể cần làm rõ
   - <0.4: Rất không chắc chắn, nên hỏi lại

4. Xử lý ngôn ngữ địa phương:
   - Linh hoạt với cách diễn đạt
   - Hiểu các từ địa phương phổ biến
   - Nếu không chắc chắn, đánh dấu needs_clarification=true

5. Khi không rõ ý định:
   - Trả về câu hỏi làm rõ một cách tự nhiên và thân thiện
   - Ví dụ:
     + "Xin lỗi bạn, mình chưa hiểu rõ ý bạn lắm. Bạn muốn ghi chi tiêu mới hay chỉnh sửa chi tiêu cũ vậy?"
     + "Bạn ơi, bạn đang muốn ghi chi tiêu hay đang có câu hỏi gì vậy?"
     + "Mình thấy tin nhắn hơi khó hiểu. Bạn có thể nói rõ hơn được không?"
   - Tránh liệt kê các intent một cách máy móc
   - Luôn giữ giọng điệu thân thiện và lịch sự"""

    user_prompt = f"Tin nhắn của người dùng: {text}"
    if previous_expense:
        user_prompt += f"\n\nChi tiêu hiện tại đang được chỉnh sửa:\n- Số tiền: {previous_expense['amount']}đ\n- Mô tả: {previous_expense['description']}\n- Danh mục: {previous_expense['category']}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        result = json.loads(response.choices[0].message.content)
        return MessageIntent(result["intent"]), result["data"]
        
    except Exception as e:
        print(f"Error analyzing message: {e}")
        return MessageIntent.UNCLEAR, {
            "possible_intents": [],
            "clarification_question": "Xin lỗi, tôi không hiểu ý của bạn. Bạn có thể nói rõ hơn được không?"
        }

def format_expense_message(expense_info, is_edit=False):
    """Formats expense information into a user-friendly message."""
    if expense_info.get("needs_clarification"):
        return f"❓ {expense_info['clarification_question']}"
        
    action = "Đã ghi nhận lại" if is_edit else "Đã ghi nhận"
    confidence = expense_info.get("confidence", 1.0)
    
    message = f"✅ {action} chi tiêu:\n"
    message += f"💰 Số tiền: {format_amount(expense_info['amount'])}đ\n"
    message += f"📝 Mô tả: {expense_info['description']}\n"
    message += f"🏷️ Danh mục: {expense_info['category']}"
    
    if confidence < 0.7:
        message += f"\n\n❓ Nếu thông tin trên không chính xác, bạn có thể chỉnh sửa bằng cách nhắn:\n"
        message += "- sửa thành [số tiền mới]\n"
        message += "- đổi thành [mô tả mới] [số tiền]"
    
    return message

def format_amount(amount):
    """Formats amount with thousand separators."""
    return "{:,.0f}".format(amount) if amount else "0" 