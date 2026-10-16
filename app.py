import os
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from yahooquery import Ticker
from aktiensuche import searchbyname

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback_secure_Secret_Key')
db = SQLAlchemy(app)

# --- LOGIN MANAGER SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bitte melde dich an, um auf diese Seite zuzugreifen.'
login_manager.login_message_category = 'warning'

# --- DATENBANK-MODELLE ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    transactions = db.relationship('Transaction', backref='asset', lazy=True, cascade="all, delete-orphan")
    dividends = db.relationship('Dividend', backref='asset', lazy=True, cascade="all, delete-orphan")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Dividend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    amount_eur = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)

class PortfolioHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, default=date.today)
    total_value = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- HILFSFUNKTION FÜR DEPOT & YAHOO KENNZAHLEN ---

def get_portfolio_data():
    assets = Asset.query.order_by(Asset.name.asc()).all()
    if not assets:
        return [], 0.0, {}, [], [], {}
    
    tickers_list = [asset.symbol for asset in assets]
    if "USDEUR=X" not in tickers_list:
        tickers_list.append("USDEUR=X")

    data = Ticker(tickers_list, asynchronous=True)
    prices = data.price
    summary_detail = data.summary_detail
    key_stats = data.key_stats

    eur_usd_rate = 1.0
    try:
        if isinstance(prices, dict) and "USDEUR=X" in prices and isinstance(prices["USDEUR=X"], dict):
            eur_usd_rate = prices["USDEUR=X"].get("regularMarketPrice", 1.0)
    except Exception:
        pass

    portfolio_items = []
    total_current_value = 0.0
    currency_allocation = {"EUR": 0.0, "USD": 0.0}
    asset_metrics = {}

    for asset in assets:
        total_shares = sum(t.shares for t in asset.transactions)
        if total_shares <= 0:
            continue

        total_invested = sum(t.shares * t.price for t in asset.transactions)
        avg_buy_price = total_invested / total_shares if total_shares > 0 else 0.0

        current_price = 0.0
        try:
            if isinstance(prices, dict) and asset.symbol in prices and isinstance(prices[asset.symbol], dict):
                current_price = prices[asset.symbol].get("regularMarketPrice", 0.0)
        except Exception:
            pass

        if not current_price:
            current_price = avg_buy_price

        multiplier = eur_usd_rate if asset.currency == "USD" else 1.0

        current_value_eur = total_shares * current_price * multiplier
        invested_eur = total_invested * multiplier
        pnl = current_value_eur - (total_shares * avg_buy_price * multiplier)
        pnl_percent = (pnl / invested_eur * 100) if invested_eur > 0 else 0.0

        total_current_value += current_value_eur
        
        if asset.currency in currency_allocation:
            currency_allocation[asset.currency] += current_value_eur
        else:
            currency_allocation[asset.currency] = current_value_eur

        pe_ratio = "N/A"
        high_52 = "N/A"
        low_52 = "N/A"
        ath = "N/A"
        atl = "N/A"
        beta = "N/A"
        last_dividend = "N/A"
        ex_div_date = "N/A"
        yahoo_yield = 0.0

        try:
            if isinstance(summary_detail, dict) and asset.symbol in summary_detail:
                sd = summary_detail[asset.symbol]
                if isinstance(sd, dict):
                    high_52 = sd.get("fiftyTwoWeekHigh", "N/A")
                    low_52 = sd.get("fiftyTwoWeekLow", "N/A")
                    ath = sd.get("allTimeHigh", "N/A")
                    atl = sd.get("allTimeLow", "N/A")
                    last_dividend = sd.get("dividendRate", sd.get("trailingAnnualDividendRate", "N/A"))
                    
                    # Ex-Dividend-Datum direkt auslesen und Datumsteil extrahieren (YYYY-MM-DD)
                    raw_ex_div = sd.get("exDividendDate")
                    if isinstance(raw_ex_div, str) and len(raw_ex_div) >= 10:
                        ex_div_date = raw_ex_div[:10]

                    raw_yield = sd.get("dividendYield", 0.0)
                    if isinstance(raw_yield, (int, float)):
                        yahoo_yield = raw_yield * 100

            if isinstance(key_stats, dict) and asset.symbol in key_stats:
                ks = key_stats[asset.symbol]
                if isinstance(ks, dict):
                    pe_ratio = ks.get("trailingPE", ks.get("forwardPE", "N/A"))
                    beta = ks.get("beta", "N/A")
        except Exception:
            pass

        formatted_last_div = f"{last_dividend:.2f}" if isinstance(last_dividend, (int, float)) else "N/A"
        formatted_yahoo_yield = f"{yahoo_yield:.2f}%" if yahoo_yield > 0 else "N/A"
        formatted_high_52 = f"{high_52:.2f}" if isinstance(high_52, (int, float)) else "N/A"
        formatted_low_52 = f"{low_52:.2f}" if isinstance(low_52, (int, float)) else "N/A"
        formatted_ath = f"{ath:.2f}" if isinstance(ath, (int, float)) else "N/A"
        formatted_atl = f"{atl:.2f}" if isinstance(atl, (int, float)) else "N/A"

        asset_metrics[asset.id] = {
            "pe_ratio": round(pe_ratio, 2) if isinstance(pe_ratio, (int, float)) else pe_ratio,
            "high_52": formatted_high_52,
            "low_52": formatted_low_52,
            "ath": formatted_ath,
            "atl": formatted_atl,
            "beta": round(beta, 2) if isinstance(beta, (int, float)) else beta,
            "last_dividend": formatted_last_div,
            "ex_div_date": ex_div_date,
            "yahoo_yield": formatted_yahoo_yield
        }

        portfolio_items.append({
            "id": asset.id,
            "symbol": asset.symbol,
            "name": asset.name,
            "currency": asset.currency,
            "shares": total_shares,
            "avg_buy_price": avg_buy_price,
            "current_price": current_price,
            "current_value_eur": current_value_eur,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "last_dividend": formatted_last_div,
            "yahoo_yield": formatted_yahoo_yield,
            "transactions": asset.transactions,
            "dividends": asset.dividends
        })

    if total_current_value > 0:
        today = date.today()
        history_entry = PortfolioHistory.query.filter_by(date=today).first()
        if history_entry:
            history_entry.total_value = total_current_value
        else:
            new_history = PortfolioHistory(date=today, total_value=total_current_value)
            db.session.add(new_history)
        db.session.commit()

    history_records = PortfolioHistory.query.order_by(PortfolioHistory.date.asc()).all()
    history_dates = [h.date.strftime("%Y-%m-%d") for h in history_records]
    history_values = [h.total_value for h in history_records]

    return portfolio_items, total_current_value, currency_allocation, history_dates, history_values, asset_metrics


