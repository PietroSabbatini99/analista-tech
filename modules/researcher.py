import json
import subprocess
import feedparser
from exa_py import Exa
from datetime import datetime, timedelta, timezone
from typing import Any

GN_CLI = "/Users/pietrosabbatini/go/bin/google-news-pp-cli"


def fetch_google_news(company_name: str, ticker: str, days: int = 7) -> list[dict[str, Any]]:
    """Fetch news via google-news-pp-cli — free, no API key needed."""
    try:
        result = subprocess.run(
            [GN_CLI, "stock", ticker, "--days", str(days), "--json"],
            capture_output=True, text=True, timeout=25
        )
        if result.returncode == 0 and result.stdout.strip():
            items = json.loads(result.stdout)
            return [
                {
                    "title":   i.get("title", ""),
                    "url":     i.get("url", ""),
                    "date":    i.get("date", ""),
                    "snippet": i.get("snippet", "")[:300],
                    "source":  "google-news",
                }
                for i in items if i.get("title")
            ][:8]
    except Exception:
        pass
    return []


def fetch_exa_news(company_name: str, ticker: str, exa_api_key: str) -> list[dict[str, Any]]:
    """News: Google News CLI primary (free), Exa fallback (uses balance)."""
    items = fetch_google_news(company_name, ticker)
    if items:
        return items
    if not exa_api_key:
        return []
    try:
        exa = Exa(api_key=exa_api_key)
        query = f'"{company_name}" OR "{ticker}" partnership OR revenue OR AI OR acquisition OR earnings'
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = exa.search_and_contents(
            query, num_results=5, start_published_date=start_date,
            text={"max_characters": 300},
        )
        return [
            {
                "title":   r.title or "",
                "url":     r.url or "",
                "date":    r.published_date or "",
                "snippet": (r.text or "")[:300],
                "source":  "exa",
            }
            for r in result.results
        ]
    except Exception:
        return []


def fetch_rss_news(
    company_name: str, ticker: str, feeds: list[dict]
) -> list[dict[str, Any]]:
    keywords = {company_name.lower(), ticker.lower()}
    items = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:20]:
                text = (entry.title + " " + entry.get("summary", "")).lower()
                if any(kw in text for kw in keywords):
                    items.append({
                        "title":   entry.title,
                        "url":     entry.link,
                        "date":    entry.get("published", ""),
                        "snippet": entry.get("summary", "")[:300],
                        "source":  feed["name"],
                    })
        except Exception:
            continue
    return items


def fetch_x_mentions(
    company_name: str,
    ticker: str,
    exa_api_key: str,
    accounts: list[str],
) -> list[dict[str, Any]]:
    exa = Exa(api_key=exa_api_key)
    account_filter = " OR ".join(f"site:x.com/{a}" for a in accounts[:10])
    query = f'({company_name} OR ${ticker}) ({account_filter})'
    start_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        result = exa.search_and_contents(
            query,
            num_results=10,
            start_published_date=start_date,
            text={"max_characters": 300},
        )
        return [
            {
                "title":   r.title or "",
                "url":     r.url or "",
                "date":    r.published_date or "",
                "snippet": (r.text or "")[:300],
                "source":  "x",
            }
            for r in result.results
        ]
    except Exception:
        return []
