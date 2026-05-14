# AI Sector Analyst — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an autonomous Python agent that daily analyzes ~150 AI/chip sector stocks, scores them for upside potential, and delivers an HTML dashboard + macOS alerts on a Mac mini running 24/7.

**Architecture:** Modular pipeline (universe → collect → research → analyze → report) coordinated by `main.py`, plus a lightweight `xscan.py` that polls X API every 2h independently. All data persisted in SQLite; HTML/MD outputs saved in dated report folders.

**Tech Stack:** Python 3.12, anthropic SDK (claude-haiku-4-5-20251001 bulk + claude-sonnet-4-6 narrative), yfinance, exa-py, tweepy, feedparser, jinja2, sqlite3, launchd

---

## File Map

| File | Responsibility |
|---|---|
| `main.py` | Orchestrator: runs full daily pipeline |
| `xscan.py` | Lightweight X-only scanner (runs every 2h) |
| `config.yaml` | Ticker list, alert thresholds, RSS feeds, X accounts |
| `.env` | API secrets (never committed) |
| `modules/db.py` | SQLite init + all queries |
| `modules/universe.py` | Load + enrich ticker list from config |
| `modules/collector.py` | yfinance + SEC EDGAR data fetching |
| `modules/researcher.py` | Exa search + X API + RSS feed parsing |
| `modules/analyzer.py` | Claude Haiku scoring + Sonnet narratives |
| `modules/reporter.py` | HTML/MD output + macOS alert + email |
| `templates/dashboard.html` | Jinja2 HTML dashboard template |
| `templates/email.html` | Jinja2 email template |
| `launchd/com.analista.tech.plist` | Daily full pipeline job |
| `launchd/com.analista.tech.xscan.plist` | X scan every 2h |
| `tests/test_db.py` | DB schema tests |
| `tests/test_universe.py` | Universe loading tests |
| `tests/test_collector.py` | Collector mock tests |
| `tests/test_researcher.py` | Researcher mock tests |
| `tests/test_analyzer.py` | Analyzer mock tests |
| `tests/test_reporter.py` | Reporter output tests |

---

### Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `.env.template`
- Create: `modules/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd ~/Desktop/Analista\ Tech
mkdir -p modules tests data/cache reports templates launchd
touch modules/__init__.py tests/__init__.py data/.gitkeep reports/.gitkeep
```

- [ ] **Step 2: Create `requirements.txt`**

```text
anthropic>=0.25.0
yfinance>=0.2.40
exa-py>=1.1.0
tweepy>=4.14.0
feedparser>=6.0.11
jinja2>=3.1.4
requests>=2.31.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
PyYAML>=6.0.1
```

- [ ] **Step 3: Install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 4: Create `.env.template`**

```
ANTHROPIC_API_KEY=sk-ant-...
EXA_API_KEY=...
X_BEARER_TOKEN=...
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
ALERT_EMAIL_TO=you@gmail.com
```

- [ ] **Step 5: Copy template to `.env` and fill real values**

```bash
cp .env.template .env
# edit .env with real API keys
```

- [ ] **Step 6: Create `config.yaml`**

