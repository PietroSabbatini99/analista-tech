# 🔬 Analista Tech

Autonomous AI agent that analyzes publicly traded companies in the AI/semiconductor ecosystem and surfaces those with the highest potential for exceptional market value increase.

Runs daily on a local Mac mini via launchd. No cloud, no subscription — just Python + two API keys.

---

## What it does

Every morning at 07:00 the agent:

1. **Collects** financial data for ~50 tickers (yfinance, SEC EDGAR, TradingView-TA)
2. **Researches** news, X/Twitter mentions, RSS feeds (Exa neural search)
3. **Scores** each company 0–100 across 5 dimensions using Claude Haiku
4. **Generates** an investment thesis for the top 10 using Claude Sonnet
5. **Reports** via local HTML dashboard + Markdown + macOS notifications + weekly email

An X scanner also runs every 2 hours to catch influencer mentions in real time.

---

## Scoring model

| Dimension | Weight | Source |
|---|---|---|
| Revenue growth YoY | 20% | yfinance |
| Margins + cash position | 15% | yfinance |
| Partnership / M&A / news | 25% | Exa + RSS + SEC 8-K |
| Influencer / analyst statements | 20% | Exa + X |
| Price momentum + volume spike | 20% | yfinance + TradingView |

---

## Dashboard (8 tabs)

| Tab | Content |
|---|---|
| Overview | Top 10 signal cards + full universe table |
| Analyst | Consensus target price, upside %, # analysts |
| Technical | TradingView RSI, MACD, EMA cross, signal |
| Earnings | Upcoming earnings calendar |
| Short Interest | Short float %, days to cover, squeeze candidates |
| Valuation | P/E vs sector average |
| Earnings Surprise | Last 4Q EPS beat/miss history |
| Correlation | Pairwise 60-day return correlation heatmap by sector |

Dashboard styled following Emil Kowalski's design engineering philosophy — custom easing curves, staggered animations, press states, `prefers-reduced-motion` support.

---

## Setup

### Requirements

- Python 3.12+
- macOS (for launchd scheduling)
- Anthropic API key (~€3–7/month usage)
- Exa API key (free tier: 1000 req/month)

### Install

```bash
git clone https://github.com/PietroSabbatini99/analista-tech
cd analista-tech

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.template .env
# Edit .env with your API keys:
# ANTHROPIC_API_KEY=sk-ant-...
# EXA_API_KEY=...
# GMAIL_ADDRESS=you@gmail.com        (optional, for weekly email)
# GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx  (optional)
# ALERT_EMAIL_TO=you@email.com       (optional)
```

Edit `config.yaml` to customize the ticker universe, alert thresholds, RSS feeds and X accounts to monitor.

### Run

```bash
# Single run
python main.py

# X scanner only
python xscan.py

# Open latest report
open reports/$(date +%Y-%m-%d)/report.html
```

### Schedule (launchd)

```bash
bash launchd/install.sh
```

Loads two jobs:
- `com.analista.tech` — full pipeline at 07:00 daily
- `com.analista.tech.xscan` — X scan every 2h (08:00–22:00)

---

## Project structure

```
├── main.py              # Main orchestrator
├── xscan.py             # Standalone X signal scanner
├── config.yaml          # Ticker universe, thresholds, feeds
├── .env.template        # API key template
├── modules/
│   ├── collector.py     # yfinance, TradingView-TA, SEC EDGAR
│   ├── researcher.py    # Exa news + RSS feeds
│   ├── analyzer.py      # Claude Haiku scoring + Sonnet narrative
│   ├── reporter.py      # HTML/MD report + alerts + email
│   ├── universe.py      # Ticker list loader
│   └── db.py            # SQLite helpers
├── templates/
│   ├── dashboard.html   # Jinja2 dashboard (8 tabs)
│   └── email.html       # Weekly email template
├── launchd/             # macOS scheduling plists
└── tests/               # pytest unit tests (17 tests)
```

---

## Data sources (all free)

| Source | Data |
|---|---|
| yfinance | Prices, fundamentals, P/E, analyst targets, short interest, earnings |
| TradingView-TA | RSI, MACD, EMA cross, signal summary |
| SEC EDGAR | 8-K filings, Form 4 insider trades |
| Exa | News, X/Twitter mentions, partnerships |
| RSS | SemiAnalysis, The Chip Letter, TechCrunch, Reuters Tech |

---

## Tests

```bash
pytest tests/ -v  # 17 tests
```

---

## Cost estimate

| Item | Monthly |
|---|---|
| Claude Haiku (bulk scoring ~50 tickers/day) | ~€2–4 |
| Claude Sonnet (top 10 narratives/day) | ~€1–3 |
| Infrastructure | €0 (local Mac mini) |
| **Total** | **~€3–7** |

---

## License

MIT
