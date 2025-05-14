# Telegram Expense Tracker Bot

Bot Telegram giúp quản lý chi tiêu cá nhân sử dụng xử lý ngôn ngữ tự nhiên.

## Tính năng

- Ghi nhận chi tiêu qua tin nhắn ngôn ngữ tự nhiên
- Tự động phân loại chi tiêu sử dụng LLM
- Xuất báo cáo và thống kê chi tiêu
- Lưu trữ dữ liệu trong SQLite database

## Yêu cầu

- Python 3.10 hoặc cao hơn
- Poetry (công cụ quản lý dependencies)

## Cài đặt

1. Clone repository
2. Cài đặt Poetry (nếu chưa có):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Cài đặt dependencies:
```bash
poetry install
```

4. Tạo file `.env` với các thông tin:
```
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_api_key
```

## Sử dụng

1. Kích hoạt môi trường ảo và chạy bot:
```bash
poetry shell
python bot.py
```

2. Hoặc chạy trực tiếp không cần kích hoạt môi trường:
```bash
poetry run python bot.py
```

3. Bắt đầu chat với bot trên Telegram:
- Gửi chi tiêu: "Hôm nay tôi chi 50k ăn phở"
- Xem báo cáo: /report
- Xem thống kê: /stats
- Trợ giúp: /help # Extracker