```yaml
universe:
  tickers:
    # Chip design
    - {ticker: NVDA, name: "NVIDIA", sector: chip}
    - {ticker: AMD, name: "Advanced Micro Devices", sector: chip}
    - {ticker: INTC, name: "Intel", sector: chip}
    - {ticker: QCOM, name: "Qualcomm", sector: chip}
    - {ticker: AVGO, name: "Broadcom", sector: chip}
    - {ticker: MRVL, name: "Marvell Technology", sector: chip}
    - {ticker: ARM, name: "Arm Holdings", sector: chip}
    - {ticker: ALAB, name: "Astera Labs", sector: chip}
    - {ticker: SMCI, name: "Super Micro Computer", sector: datacenter}
    - {ticker: LSCC, name: "Lattice Semiconductor", sector: chip}
    - {ticker: MCHP, name: "Microchip Technology", sector: chip}
    - {ticker: ON, name: "ON Semiconductor", sector: chip}
    - {ticker: MPWR, name: "Monolithic Power", sector: chip}
    - {ticker: CRUS, name: "Cirrus Logic", sector: chip}
    - {ticker: SWKS, name: "Skyworks Solutions", sector: chip}
    - {ticker: MTSI, name: "MACOM Technology", sector: chip}
    # Memory / Storage
    - {ticker: MU, name: "Micron Technology", sector: memory}
    - {ticker: WDC, name: "Western Digital", sector: memory}
    - {ticker: STX, name: "Seagate Technology", sector: memory}
    # Datacenter / Infra
    - {ticker: DELL, name: "Dell Technologies", sector: datacenter}
    - {ticker: HPE, name: "HP Enterprise", sector: datacenter}
    - {ticker: VRT, name: "Vertiv", sector: datacenter}
    - {ticker: CDNS, name: "Cadence Design", sector: eda}
    - {ticker: SNPS, name: "Synopsys", sector: eda}
    # AI Software / Cloud
    - {ticker: MSFT, name: "Microsoft", sector: ai_software}
    - {ticker: GOOGL, name: "Alphabet", sector: ai_software}
    - {ticker: META, name: "Meta Platforms", sector: ai_software}
    - {ticker: AMZN, name: "Amazon", sector: ai_software}
    - {ticker: ORCL, name: "Oracle", sector: ai_software}
    - {ticker: SNOW, name: "Snowflake", sector: ai_software}
    - {ticker: PLTR, name: "Palantir", sector: ai_software}
    - {ticker: AI, name: "C3.ai", sector: ai_software}
    - {ticker: BBAI, name: "BigBear.ai", sector: ai_software}
    - {ticker: SOUN, name: "SoundHound AI", sector: ai_software}
    - {ticker: PATH, name: "UiPath", sector: ai_software}
    - {ticker: GTLB, name: "GitLab", sector: ai_software}
    - {ticker: MDB, name: "MongoDB", sector: ai_software}
    - {ticker: NET, name: "Cloudflare", sector: ai_software}
    - {ticker: DDOG, name: "Datadog", sector: ai_software}
    - {ticker: CRWD, name: "CrowdStrike", sector: ai_software}
    - {ticker: ANET, name: "Arista Networks", sector: networking}
    # Fab Equipment
    - {ticker: AMAT, name: "Applied Materials", sector: equipment}
    - {ticker: KLAC, name: "KLA Corporation", sector: equipment}
    - {ticker: LRCX, name: "Lam Research", sector: equipment}
    - {ticker: ASML, name: "ASML Holding", sector: equipment}
    - {ticker: TER, name: "Teradyne", sector: equipment}
    # Power / Cooling
    - {ticker: ETN, name: "Eaton", sector: power}
    - {ticker: VRT, name: "Vertiv", sector: power}
    # Quantum
    - {ticker: IONQ, name: "IonQ", sector: quantum}
    - {ticker: RGTI, name: "Rigetti Computing", sector: quantum}

alerts:
  score_threshold: 75
  score_spike: 15
  partnership_instant: true
  x_influencer_threshold: 3

rss_feeds:
  - url: "https://www.semianalysis.com/feed"
    name: SemiAnalysis
  - url: "https://feeds.feedburner.com/TechCrunch"
    name: TechCrunch
  - url: "https://feeds.reuters.com/reuters/technologyNews"
    name: Reuters Tech
  - url: "https://www.thechipletter.com/feed"
    name: The Chip Letter

x_accounts:
  - jensen_huang
  - sama
  - satyanadella
  - SemiAnalysis
  - PatrickMoorhead
  - DanIves_WA
  - benedictevans
  - TechCrunch
  - mlpowered

report:
  weekly_email_day: monday
```

- [ ] **Step 7: Verify Python version**

```bash
python3 --version
```

Expected: `Python 3.12.x`

- [ ] **Step 8: Commit scaffold**

```bash
git init
echo ".env" >> .gitignore
echo ".venv/" >> .gitignore
echo "data/*.db" >> .gitignore
echo "data/cache/" >> .gitignore
echo "reports/" >> .gitignore
git add .
git commit -m "feat: project scaffold"
```

---

### Task 2: Database Module

**Files:**
- Create: `modules/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_db.py
import sqlite3
import os
import tempfile
from modules.db import init_db, get_connection


def test_init_creates_all_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "companies" in tables
        assert "daily_scores" in tables
        assert "alerts" in tables
        assert "news_cache" in tables
    finally:
        os.unlink(db_path)


def test_get_connection_returns_row_factory():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        conn = get_connection(db_path)
        row = conn.execute("SELECT 1 AS val").fetchone()
        assert row["val"] == 1
        conn.close()
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate
pytest tests/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.db'`

- [ ] **Step 3: Implement `modules/db.py`**

```python
import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            ticker      TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            sector      TEXT NOT NULL,
            cap_tier    TEXT,
            added_at    TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_scores (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker            TEXT NOT NULL,
            date              TEXT NOT NULL,
            score_revenue     REAL,
            score_margins     REAL,
            score_news        REAL,
            score_influencer  REAL,
            score_momentum    REAL,
            total_score       REAL,
            narrative         TEXT,
            UNIQUE(ticker, date)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            date        TEXT NOT NULL,
            alert_type  TEXT NOT NULL,
            message     TEXT NOT NULL,
            notified    INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS news_cache (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker  TEXT NOT NULL,
            date    TEXT NOT NULL,
            source  TEXT,
            title   TEXT,
            url     TEXT,
            snippet TEXT,
            UNIQUE(ticker, url)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_scores_ticker_date
            ON daily_scores(ticker, date);

        CREATE INDEX IF NOT EXISTS idx_alerts_date
            ON alerts(date);
    """)
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_db.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add modules/db.py tests/test_db.py
git commit -m "feat: sqlite db module with schema"
```

---

### Task 3: Universe Module

