from fastapi import FastAPI, Request, Form, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import json
from typing import Optional
from database import Database, Expense
from llm import analyze_message, format_expense_message, MessageIntent
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from telegram import Update
from telegram.ext import Application
import os
from bot import setup_bot

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")  # Thay thế bằng secret key thực
db = Database()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Pydantic models for request validation
class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None

# Initialize Telegram bot
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
if bot_token:
    application = Application.builder().token(bot_token).build()
    setup_bot(application)

def get_current_user(request: Request) -> Optional[int]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return user_id

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user_id: Optional[int] = Depends(get_current_user)):
    if not user_id:
        return templates.TemplateResponse("login.html", {"request": request})
        
    # Get current month's stats
    start_date = datetime.now().replace(day=1)
    stats = db.get_stats(user_id=user_id, start_date=start_date)
    total_month = sum(stats.values())
    
    # Calculate average per day
    days_in_month = (datetime.now() - start_date).days + 1
    avg_per_day = total_month / days_in_month if days_in_month > 0 else 0
    
    # Get total transactions
    expenses = db.get_expenses(user_id=user_id, start_date=start_date)
    total_transactions = len(expenses)
    
    # Get all unique categories
    categories = [
        'food', 'transport', 'shopping', 'entertainment', 
        'bills', 'health', 'education', 'other'
    ]
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "user_id": user_id,
            "total_month": total_month,
            "avg_per_day": avg_per_day,
            "total_transactions": total_transactions,
            "categories": categories,
            "expenses": expenses
        }
    )

@app.post("/login")
async def login(request: Request, user_id: int = Form(...)):
    request.session["user_id"] = user_id
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/expenses")
async def get_expenses(
    request: Request,
    days: Optional[int] = 7,
    category: Optional[str] = None,
    user_id: Optional[int] = Depends(get_current_user)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    start_date = datetime.now() - timedelta(days=days)
    expenses = db.get_expenses(user_id=user_id, start_date=start_date)
    
    if category:
        expenses = [e for e in expenses if e.category == category]
    
    return [{
        "id": expense.id,
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "date": expense.date.strftime("%Y-%m-%d %H:%M:%S"),
        "raw_text": expense.raw_text
    } for expense in expenses]

@app.patch("/api/expenses/{expense_id}/field")
async def update_expense_field(
    expense_id: int,
    field_update: ExpenseUpdate,
    user_id: Optional[int] = Depends(get_current_user)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    expense = db.session.query(Expense).filter_by(id=expense_id, user_id=user_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Update only the provided fields
    if field_update.amount is not None:
        expense.amount = field_update.amount
    if field_update.description is not None:
        expense.description = field_update.description
    if field_update.category is not None:
        expense.category = field_update.category
        
    db.session.commit()
    
    return {
        "id": expense.id,
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "date": expense.date.strftime("%Y-%m-%d %H:%M:%S"),
        "raw_text": expense.raw_text
    }

@app.post("/api/expenses")
async def add_expense(
    raw_text: str = Form(...),
    user_id: Optional[int] = Depends(get_current_user)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    intent, expense_info = analyze_message(raw_text)
    if intent != MessageIntent.ADD_EXPENSE or expense_info["amount"] is None:
        raise HTTPException(status_code=400, detail="Could not extract expense information")
    
    expense = db.add_expense(
        user_id=user_id,
        amount=expense_info["amount"],
        description=expense_info["description"],
        category=expense_info["category"],
        raw_text=raw_text
    )
    
    return {
        "id": expense.id,
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "date": expense.date.strftime("%Y-%m-%d %H:%M:%S"),
        "raw_text": expense.raw_text
    }

@app.get("/api/stats")
async def get_stats(
    days: Optional[int] = 7,
    user_id: Optional[int] = Depends(get_current_user)
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    start_date = datetime.now() - timedelta(days=days)
    stats = db.get_stats(user_id=user_id, start_date=start_date)
    return stats

@app.get("/api/expenses/{expense_id}")
async def get_expense(expense_id: int):
    expense = db.session.query(Expense).filter_by(id=expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return {
        "id": expense.id,
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category,
        "date": expense.date.strftime("%Y-%m-%d %H:%M:%S"),
        "raw_text": expense.raw_text
    }

@app.put("/api/expenses/{expense_id}/edit")
async def edit_expense_with_text(
    expense_id: int,
    edit_text: str = Form(...),
):
    # Get existing expense
    expense = db.session.query(Expense).filter_by(id=expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Extract new info from text
    current_expense = {
        "amount": expense.amount,
        "description": expense.description,
        "category": expense.category
    }
    intent, expense_info = analyze_message(edit_text, current_expense)
    
    if intent != MessageIntent.EDIT_EXPENSE:
        raise HTTPException(status_code=400, detail="Invalid edit command")
    
    # Update expense
    expense.amount = expense_info["amount"] if expense_info["amount"] is not None else expense.amount
    expense.description = expense_info["description"] if expense_info["description"] is not None else expense.description
    expense.category = expense_info["category"] if expense_info["category"] is not None else expense.category
    expense.raw_text = edit_text
    db.session.commit()
    
    return {
        "message": format_expense_message(expense_info, is_edit=True),
        "expense": {
            "id": expense.id,
            "amount": expense.amount,
            "description": expense.description,
            "category": expense.category,
            "date": expense.date.strftime("%Y-%m-%d %H:%M:%S"),
            "raw_text": expense.raw_text
        }
    }

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 