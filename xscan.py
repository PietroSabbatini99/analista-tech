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

    for company in companies:
        ticker   = company["ticker"]
        name     = company["name"]
        mentions = fetch_x_mentions(name, ticker, exa_key, x_accounts)

        if len(mentions) >= threshold:
            log.info(f"X signal: {ticker} — {len(mentions)} mentions")
            send_macos_notification(ticker, 0, f"{len(mentions)} influencer mentions on X")
            conn = get_connection(DB_PATH)
            conn.execute(
                "INSERT INTO alerts (ticker,date,alert_type,message,notified) VALUES (?,?,?,?,1)",
                (ticker, today, "x_influencer",
                 f"{len(mentions)} X mentions: {mentions[0]['snippet'][:100]}"),
            )
            conn.commit()
            conn.close()

    log.info("X scan complete.")


if __name__ == "__main__":
    main()