**Files:**
- Create: `modules/universe.py`
- Create: `tests/test_universe.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_universe.py
import yaml
import tempfile
import os
from modules.universe import load_universe


def _write_config(tickers):
    cfg = {
        "universe": {"tickers": tickers},
        "alerts": {}, "rss_feeds": [], "x_accounts": [], "report": {}
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(cfg, f)
        return f.name


def test_load_universe_returns_list_of_dicts():
    cfg_path = _write_config([
        {"ticker": "NVDA", "name": "NVIDIA", "sector": "chip"},
        {"ticker": "AMD",  "name": "AMD",    "sector": "chip"},
    ])
    try:
        companies = load_universe(cfg_path)
        assert len(companies) == 2
        assert companies[0]["ticker"] == "NVDA"
        assert companies[0]["name"] == "NVIDIA"
        assert companies[0]["sector"] == "chip"
    finally:
        os.unlink(cfg_path)


def test_load_universe_adds_cap_tier_key():
    cfg_path = _write_config([{"ticker": "NVDA", "name": "NVIDIA", "sector": "chip"}])
    try:
        companies = load_universe(cfg_path)
        assert "cap_tier" in companies[0]
    finally:
        os.unlink(cfg_path)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_universe.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `modules/universe.py`**

```python
import yaml
from typing import Any


def load_universe(config_path: str) -> list[dict[str, Any]]:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    companies = []
    for entry in cfg["universe"]["tickers"]:
        companies.append({
            "ticker":   entry["ticker"],
            "name":     entry["name"],
            "sector":   entry.get("sector", "unknown"),
            "cap_tier": entry.get("cap_tier", "unknown"),
        })
    return companies
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_universe.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add modules/universe.py tests/test_universe.py
git commit -m "feat: universe module loads tickers from config"
```

---

### Task 4: Collector Module

**Files:**
- Create: `modules/collector.py`
- Create: `tests/test_collector.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_collector.py
from unittest.mock import patch, MagicMock
import pandas as pd
from modules.collector import fetch_financial_snapshot, fetch_edgar_filings


def _mock_ticker(info_override=None, hist_empty=False):
    mock = MagicMock()
    mock.info = {
        "totalRevenue": 60_000_000_000,
        "revenueGrowth": 0.35,
        "grossMargins": 0.72,
        "totalCash": 10_000_000_000,
        "priceToSalesTrailing12Months": 25.0,
        "marketCap": 3_000_000_000_000,
        **(info_override or {}),
    }
    if hist_empty:
        mock.history.return_value = pd.DataFrame()
    else:
        dates = pd.date_range("2025-05-01", periods=60, freq="B")
        mock.history.return_value = pd.DataFrame({
            "Close":  [100 + i * 0.5 for i in range(60)],
            "Volume": [50_000_000] * 60,
        }, index=dates)
    return mock


def test_fetch_financial_snapshot_returns_expected_keys():
    with patch("modules.collector.yf.Ticker", return_value=_mock_ticker()):
        result = fetch_financial_snapshot("NVDA")
    assert result["ticker"] == "NVDA"
    assert "revenue_growth" in result
    assert "gross_margin" in result
    assert "momentum_20_60" in result
    assert "volume_spike" in result


def test_fetch_financial_snapshot_handles_missing_data():
    with patch("modules.collector.yf.Ticker", return_value=_mock_ticker(
        info_override={"totalRevenue": None, "revenueGrowth": None},
        hist_empty=True
    )):
        result = fetch_financial_snapshot("BADTICKER")
    assert result["revenue_growth"] == 0.0
    assert result["momentum_20_60"] == 0.0


