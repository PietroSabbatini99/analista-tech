# AI Sector Analyst — Design Spec
*Created: 2026-05-10 | Status: Approved*

## Overview

Autonomous agent that runs daily on a Mac mini, analyzes ~150 publicly traded companies in the AI/chip/datacenter ecosystem, and surfaces those with the highest probability of exceptional market value increase. Outputs: local HTML dashboard, Markdown report, macOS notifications, weekly email.

---

## Universe

~150 ticker coprenti:
- Chip design: NVDA, AMD, INTC, QCOM, MRVL, AVGO, ARM, SMCI, ALAB, LSCC...
- Memory/storage: MU, WDC, STX...
- Datacenter infra: DELL, HPE, SMCI, VRT, CDNS...
- AI software/cloud: MSFT, GOOGL, META, AMZN, ORCL, SNOW, PLTR, AI, BBAI...
- Equipment: AMAT, KLAC, LRCX, ASML, TER...
- Power/cooling: ETN, VRT...

Definiti in `config.yaml`, aggiornabili senza toccare codice.

---

## Architecture

```
launchd (07:00 daily)
    └── main.py (orchestrator)
         ├── universe.py       → carica lista ticker da config.yaml
         ├── collector.py      → yfinance + SEC EDGAR
         ├── researcher.py     → Exa + X API v2 + RSS feeds
         ├── analyzer.py       → scoring via Claude API
         └── reporter.py       → HTML + MD + alert
```

---

## Moduli

### universe.py
- Carica ticker list da `config.yaml`
- Arricchisce con metadata (nome, settore, market cap bucket)
- Output: lista `{ticker, name, sector, cap_tier}`

### collector.py
- **yfinance**: prezzi 1y, revenue TTM, gross margin, cash, P/S, volume
- **SEC EDGAR full-text search API** (gratuita): 8-K, 10-Q, 10-K
- Cache SQLite 24h
- Output: `{ticker → financial_snapshot}`

### researcher.py
- **Exa** (`web_search_exa`): notizie ultimi 7 giorni per ticker
- **X API v2** (`tweepy`): tweet ultimi 3 giorni da account chiave (CEO, analisti, media)
- **RSS feeds**: SemiAnalysis, The Chip Letter, TechCrunch, Reuters Tech, Bloomberg Tech
- Output: `{ticker → [news_items]}` con titolo, fonte, data, snippet

### analyzer.py
- **Claude Haiku** per scoring bulk (150 società)
- Score 0–100 su 5 dimensioni:

| Dimensione | Peso |
|---|---|
| Revenue growth YoY | 20% |
| Margini + cash | 15% |
| Partnership/M&A/contratti | 25% |
| Dichiarazioni influencer/analisti | 20% |
| Price momentum + volume spike | 20% |

- **Claude Sonnet** per narrativa sintetica top 10 (max 200 parole/società)
- Output: `{ticker, scores, total_score, narrative, alerts[]}`

### reporter.py
- `reports/YYYY-MM-DD/report.html` (Jinja2)
- `reports/YYYY-MM-DD/report.md`
- `reports/YYYY-MM-DD/alerts.json`
- macOS notification via `osascript` per score > soglia
- Email settimanale (lunedì) via SMTP Gmail

---

## Scoring — Soglie Alert

```yaml
alerts:
  score_threshold: 75
  score_spike: 15
  partnership_instant: true
  x_influencer_threshold: 3
```

---

## Dashboard HTML

1. Header: data run, N società analizzate
2. Top Signals: tabella top 10 con score, trigger, Δprezzo
3. Full Universe: tabella sortable/filterable
4. Score History: sparkline 30gg (Chart.js)
5. Alert Log: storico 30gg

---

## Database SQLite

```sql
companies(ticker, name, sector, cap_tier, added_at)
daily_scores(id, ticker, date, score_revenue, score_margins, score_news,
             score_influencer, score_momentum, total_score, narrative)
alerts(id, ticker, date, alert_type, message, notified)
news_cache(id, ticker, date, source, title, url, snippet)
```

---

## File System

```
~/Desktop/Analista Tech/
├── main.py
├── config.yaml
├── .env                    # ANTHROPIC_API_KEY, X_BEARER_TOKEN, GMAIL_APP_PASSWORD
├── requirements.txt
├── modules/
│   ├── universe.py
│   ├── collector.py
│   ├── researcher.py
│   ├── analyzer.py
│   └── reporter.py
├── data/
│   ├── tech_analyst.db
│   └── cache/
├── reports/
│   └── YYYY-MM-DD/
├── templates/
│   ├── dashboard.html
│   └── email.html
└── launchd/
    └── com.analista.tech.plist
```

---

## Dipendenze Python

```
anthropic>=0.25.0
yfinance>=0.2.40
feedparser>=6.0.11
tweepy>=4.14.0
jinja2>=3.1.4
requests>=2.31.0
```

---

## Scheduling (launchd)

Due job separati:

| Job | Frequenza | Cosa fa |
|---|---|---|
| `com.analista.tech.plist` | 07:00 daily | Pipeline completa (collect + research + analyze + report) |
| `com.analista.tech.xscan.plist` | ogni 2h (08:00–22:00) | Solo X API scan → notifica immediata se segnale forte |

X scan leggero: non chiama Claude, solo conta mention per ticker da account chiave. Alert se `x_influencer_threshold` superata. Risultati salvati in `alerts` table per inclusione nel report mattutino.

Log: `data/agent.log`, `data/agent.error.log`, `data/xscan.log`

---

## Costi stimati

| Voce | Stima mensile |
|---|---|
| Claude Haiku (bulk ~150 società/giorno) | ~€2–4 |
| Claude Sonnet (top 10 narrative/giorno) | ~€1–3 |
| Infrastruttura | €0 (Mac mini locale) |
| **Totale** | **~€3–7/mese** |

---

## Vincoli

- X API free tier: 500k tweet read/mese
- yfinance: fondamentali con ritardo ~24h, non real-time
- SEC EDGAR: solo società USA quotate
- Cache 24h — non adatto a trading intraday

## Out of scope (v1)

- Trading automatico
- Dati real-time
- Analisi opzioni/derivati
- Multi-lingua news
