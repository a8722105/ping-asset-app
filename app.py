
from flask import Flask, request, jsonify, send_from_directory
import yfinance as yf
import pandas as pd

app = Flask(__name__, static_folder='.')

def get_stock_price(symbol):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d")
    if not data.empty:
        return float(data["Close"].iloc[-1])
    return 0

def get_dividends(symbol):
    ticker = yf.Ticker(symbol)
    dividends = ticker.dividends
    return float(dividends.sum())

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json

    symbol = data["symbol"]
    shares = float(data["shares"])
    cost_price = float(data["cost_price"])
    loan_amount = float(data["loan_amount"])
    loan_rate = float(data["loan_rate"])

    current_price = get_stock_price(symbol)
    total_cost = shares * cost_price
    market_value = shares * current_price
    unrealized_profit = market_value - total_cost
    dividends = get_dividends(symbol)

    monthly_interest = loan_amount * (loan_rate / 100) / 12

    return jsonify({
        "current_price": round(current_price, 2),
        "total_cost": round(total_cost, 2),
        "market_value": round(market_value, 2),
        "unrealized_profit": round(unrealized_profit, 2),
        "total_dividends": round(dividends, 2),
        "monthly_interest": round(monthly_interest, 2),
        "net_value": round(market_value - loan_amount, 2)
    })

@app.route("/")
def serve_index():
    return send_from_directory('.', 'index.html')

if __name__ == "__main__":
    app.run(debug=True)