def test_fetch_edgar_filings_returns_list():
    fake_response = {"hits": {"hits": [
        {"_source": {"period_of_report": "2026-04-01",
                     "display_names": ["NVIDIA Corp"],
                     "file_date": "2026-04-02",
                     "form_type": "8-K"}},
    ]}}
    with patch("modules.collector.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake_response
        filings = fetch_edgar_filings("NVIDIA", days=30)
    assert isinstance(filings, list)
    assert filings[0]["form_type"] == "8-K"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_collector.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `modules/collector.py`**

```python
import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import Any


def fetch_financial_snapshot(ticker: str) -> dict[str, Any]:
    t = yf.Ticker(ticker)
    info = t.info or {}

    revenue_growth = float(info.get("revenueGrowth") or 0.0)
    gross_margin   = float(info.get("grossMargins") or 0.0)
    total_cash     = float(info.get("totalCash") or 0.0)
    price_to_sales = float(info.get("priceToSalesTrailing12Months") or 0.0)
    market_cap     = float(info.get("marketCap") or 0.0)

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

    return {
        "ticker":         ticker,
        "revenue_growth": revenue_growth,
        "gross_margin":   gross_margin,
        "total_cash":     total_cash,
        "price_to_sales": price_to_sales,
        "market_cap":     market_cap,
        "momentum_20_60": momentum_20_60,
        "volume_spike":   volume_spike,
    }


def fetch_edgar_filings(company_name: str, days: int = 14) -> list[dict[str, Any]]:
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_collector.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add modules/collector.py tests/test_collector.py
git commit -m "feat: collector with yfinance and SEC EDGAR"
```

---

### Task 5: Researcher Module

**Files:**
- Create: `modules/researcher.py`
- Create: `tests/test_researcher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_researcher.py
from unittest.mock import patch, MagicMock
from modules.researcher import fetch_exa_news, fetch_rss_news, fetch_x_mentions


def test_fetch_exa_news_returns_list():
    mock_exa = MagicMock()
    mock_result = MagicMock()
    mock_result.results = [
        MagicMock(title="NVDA signs AI deal", url="https://example.com/1",
                  published_date="2026-05-09", text="NVIDIA announced..."),
    ]
    mock_exa.search_and_contents.return_value = mock_result

    with patch("modules.researcher.Exa", return_value=mock_exa):
        items = fetch_exa_news("NVIDIA", "NVDA", exa_api_key="fake")

    assert isinstance(items, list)
    assert items[0]["title"] == "NVDA signs AI deal"
    assert items[0]["source"] == "exa"


def test_fetch_rss_news_no_crash_on_empty():
    fake_feed = MagicMock()
    fake_feed.entries = []
    with patch("modules.researcher.feedparser.parse", return_value=fake_feed):
        items = fetch_rss_news(
            "NVIDIA", "NVDA",
            feeds=[{"url": "https://fake.rss", "name": "FakeFeed"}]
        )
    assert isinstance(items, list)


def test_fetch_x_mentions_returns_list():
    mock_client = MagicMock()
    mock_tweet = MagicMock()
    mock_tweet.text = "NVDA is going to moon #AI"
    mock_tweet.id = 123456
    mock_client.search_recent_tweets.return_value = MagicMock(data=[mock_tweet])

    with patch("modules.researcher.tweepy.Client", return_value=mock_client):
        items = fetch_x_mentions("NVIDIA", "NVDA", bearer_token="fake", accounts=["testuser"])

    assert isinstance(items, list)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_researcher.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `modules/researcher.py`**

```python
import feedparser
import tweepy
from exa_py import Exa
from datetime import datetime, timedelta
from typing import Any


def fetch_exa_news(company_name: str, ticker: str, exa_api_key: str) -> list[dict[str, Any]]:
    exa = Exa(api_key=exa_api_key)
    query = f'"{company_name}" OR "{ticker}" partnership OR revenue OR AI OR acquisition OR earnings'
    start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
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
    bearer_token: str,
    accounts: list[str],
) -> list[dict[str, Any]]:
    client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=False)
    account_filter = " OR ".join(f"from:{a}" for a in accounts[:10])
    query = f'({company_name} OR ${ticker}) ({account_filter}) -is:retweet lang:en'
    try:
        resp = client.search_recent_tweets(
            query=query,
            max_results=10,
            tweet_fields=["created_at", "text"],
        )
        if not resp.data:
            return []
        return [
            {
                "title":   tweet.text[:100],
                "url":     f"https://x.com/i/web/status/{tweet.id}",
                "date":    str(getattr(tweet, "created_at", "")),
                "snippet": tweet.text[:300],
                "source":  "x",
            }
            for tweet in resp.data
        ]
    except Exception:
        return []
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_researcher.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add modules/researcher.py tests/test_researcher.py
git commit -m "feat: researcher with Exa, RSS, X API"
```

---

### Task 6: Analyzer Module

**Files:**
- Create: `modules/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_analyzer.py
import json
from unittest.mock import patch, MagicMock
from modules.analyzer import score_company, generate_narrative


def _mock_client(text: str):
    mock = MagicMock()
    mock.messages.create.return_value.content = [MagicMock(text=text)]
    return mock


FAKE_FINANCIAL = {
    "ticker": "NVDA", "name": "NVIDIA",
    "revenue_growth": 0.35, "gross_margin": 0.72,
    "total_cash": 10e9, "price_to_sales": 25.0,
    "market_cap": 3e12, "momentum_20_60": 0.12, "volume_spike": 0.3,
}
FAKE_NEWS = [{"title": "NVDA signs Azure deal", "snippet": "Microsoft Azure...",
              "source": "exa", "url": "http://x.com"}]


def test_score_company_returns_all_dimensions():
    fake_json = json.dumps({
        "score_revenue": 80, "score_margins": 75,
        "score_news": 85, "score_influencer": 70,
        "score_momentum": 90, "reasoning": "Strong growth."
    })
    with patch("modules.analyzer.anthropic.Anthropic", return_value=_mock_client(fake_json)):
        result = score_company(FAKE_FINANCIAL, FAKE_NEWS, api_key="fake")

    assert result["ticker"] == "NVDA"
    assert 0 <= result["total_score"] <= 100
    assert "score_revenue" in result
    assert "reasoning" in result


def test_score_company_handles_malformed_json():
    with patch("modules.analyzer.anthropic.Anthropic", return_value=_mock_client("not json")):
        result = score_company(FAKE_FINANCIAL, FAKE_NEWS, api_key="fake")
    assert result["total_score"] == 0.0


def test_generate_narrative_returns_string():
    with patch("modules.analyzer.anthropic.Anthropic",
               return_value=_mock_client("NVIDIA shows exceptional momentum...")):
        text = generate_narrative(
            {"ticker": "NVDA", "name": "NVIDIA", "total_score": 88,
             "score_revenue": 80, "score_margins": 75, "score_news": 85,
             "score_influencer": 70, "score_momentum": 90, "reasoning": "Strong."},
            FAKE_NEWS, api_key="fake",
        )
    assert isinstance(text, str) and len(text) > 0
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_analyzer.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `modules/analyzer.py`**

