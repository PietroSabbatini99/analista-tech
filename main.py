#!/usr/bin/env python3
import os
import sys
import logging
from datetime import date, datetime
from pathlib import Path
from dotenv import load_dotenv
import yaml

from modules.db import init_db, get_connection
from modules.universe import load_universe
from modules.collector import (
    fetch_financial_snapshot, fetch_edgar_filings,
    fetch_tv_analysis, fetch_tv_batch,
    fetch_earnings_calendar, fetch_insider_trades, fetch_institutional_holders,
    fetch_earnings_surprise,
    fetch_yahoo_trending,
)
from modules.researcher import fetch_exa_news, fetch_rss_news, fetch_x_mentions
from modules.analyzer import score_company, generate_narrative
from modules.reporter import (
    generate_html_report, generate_md_report,
    save_alerts_json, send_macos_notification, send_weekly_email,
)

BASE_DIR = Path(__file__).parent
CONFIG   = BASE_DIR / "config.yaml"
DB_PATH  = str(BASE_DIR / "data" / "tech_analyst.db")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "data" / "agent.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def main():
    load_dotenv(BASE_DIR / ".env", override=True)
    anthropic_key = os.environ["ANTHROPIC_API_KEY"]
    exa_key       = os.environ["EXA_API_KEY"]
    gmail_addr    = os.environ.get("GMAIL_ADDRESS", "")
    gmail_pass    = os.environ.get("GMAIL_APP_PASSWORD", "")
    alert_email   = os.environ.get("ALERT_EMAIL_TO", gmail_addr)

    with open(CONFIG) as f:
        cfg = yaml.safe_load(f)

    threshold  = float(cfg.get("alerts", {}).get("score_threshold", 75))
    rss_feeds  = cfg.get("rss_feeds", [])
    x_accounts = cfg.get("x_accounts", [])

    init_db(DB_PATH)
    companies = load_universe(str(CONFIG))
    today     = date.today().isoformat()

    report_dir = BASE_DIR / "reports" / today
    report_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Pipeline start — {today} — {len(companies)} companies")

    # Fetch trending tickers once (retail attention signal)
    trending_set = set(fetch_yahoo_trending())
    log.info(f"Trending tickers: {sorted(trending_set)}")

    # ── TV batch: ONE call for all tickers (technicals + fundamentals) ────────
    all_ticker_list = [c["ticker"] for c in companies]
    log.info(f"Fetching TV batch for {len(all_ticker_list)} tickers...")
    tv_batch = fetch_tv_batch(all_ticker_list)
    log.info(f"TV batch returned {len(tv_batch)} tickers")

    # Pass 1: collect yfinance-exclusive data (short interest, analyst targets,
    # earnings calendar, insider trades, institutional holders, hist bars)
    financials = {}
    tv_cache   = {}
    for company in companies:
        ticker = company["ticker"]
        try:
            fin = fetch_financial_snapshot(ticker)
            fin["name"]        = company["name"]
            fin["sector"]      = company["sector"]
            fin["is_trending"] = ticker in trending_set

            # Merge TV batch data — richer than yfinance for most fundamentals
            tv = tv_batch.get(ticker, {})
            if tv:
                # Override yfinance fundamentals with TV data where available
                if tv.get("total_revenue"):
                    fin["total_revenue"]    = tv["total_revenue"]
                    fin["gross_profit"]     = tv.get("gross_profit", 0)
                    fin["net_income"]       = tv.get("net_income", 0)
                    fin["ebitda"]           = tv.get("ebitda", 0)
                    fin["eps_diluted"]      = tv.get("eps_diluted_ttm", 0)
                if tv.get("gross_margin"):
                    fin["gross_margin_tv"]  = tv["gross_margin"]
                    fin["operating_margin"] = tv.get("operating_margin", 0)
                    fin["net_margin"]       = tv.get("net_margin", 0)
                if tv.get("roe"):
                    fin["roe"]              = tv["roe"]
                    fin["roa"]              = tv.get("roa", 0)
                fin["ev_ebitda"]            = tv.get("ev_ebitda", 0)
                fin["price_to_book"]        = tv.get("price_to_book", 0)
                fin["current_ratio"]        = tv.get("current_ratio", 0)
                fin["quick_ratio"]          = tv.get("quick_ratio", 0)
                fin["free_cash_flow"]       = tv.get("free_cash_flow", 0)
                fin["total_equity"]         = tv.get("total_equity", 0)
                fin["tv_analyst_target"]    = tv.get("analyst_target", 0)
                fin["perf_1m"]              = tv.get("perf_1m", 0)
                if not fin.get("market_cap") and tv.get("market_cap"):
                    fin["market_cap"]       = tv["market_cap"]

            fin.update(fetch_earnings_calendar(ticker))
            fin.update(fetch_insider_trades(company["name"]))
            fin.update(fetch_institutional_holders(ticker))
            fin["earnings_history"] = fetch_earnings_surprise(ticker)
            financials[ticker] = fin
            tv_cache[ticker]   = tv  # already fetched — no extra call
        except Exception as e:
            log.warning(f"  {ticker} data error: {e}")

    # Compute sector correlation matrices via yf.download (one call, all tickers)
    import yfinance as yf
    import pandas as pd
    all_tickers = list(financials.keys())
    sector_correlations: dict[str, Any] = {}
    try:
        prices = yf.download(all_tickers, period="3mo", auto_adjust=True, progress=False)["Close"]
        returns = prices.pct_change().dropna()

        def _corr_color(v: float) -> str:
            if v >= 0.8:  return "#ef4444"
            if v >= 0.6:  return "#f97316"
            if v >= 0.4:  return "#f59e0b"
            if v >= 0.2:  return "#84cc16"
            if v >= 0.0:  return "#22c55e"
            return "#6366f1"

        sector_groups: dict[str, list[str]] = {}
        for ticker, fin in financials.items():
            s = fin["sector"]
            sector_groups.setdefault(s, []).append(ticker)

        for sector, tickers in sector_groups.items():
            valid = [t for t in tickers if t in returns.columns]
            if len(valid) < 2:
                continue
            corr = returns[valid].corr()
            rows = []
            for i, row_t in enumerate(valid):
                cells = []
                for j, col_t in enumerate(valid):
                    val = round(float(corr.loc[row_t, col_t]), 2)
                    cells.append({"val": val, "color": _corr_color(val), "diag": i == j})
                rows.append({"ticker": row_t, "cells": cells})
            sector_correlations[sector] = {"tickers": valid, "rows": rows}
        log.info(f"Correlation computed for {len(sector_correlations)} sectors")
    except Exception as e:
        log.warning(f"Correlation matrix failed: {e}")

    # Compute sector avg P/E (trailing, exclude 0/missing)
    from collections import defaultdict
    sector_pes: dict[str, list[float]] = defaultdict(list)
    for fin in financials.values():
        if fin["trailing_pe"] > 0:
            sector_pes[fin["sector"]].append(fin["trailing_pe"])
    sector_avg_pe: dict[str, float] = {
        s: round(sum(v) / len(v), 1) for s, v in sector_pes.items() if v
    }
    log.info(f"Sector avg P/E: {sector_avg_pe}")

    # Pass 2: news + scoring (Claude)
    all_scores = []
    for company in companies:
        ticker = company["ticker"]
        name   = company["name"]
        if ticker not in financials:
            continue
        log.info(f"  {ticker}")

        financial   = financials[ticker]
        tv_data     = tv_cache[ticker]
        avg_pe      = sector_avg_pe.get(company["sector"], 0.0)
        financial["sector_avg_pe"] = avg_pe

        news  = fetch_exa_news(name, ticker, exa_key)
        news += fetch_rss_news(name, ticker, rss_feeds)
        news += fetch_x_mentions(name, ticker, exa_key, x_accounts)

        scored          = score_company(financial, news, anthropic_key, tv_data)
        scored["name"]             = name
        scored["sector"]           = company["sector"]
        scored["trailing_pe"]      = financial.get("trailing_pe", 0.0)
        scored["forward_pe"]       = financial.get("forward_pe", 0.0)
        scored["sector_avg_pe"]    = avg_pe
        scored["analyst_target"]   = financial.get("analyst_target", 0.0)
        scored["analyst_upside"]   = financial.get("analyst_upside", 0.0)
        scored["analyst_count"]    = financial.get("analyst_count", 0)
        scored["short_percent"]    = financial.get("short_percent", 0.0)
        scored["short_ratio"]      = financial.get("short_ratio", 0.0)
        scored["next_earnings"]    = financial.get("next_earnings") or "N/A"
        scored["days_until_earnings"] = financial.get("days_until_earnings")
        scored["insider_filings_30d"] = financial.get("insider_filings_30d", 0)
        scored["institutional_pct"]   = financial.get("institutional_pct", 0.0)
        scored["top_holder"]       = financial.get("top_holder") or "N/A"
        tv = tv_cache.get(ticker, {})
        scored["tv_recommendation"] = tv.get("recommendation", "N/A")
        scored["tv_rsi"]           = tv.get("rsi", 50.0)
        scored["tv_macd"]          = tv.get("macd", 0.0)
        scored["tv_ema_cross"]     = tv.get("ema_cross", 0.0)
        scored["tv_buy"]           = tv.get("buy", 0)
        scored["cap_tier"]         = financial.get("cap_tier", "large")
        # TV fundamentals (batch)
        scored["gross_margin"]     = tv.get("gross_margin", 0.0)
        scored["operating_margin"] = tv.get("operating_margin", 0.0)
        scored["net_margin"]       = tv.get("net_margin", 0.0)
        scored["roe"]              = tv.get("roe", 0.0)
        scored["roa"]              = tv.get("roa", 0.0)
        scored["ev_ebitda"]        = tv.get("ev_ebitda", 0.0)
        scored["price_to_book"]    = tv.get("price_to_book", 0.0)
        scored["free_cash_flow"]   = tv.get("free_cash_flow", 0.0)
        scored["total_revenue"]    = tv.get("total_revenue", 0.0)
        scored["net_income"]       = tv.get("net_income", 0.0)
        scored["ebitda"]           = tv.get("ebitda", 0.0)
        scored["debt_to_equity"]   = tv.get("debt_to_equity", 0.0)
        scored["current_ratio"]    = tv.get("current_ratio", 0.0)
        scored["perf_1m"]          = tv.get("perf_1m", 0.0)
        scored["accumulation"]     = financial.get("accumulation", False)
        scored["price_change_20"]  = financial.get("price_change_20", 0.0)
        scored["tv_sell"]          = tv.get("sell", 0)
        scored["earnings_history"] = financial.get("earnings_history", [])
        scored["is_trending"]      = financial.get("is_trending", False)

        conn = get_connection(DB_PATH)
        conn.execute(
            """INSERT OR REPLACE INTO daily_scores
               (ticker,date,score_revenue,score_margins,score_news,
                score_influencer,score_momentum,total_score,narrative,
                name,sector,cap_tier,accumulation,price_change_20,
                trailing_pe,forward_pe,sector_avg_pe,
                analyst_target,analyst_upside,analyst_count,
                short_percent,short_ratio,next_earnings,days_until_earnings,
                insider_filings_30d,institutional_pct,top_holder,
                tv_recommendation,tv_rsi,tv_macd,tv_ema_cross,tv_buy,tv_sell)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ticker, today,
             scored["score_revenue"], scored["score_margins"], scored["score_news"],
             scored["score_influencer"], scored["score_momentum"], scored["total_score"],
             scored.get("reasoning", ""),
             scored.get("name", ticker), scored.get("sector", "unknown"),
             scored.get("cap_tier", "large"), int(scored.get("accumulation", False)),
             scored.get("price_change_20", 0.0),
             scored.get("trailing_pe", 0.0), scored.get("forward_pe", 0.0),
             scored.get("sector_avg_pe", 0.0),
             scored.get("analyst_target", 0.0), scored.get("analyst_upside", 0.0),
             scored.get("analyst_count", 0),
             scored.get("short_percent", 0.0), scored.get("short_ratio", 0.0),
             scored.get("next_earnings", "N/A"), scored.get("days_until_earnings"),
             scored.get("insider_filings_30d", 0), scored.get("institutional_pct", 0.0),
             scored.get("top_holder", "N/A"),
             scored.get("tv_recommendation", "N/A"), scored.get("tv_rsi", 50.0),
             scored.get("tv_macd", 0.0), scored.get("tv_ema_cross", 0.0),
             scored.get("tv_buy", 0), scored.get("tv_sell", 0)),
        )
        conn.commit()
        conn.close()
        all_scores.append(scored)

    all_scores.sort(key=lambda x: x["total_score"], reverse=True)

    for s in all_scores[:10]:
        news           = fetch_exa_news(s["name"], s["ticker"], exa_key)
        s["narrative"] = generate_narrative(s, news, anthropic_key)

    generate_html_report(all_scores, str(report_dir / "report.html"),
                         sector_correlations=sector_correlations)
    generate_md_report(all_scores, str(report_dir / "report.md"))
    save_alerts_json(all_scores, str(report_dir / "alerts.json"), threshold)

    for s in all_scores:
        if s["total_score"] >= threshold:
            send_macos_notification(s["ticker"], s["total_score"], s.get("reasoning", ""))
            conn = get_connection(DB_PATH)
            conn.execute(
                "INSERT INTO alerts (ticker,date,alert_type,message,notified) VALUES (?,?,?,?,1)",
                (s["ticker"], today, "score_threshold",
                 f"Score {s['total_score']:.0f}: {s.get('reasoning','')}"),
            )
            conn.commit()
            conn.close()

    if datetime.today().weekday() == 0 and gmail_addr and gmail_pass:
        try:
            send_weekly_email(all_scores, gmail_addr, gmail_pass, alert_email)
            log.info("Weekly email sent.")
        except Exception as e:
            log.error(f"Email error: {e}")

    if all_scores:
        log.info(f"Done. Top: {all_scores[0]['ticker']} {all_scores[0]['total_score']:.0f}")
    log.info(f"Report: {report_dir}/report.html")


if __name__ == "__main__":
    main()
