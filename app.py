from flask import Flask, request, jsonify, send_from_directory
import yfinance as yf

app = Flask(__name__, static_folder='.')

def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def get_price(symbol: str) -> float:
    t = yf.Ticker(symbol)
    hist = t.history(period="1d")
    if hist is None or hist.empty:
        return 0.0
    return float(hist["Close"].iloc[-1])

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/portfolio", methods=["POST"])
def portfolio():
    payload = request.get_json(force=True) or {}
    holdings = payload.get("holdings", [])
    loans = payload.get("loans", [])

    invest_rows = []
    invest_mv_total = 0.0
    invest_cost_total = 0.0

    for h in holdings:
        symbol = (h.get("symbol") or "").strip()
        if not symbol:
            continue

        name = (h.get("name") or "").strip()
        unit = (h.get("unit") or "shares").strip()  # "lots" or "shares"
        qty = safe_float(h.get("qty"), 0)
        cost = safe_float(h.get("cost"), 0)

        # lots -> shares
        shares = qty * 1000 if unit == "lots" else qty

        price = get_price(symbol)
        cost_total = shares * cost
        mv = shares * price
        upl = mv - cost_total
        ret = (upl / cost_total * 100) if cost_total > 0 else 0.0

        invest_rows.append({
            "symbol": symbol,
            "name": name,
            "shares": round(shares, 2),
            "cost": round(cost, 4),
            "price": round(price, 4),
            "cost_total": round(cost_total, 2),
            "market_value": round(mv, 2),
            "unrealized_pl": round(upl, 2),
            "return_pct": round(ret, 2)
        })

        invest_mv_total += mv
        invest_cost_total += cost_total

    loan_rows = []
    loan_principal_total = 0.0
    loan_monthly_int_total = 0.0

    for l in loans:
        lname = (l.get("name") or "").strip()
        principal = safe_float(l.get("principal"), 0)
        rate = safe_float(l.get("rate"), 0)  # annual %
        monthly_int = principal * (rate / 100.0) / 12.0

        loan_rows.append({
            "name": lname,
            "principal": round(principal, 2),
            "rate": round(rate, 4),
            "monthly_interest": round(monthly_int, 2),
            "annual_interest": round(monthly_int * 12, 2)
        })

        loan_principal_total += principal
        loan_monthly_int_total += monthly_int

    net_worth = invest_mv_total - loan_principal_total

    return jsonify({
        "invest": invest_rows,
        "totals": {
            "invest_cost_total": round(invest_cost_total, 2),
            "invest_market_value_total": round(invest_mv_total, 2),
            "loan_principal_total": round(loan_principal_total, 2),
            "loan_monthly_interest_total": round(loan_monthly_int_total, 2),
            "net_worth": round(net_worth, 2)
        },
        "loans": loan_rows
    })

@app.route("/health")
def health():
    return "ok"