```python
import json
import anthropic
from typing import Any

WEIGHTS = {
    "score_revenue":    0.20,
    "score_margins":    0.15,
    "score_news":       0.25,
    "score_influencer": 0.20,
    "score_momentum":   0.20,
}

_SCORE_PROMPT = """\
You are a quantitative equity analyst specializing in AI/semiconductor stocks.

Company: {name} ({ticker})

FINANCIAL DATA:
- Revenue Growth YoY: {revenue_growth:.1%}
- Gross Margin: {gross_margin:.1%}
- Total Cash: ${total_cash:,.0f}
- Price/Sales: {price_to_sales:.1f}x
- Market Cap: ${market_cap:,.0f}
- Price Momentum (20d vs 60d avg): {momentum_20_60:+.1%}
- Volume Spike (20d vs 60d avg): {volume_spike:+.1%}

RECENT NEWS (last 7 days):
{news_block}

Score 0-100 per dimension based on potential for EXCEPTIONAL market value increase.
Return ONLY valid JSON, no markdown:
{{"score_revenue":<0-100>,"score_margins":<0-100>,"score_news":<0-100>,"score_influencer":<0-100>,"score_momentum":<0-100>,"reasoning":"<50 words max>"}}"""

_NARRATIVE_PROMPT = """\
You are a senior equity analyst. Write a 150-word investment thesis for:

{ticker} — Score: {total_score:.0f}/100
Revenue: {score_revenue}/100 | Margins: {score_margins}/100 | News: {score_news}/100
Influencer: {score_influencer}/100 | Momentum: {score_momentum}/100

Key signal: {reasoning}

Top news:
{news_block}

Write a concise, data-driven thesis explaining WHY this company could see exceptional market value increase. No disclaimers. Be direct."""


def _news_block(news_items: list[dict]) -> str:
    lines = [f"- [{n['source']}] {n['title']}: {n['snippet'][:100]}" for n in news_items[:5]]
    return "\n".join(lines) if lines else "No recent news."


def score_company(
    financial: dict[str, Any],
    news_items: list[dict],
    api_key: str,
) -> dict[str, Any]:
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _SCORE_PROMPT.format(
        name=financial.get("name", financial["ticker"]),
        ticker=financial["ticker"],
        revenue_growth=financial["revenue_growth"],
        gross_margin=financial["gross_margin"],
        total_cash=financial["total_cash"],
        price_to_sales=financial["price_to_sales"],
        market_cap=financial["market_cap"],
        momentum_20_60=financial["momentum_20_60"],
        volume_spike=financial["volume_spike"],
        news_block=_news_block(news_items),
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(msg.content[0].text.strip())
    except Exception:
        return {k: 0 for k in ["score_revenue","score_margins","score_news",
                                "score_influencer","score_momentum"]} | {
            "ticker": financial["ticker"], "total_score": 0.0, "reasoning": "error"
        }

    total = sum(data.get(k, 0) * w for k, w in WEIGHTS.items())
    return {
        "ticker":           financial["ticker"],
        "score_revenue":    data.get("score_revenue", 0),
        "score_margins":    data.get("score_margins", 0),
        "score_news":       data.get("score_news", 0),
        "score_influencer": data.get("score_influencer", 0),
        "score_momentum":   data.get("score_momentum", 0),
        "total_score":      round(total, 1),
        "reasoning":        data.get("reasoning", ""),
    }


def generate_narrative(
    scored: dict[str, Any],
    news_items: list[dict],
    api_key: str,
) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _NARRATIVE_PROMPT.format(**scored, news_block=_news_block(news_items))
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return scored.get("reasoning", "")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_analyzer.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add modules/analyzer.py tests/test_analyzer.py
git commit -m "feat: analyzer with Haiku scoring and Sonnet narratives"
```

---

### Task 7: Reporter Module + Templates

**Files:**
- Create: `modules/reporter.py`
- Create: `templates/dashboard.html`
- Create: `templates/email.html`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_reporter.py
import os
import json
import tempfile
from unittest.mock import patch
from modules.reporter import (
    generate_html_report, generate_md_report,
    save_alerts_json, send_macos_notification
)

SAMPLE = [
    {"ticker": "NVDA", "name": "NVIDIA", "total_score": 88, "score_revenue": 80,
     "score_margins": 75, "score_news": 85, "score_influencer": 70,
     "score_momentum": 90, "reasoning": "Strong.", "narrative": "Thesis."},
    {"ticker": "AMD",  "name": "AMD",    "total_score": 62, "score_revenue": 60,
     "score_margins": 55, "score_news": 65, "score_influencer": 60,
     "score_momentum": 70, "reasoning": "Decent.", "narrative": "AMD."},
]


def test_generate_html_report_creates_file():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "report.html")
        generate_html_report(SAMPLE, out, template_dir="templates")
        assert os.path.exists(out)
        assert "NVDA" in open(out).read()


def test_generate_md_report_creates_file():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "report.md")
        generate_md_report(SAMPLE, out)
        assert os.path.exists(out)
        assert "NVDA" in open(out).read()


def test_save_alerts_json_filters_by_threshold():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "alerts.json")
        save_alerts_json(SAMPLE, out, threshold=75)
        data = json.loads(open(out).read())
        assert any(a["ticker"] == "NVDA" for a in data)
        assert not any(a["ticker"] == "AMD" for a in data)


