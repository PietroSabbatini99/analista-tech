# Analista Tech — Agent Chat System Design
*Created: 2026-05-21 | Status: Approved*

## Overview

Sistema agente autonomo con:
1. **Memoria vettoriale** (ChromaDB) — storico permanente di news, score, filing
2. **Chat web interattiva** (FastAPI + dark UI) — accessibile da qualsiasi device via ngrok
3. **Alert email proattivi** — triggered da segnali forti basati su NEWS, non su prezzo
4. **News scanner** (xscan evoluto) — classifica news ogni 2h, alert immediato se significance ≥ 7

---

## Architettura

```
Mac mini (sempre acceso)

launchd jobs:
  com.analista.tech          → 07:00 daily (pipeline + ChromaDB ingestion)
  com.analista.tech.xscan    → ogni 2h (news scan + classificazione + email alert)
  com.analista.agent         → al boot, sempre attivo (FastAPI :8080)
  com.analista.ngrok         → al boot, tunnel pubblico

URL pubblico: https://analista-xxxx.ngrok-free.app/chat
```

---

## Componenti nuovi

### `agent.py` — FastAPI server
- `GET /` → chat UI HTML
- `POST /chat` → riceve messaggio, restituisce risposta agente
- `GET /status` → health check (pipeline ultima run, n° documenti ChromaDB)
- `GET /ticker/{ticker}` → brief automatico su singola società

### `modules/memory.py` — ChromaDB wrapper

**Collezioni:**

| Collezione | Campi | Retention |
|---|---|---|
| `news` | ticker, date, title, snippet, source, category, significance, url | Per sempre |
| `scores` | ticker, date, total_score, reasoning, narrative | Per sempre |
| `filings` | ticker, date, form_type, content | Per sempre |

**API:**
```python
add_news(ticker, items)           # ingesta notizie
add_score(ticker, date, scored)   # ingesta score + reasoning
search(query, ticker=None, k=10)  # semantic search
get_history(ticker, days=90)      # storico score ticker
```

### `modules/news_classifier.py` — Classificatore news (Claude Haiku)

Per ogni notizia, assegna:
- `category`: rating_change | ma_event | government_contract | earnings_guidance | supply_chain | executive_hire | patent_grant | product_launch | strategic_partnership | other
- `significance`: 1-10
- `sentiment`: bullish | bearish | neutral
- `reasoning`: 1 frase

### `templates/chat.html` — Chat UI

Dark theme coerente con dashboard. Layout tipo ChatGPT:
- Header con status agente
- Messaggi con citazione fonti ChromaDB
- Ticker chip cliccabili per brief rapido
- Input con shortcut: `/briefing`, `/ticker NVDA`, `/top5`

---

## Segnali Forti (trigger email alert)

Basati esclusivamente su NEWS — non su prezzo o score.

```yaml
agent_alerts:
  significance_threshold: 7
  immediate_alert: true

  high_priority:               # alert immediato se significance >= 7
    - rating_change
    - ma_event
    - government_contract
    - earnings_guidance
    - supply_chain
    - strategic_partnership

  medium_priority:             # alert solo se score ticker > 60 E significance >= 8
    - executive_hire
    - patent_grant
    - product_launch
    - index_inclusion
```

**Formato email alert:**
```
⚡ SEGNALE: CRWV — strategic_partnership

CoreWeave annuncia accordo pluriennale con Microsoft Azure.
Significance: 9/10 | Sentiment: bullish
Claude: "Accordo strutturale, riduce rischio cliente-concentrazione."
Fonte: Reuters, 2026-05-21 14:32

→ [Approfondisci](https://analista-xxxx.ngrok-free.app/chat?ticker=CRWV)
```

---

## Flusso query agente

```
Utente scrive → FastAPI riceve
    ↓
Intent detection (Claude Haiku):
  "analisi ticker"   → news + score history da ChromaDB
  "ricerca autonoma" → semantic search + fresh data da CLI
  "raccomandazione"  → cross-ticker comparison
  "briefing"         → top 5 segnali giornalieri
    ↓
ChromaDB semantic search → top-K documenti
    ↓
Claude Sonnet: system prompt + contesto + domanda
    ↓
Risposta + fonti citate → UI
```

**System prompt:**
```
Sei un analista finanziario specializzato in AI/chip/datacenter.
Hai accesso a storico completo di news, score e filing SEC.
Rispondi in italiano. Sii diretto, cita le fonti.
Non dare consigli di investimento — analizza fatti e segnali.
```

---

## Ingestion pipeline

**`main.py`** (dopo ogni run): ingesta news + score in ChromaDB
**`xscan.py`** (ogni 2h): fetch news → classifica → se significance ≥ 7 → email + ChromaDB

---

## File system

```
Analista Tech/
├── agent.py                    # FastAPI server + agent logic   [NUOVO]
├── modules/
│   ├── memory.py               # ChromaDB wrapper               [NUOVO]
│   └── news_classifier.py      # Claude news classification     [NUOVO]
├── templates/
│   └── chat.html               # Chat UI dark theme             [NUOVO]
└── launchd/
    ├── com.analista.agent.plist # FastAPI al boot                [NUOVO]
    └── com.analista.ngrok.plist # ngrok al boot                 [NUOVO]
```

**Modificati:** `main.py` (+ingestion), `xscan.py` (+classificazione + alert)

---

## Stack

| Componente | Tool | Costo |
|---|---|---|
| Web server | FastAPI + Uvicorn | €0 |
| Memoria | ChromaDB | €0 |
| Chat UI | HTML/JS vanilla | €0 |
| Tunnel | ngrok free | €0 |
| Agent LLM | Claude Sonnet | ~€3-8/mese |
| Classifier | Claude Haiku | ~€0.5-1/mese |

---

## Setup (3 comandi)

```bash
pip install fastapi uvicorn chromadb
brew install ngrok
ngrok config add-authtoken <token>
```

---

## Out of scope v1

- Autenticazione (URL segreto come protezione)
- Telegram bot
- Mobile app nativa
- Multi-utente
