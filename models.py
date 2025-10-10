from extensions import db
from datetime import datetime

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payer = db.Column(db.String(100), nullable=False)
    participants = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