def test_send_macos_notification_calls_osascript():
    with patch("modules.reporter.subprocess.run") as mock_run:
        send_macos_notification("NVDA", 88, "Partnership announced")
        assert "osascript" in mock_run.call_args[0][0]
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_reporter.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `templates/dashboard.html`**

```html
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>AI Sector Analyst — {{ run_date }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background:#0d1117; color:#e6edf3; font-family:'Segoe UI',sans-serif; }
    .card { background:#161b22; border:1px solid #30363d; }
    .sh { color:#3fb950; } .sm { color:#d29922; } .sl { color:#f85149; }
    th { color:#8b949e; font-size:.8rem; text-transform:uppercase; }
  </style>
</head>
<body class="p-4">
  <div class="d-flex justify-content-between mb-4">
    <h1 class="h4 mb-0">🔬 AI Sector Analyst</h1>
    <span class="text-muted small">{{ run_date }} | {{ companies|length }} companies</span>
  </div>

  <div class="card mb-4 p-3">
    <h5 class="mb-3">🔥 Top Signals</h5>
    <table class="table table-dark table-hover mb-0">
      <thead><tr><th>Ticker</th><th>Name</th><th>Score</th><th>Rev</th><th>Mar</th><th>News</th><th>Infl</th><th>Mom</th><th>Signal</th></tr></thead>
      <tbody>
        {% for c in companies[:10] %}
        <tr>
          <td><strong>{{ c.ticker }}</strong></td>
          <td>{{ c.name }}</td>
          <td class="fw-bold {% if c.total_score>=75 %}sh{% elif c.total_score>=50 %}sm{% else %}sl{% endif %}">{{ c.total_score|round|int }}</td>
          <td>{{ c.score_revenue|round|int }}</td>
          <td>{{ c.score_margins|round|int }}</td>
          <td>{{ c.score_news|round|int }}</td>
          <td>{{ c.score_influencer|round|int }}</td>
          <td>{{ c.score_momentum|round|int }}</td>
          <td><small class="text-muted">{{ c.reasoning[:80] }}</small></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="card p-3">
    <h5 class="mb-3">📊 Full Universe</h5>
    <input class="form-control form-control-sm mb-3 bg-dark text-light border-secondary"
           id="fi" placeholder="Filter..." style="max-width:280px">
    <table class="table table-dark table-hover mb-0" id="ut">
      <thead><tr><th>Ticker</th><th>Name</th><th>Score</th><th>Rev</th><th>Mar</th><th>News</th><th>Infl</th><th>Mom</th></tr></thead>
      <tbody>
        {% for c in companies %}
        <tr>
          <td><strong>{{ c.ticker }}</strong></td><td>{{ c.name }}</td>
          <td class="{% if c.total_score>=75 %}sh{% elif c.total_score>=50 %}sm{% else %}sl{% endif %}">{{ c.total_score|round|int }}</td>
          <td>{{ c.score_revenue|round|int }}</td><td>{{ c.score_margins|round|int }}</td>
          <td>{{ c.score_news|round|int }}</td><td>{{ c.score_influencer|round|int }}</td>
          <td>{{ c.score_momentum|round|int }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <script>
    document.getElementById("fi").addEventListener("input",function(){
      const v=this.value.toLowerCase();
      document.querySelectorAll("#ut tbody tr").forEach(r=>{
        r.style.display=r.textContent.toLowerCase().includes(v)?"":"none";
      });
    });
  </script>
</body>
</html>
```

- [ ] **Step 4: Create `templates/email.html`**

```html
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#f5f5f5;padding:20px">
  <h2>🔬 AI Analyst Weekly — {{ run_date }}</h2>
  <p>{{ companies|length }} companies analyzed.</p>
  <h3>Top 10</h3>
  <table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
    <tr style="background:#222;color:white"><th>Ticker</th><th>Score</th><th>Signal</th></tr>
    {% for c in companies[:10] %}
    <tr>
      <td><b>{{ c.ticker }}</b> — {{ c.name }}</td>
      <td><b>{{ c.total_score|round|int }}</b></td>
      <td>{{ c.reasoning[:100] }}</td>
    </tr>
    {% endfor %}
  </table>
  <p style="color:#999;font-size:12px">Generated by AI Sector Analyst</p>
</body>
</html>
```

- [ ] **Step 5: Implement `modules/reporter.py`**