# --- AUTH & ROUTEN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Erfolgreich angemeldet.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Du wurdest erfolgreich abgemeldet.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    items, total_value, currency_allocation, history_dates, history_values, asset_metrics = get_portfolio_data()
    assets = Asset.query.order_by(Asset.name.asc()).all()
    
    search_query = request.args.get('q', '').strip()
    search_results = searchbyname(search_query) if search_query else []

    return render_template(
        'index.html', 
        items=items, 
        total_value=total_value, 
        currency_allocation=currency_allocation,
        history_dates=history_dates,
        history_values=history_values,
        asset_metrics=asset_metrics,
        assets=assets, 
        search_results=search_results,
        search_query=search_query
    )

@app.route('/add_asset', methods=['POST'])
@login_required
def add_asset():
    symbol = request.form.get('symbol', '').strip().upper()
    name = request.form.get('name', '').strip()
    currency = request.form.get('currency', 'EUR').upper()
    if not symbol or not name:
        flash('Bitte alle Felder ausfüllen!', 'danger')
        return redirect(url_for('index') + '#add-content')
    try:
        new_asset = Asset(symbol=symbol, name=name, currency=currency)
        db.session.add(new_asset)
        db.session.commit()
        flash(f'Asset {symbol} erfolgreich hinzugefügt.', 'success')
    except Exception:
        db.session.rollback()
        flash(f'Fehler: Das Asset "{symbol}" existiert bereits.', 'warning')
    
    return redirect(url_for('index') + '#add-content')

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    try:
        asset_id = request.form.get('asset_id')
        shares = float(request.form.get('shares'))
        price = float(request.form.get('price'))
        tx = Transaction(asset_id=asset_id, shares=shares, price=price)
        db.session.add(tx)
        db.session.commit()
        flash('Transaktion erfolgreich gebucht.', 'success')
    except Exception:
        db.session.rollback()
        flash('Fehler beim Speichern der Transaktion.', 'danger')
    return redirect(url_for('index') + '#add-content')

