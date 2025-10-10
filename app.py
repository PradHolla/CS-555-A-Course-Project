from flask import Flask, render_template, request, redirect, url_for
import os

from extensions import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from models import Expense  # noqa: E402

@app.route('/')
def home():
    return render_template('home/index.html', page_id='home')

@app.route('/expense-splitter', methods=['GET', 'POST'])
def expense_splitter():
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        amount_raw = request.form.get('amount', '').strip()
        payer = request.form.get('payer', '').strip()
        participants = request.form.get('participants', '').strip()

        try:
            amount = float(amount_raw)
        except ValueError:
            amount = None

        if description and amount is not None and payer:
            expense = Expense(
                description=description,
                amount=amount,
                payer=payer,
                participants=participants or None
            )
            db.session.add(expense)
            db.session.commit()

        return redirect(url_for('expense_splitter'))

    expenses = Expense.query.order_by(Expense.created_at.desc()).all()
    expense_views = []
    for expense in expenses:
        people = [p.strip() for p in (expense.participants or '').split(',') if p.strip()]
        share = expense.amount / len(people) if people else None
        expense_views.append({
            'model': expense,
            'participants': people,
            'share': share
        })

    return render_template(
        'apps/expense_splitter/index.html',
        page_id='expense-splitter',
        expenses=expense_views
    )

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    if not os.path.exists('app.db'):
        init_db()
    app.run(debug=True)