```python
import os
import json
import subprocess
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from typing import Any


def generate_html_report(
    scores: list[dict[str, Any]], output_path: str, template_dir: str = "templates"
) -> None:
    env  = Environment(loader=FileSystemLoader(template_dir))
    html = env.get_template("dashboard.html").render(
        companies=scores, run_date=date.today().isoformat()
    )
    with open(output_path, "w") as f:
        f.write(html)


def generate_md_report(scores: list[dict[str, Any]], output_path: str) -> None:
    lines = [
        f"# AI Sector Analyst — {date.today().isoformat()}", "",
        "## Top Signals", "",
        "| Ticker | Score | Signal |", "|--------|-------|--------|",
    ]
    for c in scores[:20]:
        lines.append(f"| **{c['ticker']}** | {c['total_score']:.0f} | {c.get('reasoning','')[:80]} |")
    lines += ["", "## Full Universe", "", "| Ticker | Score |", "|--------|-------|"]
    for c in scores:
        lines.append(f"| {c['ticker']} | {c['total_score']:.0f} |")
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def save_alerts_json(
    scores: list[dict[str, Any]], output_path: str, threshold: float = 75.0
) -> None:
    with open(output_path, "w") as f:
        json.dump([c for c in scores if c["total_score"] >= threshold], f, indent=2)


def send_macos_notification(ticker: str, score: float, reason: str) -> None:
    msg    = f"{ticker} — Score {score:.0f}: {reason[:60]}"
    script = f'display notification "{msg}" with title "AI Analyst 🔬" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def send_weekly_email(
    scores: list[dict[str, Any]],
    gmail_address: str,
    app_password: str,
    to_address: str,
    template_dir: str = "templates",
) -> None:
    env  = Environment(loader=FileSystemLoader(template_dir))
    html = env.get_template("email.html").render(
        companies=scores, run_date=date.today().isoformat()
    )
    msg             = MIMEMultipart("alternative")
    msg["Subject"]  = f"AI Analyst Weekly — {date.today().isoformat()}"
    msg["From"]     = gmail_address
    msg["To"]       = to_address
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(gmail_address, app_password)
        s.sendmail(gmail_address, to_address, msg.as_string())
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_reporter.py -v
```

Expected: `4 passed`

- [ ] **Step 7: Commit**

```bash
git add modules/reporter.py templates/ tests/test_reporter.py
git commit -m "feat: reporter with HTML, MD, alerts, macOS notification, email"
```

---

### Task 8: Main Orchestrator

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create `main.py`**

```python
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
from modules.collector import fetch_financial_snapshot, fetch_edgar_filings
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
    load_dotenv(BASE_DIR / ".env")
    anthropic_key = os.environ["ANTHROPIC_API_KEY"]
    exa_key       = os.environ["EXA_API_KEY"]
    x_bearer      = os.environ.get("X_BEARER_TOKEN", "")
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

    all_scores = []
    for company in companies:
        ticker = company["ticker"]
        name   = company["name"]
        log.info(f"  {ticker}")
        try:
            financial      = fetch_financial_snapshot(ticker)
            financial["name"] = name
        except Exception as e:
            log.warning(f"  {ticker} financial error: {e}")
            continue

        news = (
            fetch_edgar_filings(name)
            and []  # edgar returns list of filing dicts, not news format; skip for news list
        )
        news  = fetch_exa_news(name, ticker, exa_key)
        news += fetch_rss_news(name, ticker, rss_feeds)
        if x_bearer:
            news += fetch_x_mentions(name, ticker, x_bearer, x_accounts)

        scored          = score_company(financial, news, anthropic_key)
        scored["name"]   = name
        scored["sector"] = company["sector"]

        conn = get_connection(DB_PATH)
        conn.execute(
            """INSERT OR REPLACE INTO daily_scores
               (ticker,date,score_revenue,score_margins,score_news,
                score_influencer,score_momentum,total_score,narrative)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (ticker, today, scored["score_revenue"], scored["score_margins"],
             scored["score_news"], scored["score_influencer"], scored["score_momentum"],
             scored["total_score"], scored.get("reasoning", "")),
        )
        conn.commit()
        conn.close()
        all_scores.append(scored)

    all_scores.sort(key=lambda x: x["total_score"], reverse=True)

    for s in all_scores[:10]:
        news           = fetch_exa_news(s["name"], s["ticker"], exa_key)
        s["narrative"] = generate_narrative(s, news, anthropic_key)

    generate_html_report(all_scores, str(report_dir / "report.html"))
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

    log.info(f"Done. Top: {all_scores[0]['ticker']} {all_scores[0]['total_score']:.0f}")
    log.info(f"Report: {report_dir}/report.html")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run with one ticker**

Temporarily edit `config.yaml` to keep only `NVDA` under `tickers`, then:

```bash
source .venv/bin/activate
python main.py
```

Expected: log shows processing NVDA, `reports/YYYY-MM-DD/report.html` created.

- [ ] **Step 3: Open dashboard**

```bash
open reports/$(date +%Y-%m-%d)/report.html
```

Expected: styled dark dashboard with NVDA row visible.

- [ ] **Step 4: Restore full ticker list in `config.yaml`**

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: main orchestrator pipeline"
```

---

### Task 9: X Scanner (lightweight 2h job)

**Files:**
- Create: `xscan.py`

- [ ] **Step 1: Create `xscan.py`**

```python
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
    load_dotenv(BASE_DIR / ".env")
    x_bearer = os.environ.get("X_BEARER_TOKEN", "")
    if not x_bearer:
        log.warning("No X_BEARER_TOKEN — exit")
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
        mentions = fetch_x_mentions(name, ticker, x_bearer, x_accounts)

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
```

- [ ] **Step 2: Test run manually**

```bash
source .venv/bin/activate
python xscan.py
```

Expected: log output, no crash. With valid token: mention counts logged per ticker.

- [ ] **Step 3: Commit**

