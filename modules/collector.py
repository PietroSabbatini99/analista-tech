import json
import subprocess
import yfinance as yf
import requests
from datetime import datetime, timedelta, timezone
from typing import Any

TV_CLI = "/Users/pietrosabbatini/go/bin/tradingview-pp-cli"
YF_CLI = "/Users/pietrosabbatini/go/bin/yahoo-finance-pp-cli"


def fetch_financial_snapshot(ticker: str) -> dict[str, Any]:
    t = yf.Ticker(ticker)
    info = t.info or {}

    revenue_growth = float(info.get("revenueGrowth") or 0.0)
    gross_margin   = float(info.get("grossMargins") or 0.0)
    total_cash     = float(info.get("totalCash") or 0.0)
    price_to_sales = float(info.get("priceToSalesTrailing12Months") or 0.0)
    market_cap     = float(info.get("marketCap") or 0.0)
    trailing_pe    = float(info.get("trailingPE") or 0.0)
    forward_pe     = float(info.get("forwardPE") or 0.0)
    current_price  = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
    analyst_target = float(info.get("targetMeanPrice") or 0.0)
    analyst_count  = int(info.get("numberOfAnalystOpinions") or 0)
    analyst_upside = round((analyst_target - current_price) / current_price * 100, 1) if current_price and analyst_target else 0.0
    short_percent  = round(float(info.get("shortPercentOfFloat") or 0.0) * 100, 2)
    short_ratio    = round(float(info.get("shortRatio") or 0.0), 1)

    hist = t.history(period="3mo")
    momentum_20_60 = 0.0
    volume_spike   = 0.0
    if not hist.empty and len(hist) >= 20:
        close  = hist["Close"]
        avg20  = close.iloc[-20:].mean()
        avg60  = close.mean() if len(hist) < 60 else close.iloc[-60:].mean()
        momentum_20_60 = float((avg20 - avg60) / avg60) if avg60 else 0.0

        vol       = hist["Volume"]
        avg_vol20 = vol.iloc[-20:].mean()
        avg_vol60 = vol.mean() if len(vol) < 60 else vol.iloc[-60:].mean()
        volume_spike = float((avg_vol20 - avg_vol60) / avg_vol60) if avg_vol60 else 0.0

        # Accumulation: price flat (±5%) + volume spike >30% = smart money building
        price_change_20 = float((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) if len(close) >= 20 else 0.0
        accumulation    = abs(price_change_20) <= 0.05 and volume_spike >= 0.30
    else:
        price_change_20 = 0.0
        accumulation    = False

    # Cap tier
    if market_cap >= 10_000_000_000:
        cap_tier = "large"
    elif market_cap >= 1_000_000_000:
        cap_tier = "mid"
    else:
        cap_tier = "small"

    return {
        "ticker":          ticker,
        "revenue_growth":  revenue_growth,
        "gross_margin":    gross_margin,
        "total_cash":      total_cash,
        "price_to_sales":  price_to_sales,
        "market_cap":      market_cap,
        "momentum_20_60":  momentum_20_60,
        "volume_spike":    volume_spike,
        "price_change_20": round(price_change_20, 4),
        "accumulation":    accumulation,
        "cap_tier":        cap_tier,
        "trailing_pe":    trailing_pe,
        "forward_pe":     forward_pe,
        "analyst_target": analyst_target,
        "analyst_upside": analyst_upside,
        "analyst_count":  analyst_count,
        "short_percent":  short_percent,
        "short_ratio":    short_ratio,
    }


def fetch_tv_analysis(ticker: str) -> dict[str, Any]:
    """Fetch TradingView TA via tradingview-pp-cli (replaces tradingview-ta Python library)."""
    try:
        result = subprocess.run(
            [TV_CLI, "export", ticker, "--format", "analista", "--json"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if data:
                d = data[0]
                return {
                    "recommendation": d.get("tv_recommendation", "NEUTRAL"),
                    "buy":            d.get("tv_buy", 0),
                    "sell":           d.get("tv_sell", 0),
                    "neutral":        d.get("tv_neutral", 0),
                    "rsi":            round(d.get("tv_rsi", 50.0), 2),
                    "macd":           round(d.get("tv_macd", 0.0), 4),
                    "ema_cross":      round(d.get("tv_ema_cross", 0.0), 2),
                }
    except Exception:
        pass
    return {
        "recommendation": "NEUTRAL",
        "buy": 0, "sell": 0, "neutral": 0,
        "rsi": 50.0, "macd": 0.0, "ema_cross": 0.0,
    }


# All field names verified against scanner.tradingview.com/america/scan
TV_BATCH_COLUMNS = [
    # Technicals
    "Recommend.All", "Recommend.MA", "Recommend.Other",
    "RSI", "MACD.macd", "MACD.signal",
    "EMA20", "EMA50", "EMA200",
    "close", "volume", "change", "market_cap_basic",
    # Income Statement
    "total_revenue",                   # Revenue TTM
    "gross_profit",                    # Gross Profit TTM
    "net_income",                      # Net Income TTM
    "ebitda",                          # EBITDA TTM
    "earnings_per_share_diluted_ttm",  # EPS Diluted TTM
    # Balance Sheet
    "total_assets",
    "total_debt",
    "total_equity_fq",                 # Shareholders' Equity
    "cash_n_equivalents_fq",           # Cash & Equivalents
    # Cash Flow
    "free_cash_flow",                  # FCF TTM
    "cash_f_operating_activities_fq",  # Operating Cash Flow
    # Ratios
    "price_earnings_ttm",              # P/E Trailing
    "price_book_fq",                   # P/B
    "enterprise_value_ebitda_ttm",     # EV/EBITDA
    "debt_to_equity",                  # D/E Ratio
    "return_on_equity",                # ROE %
    "return_on_assets",                # ROA %
    "price_revenue_ttm",               # P/S (Price/Revenue)
    "current_ratio",                   # Current Ratio
    "quick_ratio",                     # Quick Ratio
    # Margins (%)
    "gross_margin",                    # Gross Margin %
    "operating_margin",                # Operating Margin %
    "net_margin",                      # Net Margin %
    # Analyst & Performance
    "price_target_average",            # Analyst avg price target
    "Perf.1M",                         # 1-month price performance %
]


def _tv_score_to_rec(score: float) -> str:
    if score >= 0.5:  return "STRONG_BUY"
    if score >= 0.1:  return "BUY"
    if score > -0.1:  return "NEUTRAL"
    if score > -0.5:  return "SELL"
    return "STRONG_SELL"


def _tv_rec_counts(score: float) -> tuple[int, int, int]:
    return {
        "STRONG_BUY":  (15, 1, 10),
        "BUY":         (10, 3, 13),
        "NEUTRAL":     (5,  5, 16),
        "SELL":        (3,  10, 13),
        "STRONG_SELL": (1,  15, 10),
    }.get(_tv_score_to_rec(score), (5, 5, 16))


def fetch_tv_batch(tickers: list[str], market: str = "america") -> dict[str, dict[str, Any]]:
    """Fetch TradingView technicals + fundamentals for ALL tickers in ONE call.
    Returns {TICKER: {all_fields}}.  Replaces the per-ticker fetch_tv_analysis loop."""
    if not tickers:
        return {}

    def _norm(t: str) -> str:
        return t.upper() if ":" in t else f"NASDAQ:{t.upper()}"

    normalized = [_norm(t) for t in tickers]
    payload = {"symbols": {"tickers": normalized}, "columns": TV_BATCH_COLUMNS}
    try:
        resp = requests.post(
            f"https://scanner.tradingview.com/{market}/scan",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent":   "Mozilla/5.0 (compatible; analista-tech/1.0)",
                "Origin":       "https://www.tradingview.com",
                "Referer":      "https://www.tradingview.com/",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    cidx = {c: i for i, c in enumerate(TV_BATCH_COLUMNS)}

    def _g(d: list, col: str) -> float:
        i = cidx.get(col)
        if i is None or i >= len(d) or d[i] is None:
            return 0.0
        try:   return float(d[i])
        except: return 0.0

    result: dict[str, dict[str, Any]] = {}
    for item in data.get("data", []):
        sym = item.get("s", "")
        d   = item.get("d", [])
        key = sym.split(":")[-1] if ":" in sym else sym

        rec_score = _g(d, "Recommend.All")
        ema20, ema50 = _g(d, "EMA20"), _g(d, "EMA50")
        ema_cross = round((ema20 - ema50) / ema50 * 100, 2) if ema50 else 0.0
        buy, sell, neutral = _tv_rec_counts(rec_score)

        result[key] = {
            # Technicals
            "recommendation":  _tv_score_to_rec(rec_score),
            "recommend_score": rec_score,
            "buy": buy, "sell": sell, "neutral": neutral,
            "rsi":         round(_g(d, "RSI"), 2),
            "macd":        round(_g(d, "MACD.macd"), 4),
            "macd_signal": round(_g(d, "MACD.signal"), 4),
            "ema20": ema20, "ema50": ema50, "ema200": _g(d, "EMA200"),
            "ema_cross": ema_cross,
            "close": _g(d, "close"), "volume": _g(d, "volume"),
            "change": _g(d, "change"),
            "market_cap": _g(d, "market_cap_basic"),
            # Income Statement
            "total_revenue":   _g(d, "total_revenue"),
            "gross_profit":    _g(d, "gross_profit"),
            "net_income":      _g(d, "net_income"),
            "ebitda":          _g(d, "ebitda"),
            "eps_diluted_ttm": _g(d, "earnings_per_share_diluted_ttm"),
            # Balance Sheet
            "total_assets":  _g(d, "total_assets"),
            "total_debt":    _g(d, "total_debt"),
            "total_equity":  _g(d, "total_equity_fq"),
            "total_cash":    _g(d, "cash_n_equivalents_fq"),
            # Cash Flow
            "free_cash_flow": _g(d, "free_cash_flow"),
            "cash_from_ops":  _g(d, "cash_f_operating_activities_fq"),
            # Ratios
            "pe_ratio":       _g(d, "price_earnings_ttm"),
            "price_to_book":  _g(d, "price_book_fq"),
            "ev_ebitda":      _g(d, "enterprise_value_ebitda_ttm"),
            "debt_to_equity": _g(d, "debt_to_equity"),
            "roe":            _g(d, "return_on_equity"),
            "roa":            _g(d, "return_on_assets"),
            "price_to_sales": _g(d, "price_revenue_ttm"),
            "current_ratio":  _g(d, "current_ratio"),
            "quick_ratio":    _g(d, "quick_ratio"),
            # Margins
            "gross_margin":     _g(d, "gross_margin"),
            "operating_margin": _g(d, "operating_margin"),
            "net_margin":       _g(d, "net_margin"),
            # Analyst & Performance
            "analyst_target": _g(d, "price_target_average"),
            "perf_1m":        _g(d, "Perf.1M"),
        }
    return result


def fetch_yahoo_quote(ticker: str) -> dict[str, Any]:
    """Fetch real-time quote from Yahoo Finance via yahoo-finance-pp-cli."""
    try:
        result = subprocess.run(
            [YF_CLI, "quote", "--symbols", ticker, "--json"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = json.loads(result.stdout)
            # Handle nested: {results: {quoteResponse: {result: [...]}}}
            d = {}
            if isinstance(raw, dict) and "results" in raw:
                qr = raw["results"].get("quoteResponse", {}).get("result", [])
                if qr:
                    d = qr[0]
            elif isinstance(raw, list) and raw:
                d = raw[0]
            elif isinstance(raw, dict):
                d = raw
            if d:
                return {
                    "price":      float(d.get("regularMarketPrice") or 0),
                    "change_pct": float(d.get("regularMarketChangePercent") or 0),
                    "volume":     float(d.get("regularMarketVolume") or 0),
                    "market_cap": float(d.get("marketCap") or 0),
                    "52w_high":   float(d.get("fiftyTwoWeekHigh") or 0),
                    "52w_low":    float(d.get("fiftyTwoWeekLow") or 0),
                }
    except Exception:
        pass
    return {}


def fetch_earnings_surprise(ticker: str) -> list[dict[str, Any]]:
    try:
        dates = yf.Ticker(ticker).earnings_dates
        if dates is None or dates.empty:
            return []
        valid = dates.dropna(subset=["EPS Estimate", "Reported EPS"]).head(4)
        results = []
        for idx, row in valid.iterrows():
            estimate = float(row.get("EPS Estimate") or 0)
            reported = float(row.get("Reported EPS") or 0)
            surprise  = float(row.get("Surprise(%)") or 0)
            results.append({
                "date":         str(idx.date()) if hasattr(idx, "date") else str(idx)[:10],
                "estimate":     round(estimate, 2),
                "reported":     round(reported, 2),
                "surprise_pct": round(surprise, 1),
            })
        return results
    except Exception:
        return []


def fetch_earnings_calendar(ticker: str) -> dict[str, Any]:
    try:
        import datetime as _dt
        cal = yf.Ticker(ticker).calendar
        if cal and "Earnings Date" in cal:
            dates = cal["Earnings Date"]
            if dates:
                next_dt = dates[0]
                # dates[0] is datetime.date or datetime.datetime — handle both
                if isinstance(next_dt, _dt.datetime):
                    next_date = next_dt.date()
                else:
                    next_date = next_dt          # already datetime.date
                days_until = (next_date - datetime.now(timezone.utc).date()).days
                return {"next_earnings": str(next_date), "days_until_earnings": days_until}
    except Exception:
        pass
    return {"next_earnings": None, "days_until_earnings": None}


def fetch_insider_trades(company_name: str, days: int = 30) -> dict[str, Any]:
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {"q": f'"{company_name}"', "forms": "4", "dateRange": "custom", "startdt": start}
    try:
        resp = requests.get("https://efts.sec.gov/LATEST/search-index", params=params, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        return {"insider_filings_30d": len(hits)}
    except Exception:
        return {"insider_filings_30d": 0}


def fetch_institutional_holders(ticker: str) -> dict[str, Any]:
    try:
        holders = yf.Ticker(ticker).institutional_holders
        if holders is not None and not holders.empty:
            pct_col = next((c for c in holders.columns if "%" in c or "pct" in c.lower()), None)
            total_pct = float(holders[pct_col].sum()) * 100 if pct_col else 0.0
            top = str(holders.iloc[0].get("Holder", "")) if len(holders) > 0 else ""
            return {"institutional_pct": round(total_pct, 1), "top_holder": top}
    except Exception:
        pass
    return {"institutional_pct": 0.0, "top_holder": ""}


def fetch_edgar_filings(company_name: str, days: int = 14) -> list[dict[str, Any]]:
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "q": f'"{company_name}"',
        "forms": "8-K,10-Q",
        "dateRange": "custom",
        "startdt": start,
    }
    try:
        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params=params, timeout=10
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
    except Exception:
        return []

    return [
        {
            "form_type": h["_source"].get("form_type", ""),
            "file_date": h["_source"].get("file_date", ""),
            "period":    h["_source"].get("period_of_report", ""),
        }
        for h in hits[:5]
    ]


def fetch_yahoo_trending(region: str = "US") -> list[str]:
    """Return list of trending tickers on Yahoo Finance right now."""
    try:
        result = subprocess.run(
            [YF_CLI, "trending", region, "--json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = json.loads(result.stdout)
            quotes = (raw.get("results", {})
                        .get("finance", {})
                        .get("result", [{}])[0]
                        .get("quotes", []))
            return [q["symbol"] for q in quotes if "symbol" in q]
    except Exception:
        pass
    return []


def fetch_yahoo_insights(ticker: str) -> dict[str, Any]:
    """Fetch Yahoo Finance insights: technical events, valuation signals, research."""
    try:
        result = subprocess.run(
            [YF_CLI, "insights", "--symbols", ticker, "--json"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = json.loads(result.stdout)
            # Navigate nested structure
            data = (raw.get("results", {})
                       .get("finance", {})
                       .get("result", {})
                       .get(ticker, {}))
            if not data:
                # try flat structure
                data = raw if isinstance(raw, dict) else {}

            tech = data.get("instrumentInfo", {}).get("technicalEvents", {})
            val  = data.get("instrumentInfo", {}).get("valuation", {})
            sig  = data.get("upsell", {})

            return {
                "short_term_outlook":  tech.get("shortTermOutlook", {}).get("direction", ""),
                "mid_term_outlook":    tech.get("intermediateTermOutlook", {}).get("direction", ""),
                "long_term_outlook":   tech.get("longTermOutlook", {}).get("direction", ""),
                "valuation_description": val.get("description", ""),
                "valuation_discount":  val.get("discount", ""),
            }
    except Exception:
        pass
    return {}
