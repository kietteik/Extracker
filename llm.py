import os
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_expense_info(text: str) -> dict:
    """Extract expense information from natural language text using OpenAI."""
    
    system_prompt = """
    Bạn là một trợ lý phân tích chi tiêu. Nhiệm vụ của bạn là trích xuất thông tin chi tiêu từ văn bản tiếng Việt.
    Hãy trả về kết quả theo định dạng JSON với các trường:
    - amount: số tiền (float)
    - description: mô tả chi tiêu
    - category: phân loại chi tiêu (food, transport, shopping, entertainment, bills, other)
    
    Nếu không thể xác định được thông tin, trả về None cho trường tương ứng.
    """
    
    user_prompt = f"Phân tích thông tin chi tiêu từ văn bản sau: {text}"
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        return result
    except:
        return {
            "amount": None,
            "description": None,
            "category": "other"
        } 