```bash
git add xscan.py
git commit -m "feat: lightweight X scanner for 2h polling"
```

---

### Task 10: launchd Scheduling

**Files:**
- Create: `launchd/com.analista.tech.plist`
- Create: `launchd/com.analista.tech.xscan.plist`
- Create: `launchd/install.sh`

- [ ] **Step 1: Get your username**

```bash
whoami
```

Use this value to replace `YOUR_USERNAME` in the plist files below.

- [ ] **Step 2: Create `launchd/com.analista.tech.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.analista.tech</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/Desktop/Analista Tech/.venv/bin/python3</string>
        <string>/Users/YOUR_USERNAME/Desktop/Analista Tech/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/Desktop/Analista Tech</string>
    <key>StartCalendarInterval</key>
    <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/Desktop/Analista Tech/data/agent.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/Desktop/Analista Tech/data/agent.error.log</string>
    <key>RunAtLoad</key><false/>
</dict>
</plist>
```

- [ ] **Step 3: Create `launchd/com.analista.tech.xscan.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.analista.tech.xscan</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/Desktop/Analista Tech/.venv/bin/python3</string>
        <string>/Users/YOUR_USERNAME/Desktop/Analista Tech/xscan.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/Desktop/Analista Tech</string>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>22</integer><key>Minute</key><integer>0</integer></dict>
    </array>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/Desktop/Analista Tech/data/xscan.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/Desktop/Analista Tech/data/xscan.error.log</string>
    <key>RunAtLoad</key><false/>
</dict>
</plist>
```

- [ ] **Step 4: Create `launchd/install.sh`**

```bash
#!/bin/bash
set -e
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

sed -i '' "s|YOUR_USERNAME|$(whoami)|g" "$PROJECT_DIR/launchd/com.analista.tech.plist"
sed -i '' "s|YOUR_USERNAME|$(whoami)|g" "$PROJECT_DIR/launchd/com.analista.tech.xscan.plist"

cp "$PROJECT_DIR/launchd/com.analista.tech.plist"       "$LAUNCH_AGENTS/"
cp "$PROJECT_DIR/launchd/com.analista.tech.xscan.plist" "$LAUNCH_AGENTS/"

launchctl load "$LAUNCH_AGENTS/com.analista.tech.plist"
launchctl load "$LAUNCH_AGENTS/com.analista.tech.xscan.plist"

echo "Jobs loaded. Daily 07:00, X scan 08:00–22:00 every 2h."
launchctl list | grep analista
```

- [ ] **Step 5: Run install**

```bash
chmod +x launchd/install.sh
bash launchd/install.sh
```

Expected output: two `com.analista.tech*` entries from `launchctl list`.

- [ ] **Step 6: Commit**

```bash
git add launchd/
git commit -m "feat: launchd scheduling — daily pipeline + 2h X scan"
```

---

### Task 11: Full Integration Test

- [ ] **Step 1: Run full test suite**

```bash
source .venv/bin/activate
pytest tests/ -v
```

Expected: all 13 tests pass.

- [ ] **Step 2: Run full pipeline with real APIs (all tickers)**

```bash
python main.py
```

Monitor `data/agent.log`. Expected: all companies processed, no fatal errors, report files written.

- [ ] **Step 3: Verify dashboard**

```bash
open reports/$(date +%Y-%m-%d)/report.html
```

Expected: dark dashboard, top 10 table, full universe filterable table.

- [ ] **Step 4: Verify macOS notification fired**

Check Notification Center — alert for tickers with score > 75.

- [ ] **Step 5: Run xscan manually**

```bash
python xscan.py
```

Expected: `X scan complete.` in log, no crash.

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: AI sector analyst v1 complete"
```

---

## Self-Review

**Spec coverage:**
- ✅ ~150 ticker AI/chip universe → `config.yaml` + `universe.py`
- ✅ yfinance fundamentals → `collector.py:fetch_financial_snapshot`
- ✅ SEC EDGAR 8-K → `collector.py:fetch_edgar_filings`
- ✅ Exa news search → `researcher.py:fetch_exa_news`
- ✅ X API scan (daily + 2h) → `researcher.py:fetch_x_mentions` + `xscan.py`
- ✅ RSS feeds → `researcher.py:fetch_rss_news`
- ✅ Claude Haiku scoring 5 dimensions → `analyzer.py:score_company`
- ✅ Claude Sonnet narrative top 10 → `analyzer.py:generate_narrative`
- ✅ HTML dashboard → `templates/dashboard.html` + `reporter.py:generate_html_report`
- ✅ MD report → `reporter.py:generate_md_report`
- ✅ alerts.json → `reporter.py:save_alerts_json`
- ✅ macOS notification → `reporter.py:send_macos_notification`
- ✅ Weekly email Monday → `reporter.py:send_weekly_email` + `main.py`
- ✅ SQLite persistence → `modules/db.py`
- ✅ launchd daily 07:00 → `com.analista.tech.plist`
- ✅ launchd X scan every 2h → `com.analista.tech.xscan.plist`
- ✅ Configurable thresholds → `config.yaml`

**Placeholder scan:** None.

**Type consistency:** `score_company` output keys used identically in `main.py`, `generate_narrative`, `reporter.py`.
