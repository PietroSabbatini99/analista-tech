#!/usr/bin/env python3
import os
import sys
import logging
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
import yaml

from modules.db import init_db, get_connection
from modules.researcher import fetch_x_mentions
from modules.reporter import send_macos_notification

BASE_DIR = Path(__file__).parent
CONFIG   = BASE_DIR / "config.yaml"
DB_PATH  = str(BASE_DIR / "data" / "tech_analyst.db")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "data" / "xscan.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def main():
    load_dotenv(BASE_DIR / ".env", override=True)
    exa_key = os.environ.get("EXA_API_KEY", "")
    if not exa_key:
        log.warning("No EXA_API_KEY — exit")
        return

    with open(CONFIG) as f:
        cfg = yaml.safe_load(f)

    threshold  = int(cfg.get("alerts", {}).get("x_influencer_threshold", 3))
    x_accounts = cfg.get("x_accounts", [])
    companies  = cfg["universe"]["tickers"]
    today      = date.today().isoformat()

    init_db(DB_PATH)

    from modules.memory import Memory
    from modules.news_classifier import classify_news_item, should_alert, build_alert_email
    from modules.researcher import fetch_google_news
    from modules.reporter import send_macos_notification

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    gmail_addr    = os.environ.get("GMAIL_ADDRESS", "")
    gmail_pass    = os.environ.get("GMAIL_APP_PASSWORD", "")
    alert_email   = os.environ.get("ALERT_EMAIL_TO", gmail_addr)
    ngrok_url     = os.environ.get("NGROK_URL", "http://localhost:8080")

    mem = Memory(str(BASE_DIR / "data" / "chromadb"))

    conn = get_connection(DB_PATH)
    score_rows = conn.execute(
        "SELECT ticker, total_score FROM daily_scores WHERE date=?", (today,)
    ).fetchall()
    conn.close()
    ticker_scores = {r["ticker"]: float(r["total_score"]) for r in score_rows}

    for company in companies:
        ticker = company["ticker"]
        name   = company["name"]
        news_items = fetch_google_news(name, ticker, days=1)
        if not news_items or not anthropic_key:
            continue
        for item in news_items:
            classified = classify_news_item(
                item.get("title",""), item.get("snippet",""), api_key=anthropic_key
            )
            item.update(classified)
            item["ticker"] = ticker
            mem.add_news(ticker, [item])
            ts = ticker_scores.get(ticker, 0)
            if should_alert(classified["category"], classified["significance"], ts):
                subject, body = build_alert_email(item, base_url=ngrok_url)
                log.info(f"ALERT: {ticker} — {classified['category']} sig={classified['significance']}")
                send_macos_notification(ticker, classified["significance"]*10, classified["reasoning"])
                if gmail_addr and gmail_pass and alert_email:
                    import smtplib
                    from email.mime.multipart import MIMEMultipart
                    from email.mime.text import MIMEText
                    try:
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = subject
                        msg["From"]    = gmail_addr
                        msg["To"]      = alert_email
                        msg.attach(MIMEText(body, "html"))
                        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                            s.login(gmail_addr, gmail_pass)
                            s.sendmail(gmail_addr, alert_email, msg.as_string())
                        log.info(f"Alert email sent: {ticker}")
                    except Exception as e:
                        log.error(f"Alert email failed: {e}")

    log.info("X scan complete.")


if __name__ == "__main__":
    main()
