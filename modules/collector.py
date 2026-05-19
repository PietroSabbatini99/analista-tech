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
        cal = yf.Ticker(ticker).calendar
        if cal and "Earnings Date" in cal:
            dates = cal["Earnings Date"]
            if dates:
                next_dt = dates[0]
                days_until = (next_dt.date() - datetime.now(timezone.utc).date()).days
                return {"next_earnings": str(next_dt.date()), "days_until_earnings": days_until}
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
