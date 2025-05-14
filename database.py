from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Expense(Base):
    __tablename__ = 'expenses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Float)
    description = Column(Text)
    category = Column(String(100))
    date = Column(DateTime, default=datetime.now)
    raw_text = Column(Text)

class Database:
    def __init__(self):
        self.engine = create_engine('sqlite:///expenses.db')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_expense(self, user_id: int, amount: float, description: str, category: str, raw_text: str):
        expense = Expense(
            user_id=user_id,
            amount=amount,
            description=description,
            category=category,
            raw_text=raw_text
        )
        self.session.add(expense)
        self.session.commit()
        return expense
    
    def get_expenses(self, user_id: int, start_date: datetime = None, end_date: datetime = None):
        query = self.session.query(Expense).filter(Expense.user_id == user_id)
        if start_date:
            query = query.filter(Expense.date >= start_date)
        if end_date:
            query = query.filter(Expense.date <= end_date)
        return query.all()
    
    def get_stats(self, user_id: int, start_date: datetime = None, end_date: datetime = None):
        expenses = self.get_expenses(user_id, start_date, end_date)
        stats = {}
        for expense in expenses:
            if expense.category not in stats:
                stats[expense.category] = 0
            stats[expense.category] += expense.amount
        return stats 