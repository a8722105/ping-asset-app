from flask import Flask, request, jsonify, send_from_directory
import yfinance as yf
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='.')

def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def get_price(symbol: str) -> float:
    t = yf.Ticker(symbol)
    hist = t.history(period="5d")
    if hist is None or hist.empty:
        return 0.0
    return float(hist["Close"].dropna().iloc[-1])

def get_dividend_ttm_per_share(symbol: str) -> float:
    """
    近一年(約365天)每股股息加總。
    若抓不到股息資料，回傳 0。
    """
    try:
        t = yf.Ticker(symbol)
        div = t.dividends
        if div is None or div.empty:
            return 0.0
        cutoff = datetime.now() - timedelta(days=365)
        div = div[div.index.to_pydatetime() >= cutoff]
        return float(div.sum()) if not div.empty else 0.0
    except:
        return 0.0

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
    invest_div_ttm_total = 0.0

    for h in holdings:
        symbol = (h.get("symbol") or "").strip()
        if not symbol:
            continue

        asset_type = (h.get("asset_type") or "stock").strip()  # "stock" or "fund"
        name = (h.get("name") or "").strip()

        unit = (h.get("unit") or "shares").strip()  # "lots" or "shares" (stock/ETF)
        qty = safe_float(h.get("qty"), 0)
        cost = safe_float(h.get("cost"), 0)

        # fund fields
        nav_mode = (h.get("nav_mode") or "auto").strip()  # "auto" or "manual"
        manual_nav = safe_float(h.get("manual_nav"), 0)

        # shares / units
        if asset_type == "stock":
            shares = qty * 1000 if unit == "lots" else qty
            price = get_price(symbol)
        else:
            # fund uses "units" concept; qty is units
            shares = qty
            if nav_mode == "manual":
                price = manual_nav
            else:
                price = get_price(symbol)

        cost_total = shares * cost
        mv = shares * price
        upl = mv - cost_total
        ret = (upl / cost_total * 100) if cost_total > 0 else 0.0

        # dividends only for stock/ETF (基金配息可下一版加「配息明細」或手動輸入)
        div_ttm_per_share = get_dividend_ttm_per_share(symbol) if asset_type == "stock" else 0.0
        div_ttm_total = div_ttm_per_share * shares
        div_yield_price = (div_ttm_per_share / price * 100) if price > 0 else 0.0
        div_yield_cost = (div_ttm_per_share / cost * 100) if cost > 0 else 0.0

        invest_rows.append({
            "asset_type": asset_type,
            "symbol": symbol,
            "name": name,
            "units": round(shares, 4),  # 股數/基金份額
            "cost": round(cost, 6),
            "price": round(price, 6),
            "cost_total": round(cost_total, 2),
            "market_value": round(mv, 2),
            "unrealized_pl": round(upl, 2),
            "return_pct": round(ret, 2),

            "div_ttm_per_share": round(div_ttm_per_share, 6),
            "div_ttm_total": round(div_ttm_total, 2),
            "div_yield_price_pct": round(div_yield_price, 2),
            "div_yield_cost_pct": round(div_yield_cost, 2),
        })

        invest_mv_total += mv
        invest_cost_total += cost_total
        invest_div_ttm_total += div_ttm_total

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
            "invest_div_ttm_total": round(invest_div_ttm_total, 2),

            "loan_principal_total": round(loan_principal_total, 2),
            "loan_monthly_interest_total": round(loan_monthly_int_total, 2),
            "net_worth": round(net_worth, 2)
        },
        "loans": loan_rows
    })

@app.route("/health")
def health():
    return "ok"