@app.route('/add_dividend', methods=['POST'])
@login_required
def add_dividend():
    try:
        asset_id = request.form.get('asset_id')
        amount_eur = float(request.form.get('amount_eur'))
        div_date = request.form.get('date')
        d = Dividend(asset_id=asset_id, amount_eur=amount_eur, date=date.fromisoformat(div_date) if div_date else date.today())
        db.session.add(d)
        db.session.commit()
        flash('Dividende erfolgreich gebucht.', 'success')
    except Exception:
        db.session.rollback()
        flash('Fehler beim Speichern der Dividende.', 'danger')
    return redirect(url_for('index'))

@app.route('/update_transaction/<int:tx_id>', methods=['POST'])
@login_required
def update_transaction(tx_id):
    tx = Transaction.query.get_or_404(tx_id)
    try:
        tx.shares = float(request.form.get('shares'))
        tx.price = float(request.form.get('price'))
        db.session.commit()
        flash('Transaktion aktualisiert.', 'success')
    except Exception:
        db.session.rollback()
        flash('Fehler beim Aktualisieren.', 'danger')
    return redirect(url_for('index'))

@app.route('/delete_transaction/<int:tx_id>', methods=['POST'])
@login_required
def delete_transaction(tx_id):
    tx = Transaction.query.get_or_404(tx_id)
    try:
        db.session.delete(tx)
        db.session.commit()
        flash('Transaktion gelöscht.', 'success')
    except Exception:
        db.session.rollback()
        flash('Fehler beim Löschen.', 'danger')
    return redirect(url_for('index'))

@app.route('/delete_dividend/<int:div_id>', methods=['POST'])
@login_required
def delete_dividend(div_id):
    div = Dividend.query.get_or_404(div_id)
    try:
        db.session.delete(div)
        db.session.commit()
        flash('Dividende gelöscht.', 'success')
    except Exception:
        db.session.rollback()
        flash('Fehler beim Löschen.', 'danger')
    return redirect(url_for('index'))

@app.route('/api/asset_history/<string:symbol>')
@login_required
def api_asset_history(symbol):
    try:
        t = Ticker(symbol.upper())
        hist_df = t.history(period='1y')
        
        dates = []
        prices = []
        
        if not hist_df.empty:
            # MultiIndex prüfen
            if symbol.upper() in hist_df.index.get_level_values(0):
                asset_hist = hist_df.loc[symbol.upper()]
                for idx, row in asset_hist.iterrows():
                    d_val = idx[1] if isinstance(idx, tuple) else idx
                    dates.append(str(d_val)[:10])
                    prices.append(float(row['close']))
            else:
                # Fallback falls kein MultiIndex
                for idx, row in hist_df.iterrows():
                    dates.append(str(idx)[:10])
                    prices.append(float(row['close']))
                    
        return {"dates": dates, "prices": prices}
    except Exception as e:
        return {"dates": [], "prices": [], "error": str(e)}, 500
    
if __name__ == '__main__':
    app.run(debug=True)