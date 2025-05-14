import os
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_expense_info(text, previous_expense=None):
    """
    Extracts expense information from natural language text.
    If previous_expense is provided, it will be used as context for editing.
    """
    system_prompt = """Bạn là trợ lý phân tích chi tiêu. Nhiệm vụ của bạn là trích xuất thông tin chi tiêu từ văn bản tiếng Việt và trả về dưới dạng JSON.
    
Quy tắc xử lý số tiền:
- Nếu có "k" hoặc "K" (nghìn): nhân với 1000
- Nếu có "tr" hoặc "triệu": nhân với 1000000
- Mặc định đơn vị là VNĐ
- Làm tròn số tiền đến hàng nghìn
- Với yêu cầu chỉnh sửa, nếu không có số tiền mới thì giữ nguyên số tiền cũ

Quy tắc xử lý mô tả:
- Giữ nguyên mô tả gốc nếu không có thông tin mô tả mới
- Với yêu cầu chỉnh sửa chỉ có số tiền (VD: "sửa thành 45k"), giữ nguyên mô tả cũ
- Cập nhật mô tả mới nếu có thông tin mới rõ ràng

Danh mục chi tiêu:
- food: ăn uống, đồ ăn, thức ăn, cafe, trà sữa, nhà hàng, ăn sáng, ăn trưa, ăn tối
- transport: di chuyển, xăng, grab, taxi, xe bus, gửi xe, đổ xăng, xe ôm, giao thông
- shopping: mua sắm, quần áo, giày dép, phụ kiện, đồ dùng, mỹ phẩm
- entertainment: giải trí, xem phim, du lịch, game, vui chơi, thể thao
- bills: hóa đơn, điện, nước, internet, điện thoại, tiền nhà, gas
- health: khám bệnh, thuốc, bảo hiểm, y tế
- education: học phí, sách vở, khóa học
- other: các khoản khác

Trả về kết quả theo định dạng JSON:
{
    "amount": <số tiền>,
    "description": "<mô tả>",
    "category": "<danh mục>"
}"""

    if previous_expense:
        user_prompt = f"""Chi tiêu hiện tại:
- Số tiền: {previous_expense['amount']}đ
- Mô tả: {previous_expense['description']}
- Danh mục: {previous_expense['category']}

Yêu cầu chỉnh sửa: {text}

Hãy phân tích và trả về thông tin chi tiêu sau khi chỉnh sửa theo định dạng JSON.
Lưu ý:
- Nếu chỉ sửa số tiền, giữ nguyên mô tả và danh mục
- Nếu chỉ sửa mô tả, giữ nguyên số tiền
- Tự động phân loại lại danh mục nếu mô tả mới thuộc danh mục khác"""
    else:
        user_prompt = f"Hãy phân tích chi tiêu sau và trả về kết quả theo định dạng JSON: {text}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Lower temperature for more consistent results
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate and clean up results
        if previous_expense:
            # Keep previous values if new ones are not provided
            if result["amount"] is None:
                result["amount"] = previous_expense["amount"]
            if not result["description"] or result["description"] == text:
                result["description"] = previous_expense["description"]
            if not result["category"]:
                result["category"] = previous_expense["category"]
                
        return result
    except Exception as e:
        print(f"Error extracting expense info: {e}")
        if previous_expense:
            return previous_expense
        return {
            "amount": None,
            "description": text,
            "category": "other"
        }

def format_expense_message(expense_info, is_edit=False):
    """Formats expense information into a user-friendly message."""
    action = "Đã ghi nhận lại" if is_edit else "Đã ghi nhận"
    return f"""✅ {action} chi tiêu:
💰 Số tiền: {format_amount(expense_info['amount'])}đ
📝 Mô tả: {expense_info['description']}
🏷️ Danh mục: {expense_info['category']}"""

def format_amount(amount):
    """Formats amount with thousand separators."""
    return "{:,.0f}".format(amount) if amount else "0" 