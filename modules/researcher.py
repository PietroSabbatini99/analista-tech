import feedparser
from exa_py import Exa
from datetime import datetime, timedelta, timezone
from typing import Any


def fetch_exa_news(company_name: str, ticker: str, exa_api_key: str) -> list[dict[str, Any]]:
    exa = Exa(api_key=exa_api_key)
    query = f'"{company_name}" OR "{ticker}" partnership OR revenue OR AI OR acquisition OR earnings'
    start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        result = exa.search_and_contents(
            query,
            num_results=5,
            start_published_date=start_date,
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
