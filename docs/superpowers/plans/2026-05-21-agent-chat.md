# Agent Chat System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI agent with ChromaDB memory, news-based email alerts, and a dark-theme chat UI accessible via ngrok.

**Architecture:** ChromaDB stores all news/scores permanently. FastAPI exposes a chat endpoint where Claude Sonnet answers using retrieved context. xscan.py classifies news with Claude Haiku and fires email alerts for significance ≥ 7.

**Tech Stack:** FastAPI, Uvicorn, ChromaDB, Claude Haiku (classifier), Claude Sonnet (agent), ngrok, vanilla JS chat UI.

---

### Task 1: Install dependencies + verify ChromaDB

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Install packages**

```bash
cd "/Users/pietrosabbatini/Desktop/Analista Tech"
source .venv/bin/activate
pip install fastapi uvicorn chromadb
brew install ngrok
```

- [ ] **Step 2: Verify chromadb works**

```bash
python -c "import chromadb; c = chromadb.PersistentClient(path='data/chromadb'); print('ChromaDB OK:', c.list_collections())"
```
Expected: `ChromaDB OK: []`

- [ ] **Step 3: Update requirements.txt** — add:
```
fastapi>=0.115.0
uvicorn>=0.30.0
chromadb>=0.6.0
```

- [ ] **Step 4: Commit**
```bash
git add requirements.txt
git commit -m "Add FastAPI, Uvicorn, ChromaDB dependencies"
```

---

### Task 2: `modules/memory.py` — ChromaDB wrapper

**Files:**
- Create: `modules/memory.py`
- Create: `tests/test_memory.py`

- [ ] **Step 1: Write failing tests** — create `tests/test_memory.py`:

```python
import pytest
from modules.memory import Memory


@pytest.fixture
def mem(tmp_path):
    return Memory(db_path=str(tmp_path / "test_chroma"))


def test_add_and_search_news(mem):
    mem.add_news("NVDA", [
        {"title": "NVDA signs Azure deal", "url": "https://example.com/1",
         "date": "2026-05-21", "snippet": "Microsoft Azure signs GPU deal with NVIDIA",
         "source": "Reuters", "category": "strategic_partnership", "significance": 9}
    ])
    results = mem.search("Microsoft Azure GPU deal", ticker="NVDA", k=5)
    assert len(results) >= 1
    assert results[0]["ticker"] == "NVDA"


def test_add_and_get_score_history(mem):
    mem.add_score("NVDA", "2026-05-21", {
        "ticker": "NVDA", "total_score": 84,
        "reasoning": "Strong momentum", "narrative": "NVDA thesis."
    })
    history = mem.get_score_history("NVDA", days=7)
    assert len(history) >= 1
    assert history[0]["total_score"] == 84


def test_search_without_ticker_filter(mem):
    mem.add_news("AMD", [
        {"title": "AMD acquires Pensando", "url": "https://example.com/2",
         "date": "2026-05-20", "snippet": "AMD acquisition of Pensando",
         "source": "WSJ", "category": "ma_event", "significance": 8}
    ])
    results = mem.search("acquisition semiconductor", k=5)
    assert len(results) >= 1


def test_add_news_deduplicates(mem):
    item = {"title": "NVDA earnings beat", "url": "https://example.com/3",
            "date": "2026-05-21", "snippet": "NVDA beats EPS",
            "source": "Bloomberg", "category": "earnings_guidance", "significance": 7}
    mem.add_news("NVDA", [item])
    mem.add_news("NVDA", [item])
    results = mem.search("NVDA earnings beat", ticker="NVDA", k=10)
    assert len(results) == 1
```

- [ ] **Step 2: Run — expect FAIL**
```bash
pytest tests/test_memory.py -v
```

- [ ] **Step 3: Create `modules/memory.py`**

```python
"""ChromaDB persistent memory for news, scores, and filings."""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
import chromadb


class Memory:
    def __init__(self, db_path: str = "data/chromadb"):
        self.client  = chromadb.PersistentClient(path=db_path)
        self.news    = self.client.get_or_create_collection("news")
        self.scores  = self.client.get_or_create_collection("scores")
        self.filings = self.client.get_or_create_collection("filings")

    def add_news(self, ticker: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        ids, docs, metas = [], [], []
        for item in items:
            uid = hashlib.md5(item.get("url", item["title"]).encode()).hexdigest()
            ids.append(uid)
            docs.append(f"{item['title']} {item.get('snippet', '')}")
            metas.append({
                "ticker":       ticker,
                "date":         item.get("date", ""),
                "title":        item.get("title", ""),
                "snippet":      item.get("snippet", "")[:500],
                "source":       item.get("source", ""),
                "url":          item.get("url", ""),
                "category":     item.get("category", "other"),
                "significance": int(item.get("significance", 5)),
            })
        self.news.upsert(ids=ids, documents=docs, metadatas=metas)

    def search(self, query: str, ticker: str | None = None, k: int = 10) -> list[dict[str, Any]]:
        where  = {"ticker": ticker} if ticker else None
        kwargs: dict = {"query_texts": [query], "n_results": k}
        if where:
            kwargs["where"] = where
        try:
            res = self.news.query(**kwargs)
        except Exception:
            return []
        return [{**meta, "distance": dist}
                for meta, dist in zip(res["metadatas"][0], res["distances"][0])]

    def add_score(self, ticker: str, date: str, scored: dict[str, Any]) -> None:
        uid = f"{ticker}_{date}"
        doc = (f"{ticker} score {scored.get('total_score', 0):.0f} on {date}. "
               f"{scored.get('reasoning', '')} {scored.get('narrative', '')}")
        self.scores.upsert(
            ids=[uid], documents=[doc],
            metadatas=[{
                "ticker":      ticker,
                "date":        date,
                "total_score": float(scored.get("total_score", 0)),
                "reasoning":   str(scored.get("reasoning", ""))[:500],
                "narrative":   str(scored.get("narrative", ""))[:500],
            }]
        )

    def get_score_history(self, ticker: str, days: int = 90) -> list[dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            res = self.scores.get(
                where={"$and": [{"ticker": ticker}, {"date": {"$gte": cutoff}}]}
            )
        except Exception:
            return []
        rows = list(res["metadatas"])
        rows.sort(key=lambda x: x.get("date", ""), reverse=True)
        return rows

    def add_filing(self, ticker: str, date: str, form_type: str, content: str) -> None:
        uid = hashlib.md5(f"{ticker}_{date}_{form_type}".encode()).hexdigest()
        self.filings.upsert(
            ids=[uid], documents=[content[:2000]],
            metadatas=[{"ticker": ticker, "date": date, "form_type": form_type}],
        )
```

- [ ] **Step 4: Run — expect PASS**
```bash
pytest tests/test_memory.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**
```bash
git add modules/memory.py tests/test_memory.py
git commit -m "Add ChromaDB memory module with news/score/filing storage"
```

---

### Task 3: `modules/news_classifier.py` — Claude Haiku news classifier

**Files:**
- Create: `modules/news_classifier.py`
- Create: `tests/test_classifier.py`

- [ ] **Step 1: Write failing tests** — create `tests/test_classifier.py`:

```python
import json
from unittest.mock import patch, MagicMock
from modules.news_classifier import classify_news_item, should_alert, build_alert_email


def _mock_claude(text):
    mock = MagicMock()
    mock.content = [MagicMock(text=text)]
    return mock


def test_classify_partnership_news():
    fake = json.dumps({"category": "strategic_partnership", "significance": 9,
                        "sentiment": "bullish", "reasoning": "Structural deal."})
    with patch("modules.news_classifier.anthropic.Anthropic") as M:
        M.return_value.messages.create.return_value = _mock_claude(fake)
        r = classify_news_item("CoreWeave signs $10B Azure deal", "GPU cluster.", api_key="fake")
    assert r["category"] == "strategic_partnership"
    assert r["significance"] == 9


def test_classify_handles_markdown_json():
    fake = '```json\n{"category":"ma_event","significance":8,"sentiment":"bullish","reasoning":"Acquisition."}\n```'
    with patch("modules.news_classifier.anthropic.Anthropic") as M:
        M.return_value.messages.create.return_value = _mock_claude(fake)
        r = classify_news_item("NVDA buys startup", "...", api_key="fake")
    assert r["category"] == "ma_event"


def test_should_alert_high_priority():
    assert should_alert("strategic_partnership", 7) is True
    assert should_alert("ma_event", 9) is True
    assert should_alert("ma_event", 6) is False


def test_should_alert_medium_with_high_score():
    assert should_alert("executive_hire", 8, ticker_score=65) is True
    assert should_alert("executive_hire", 8, ticker_score=55) is False


def test_build_alert_email():
    item = {"ticker": "CRWV", "title": "CoreWeave Azure deal",
            "snippet": "Microsoft commits.", "source": "Reuters",
            "date": "2026-05-21", "category": "strategic_partnership",
            "significance": 9, "reasoning": "Structural deal."}
    subject, body = build_alert_email(item, base_url="https://test.ngrok.io")
    assert "CRWV" in subject
    assert "https://test.ngrok.io/chat?ticker=CRWV" in body
```

- [ ] **Step 2: Run — expect FAIL**
```bash
pytest tests/test_classifier.py -v
```

- [ ] **Step 3: Create `modules/news_classifier.py`**

```python
"""News classifier using Claude Haiku. Assigns category, significance, sentiment."""
import json
import anthropic
from typing import Any

HIGH_PRIORITY   = {"rating_change","ma_event","government_contract",
                   "earnings_guidance","supply_chain","strategic_partnership"}
MEDIUM_PRIORITY = {"executive_hire","patent_grant","product_launch","index_inclusion"}

_PROMPT = """\
Classify this financial news item for a stock analyst.

Title: {title}
Snippet: {snippet}

Return ONLY valid JSON (no markdown):
{{"category":"<rating_change|ma_event|government_contract|earnings_guidance|supply_chain|executive_hire|patent_grant|product_launch|strategic_partnership|other>",
  "significance":<1-10>,
  "sentiment":"<bullish|bearish|neutral>",
  "reasoning":"<one sentence>"}}

Significance: 9-10=major acquisition/gov contract, 7-8=analyst upgrade/partnership,
5-6=product launch/exec hire, 3-4=minor news, 1-2=irrelevant."""


def classify_news_item(title: str, snippet: str, api_key: str) -> dict[str, Any]:
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _PROMPT.format(title=title, snippet=snippet[:400])
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.startswith("json") else raw
        return json.loads(raw.strip())
    except Exception:
        return {"category":"other","significance":5,"sentiment":"neutral","reasoning":"Classification failed."}


def should_alert(category: str, significance: int, ticker_score: float = 0) -> bool:
    if category in HIGH_PRIORITY and significance >= 7:
        return True
    if category in MEDIUM_PRIORITY and significance >= 8 and ticker_score > 60:
        return True
    return False


def build_alert_email(item: dict[str, Any], base_url: str = "http://localhost:8080") -> tuple[str, str]:
    ticker = item.get("ticker","?")
    cat    = item.get("category","other")
    sig    = item.get("significance",0)
    subject = f"⚡ SEGNALE: {ticker} — {cat} (significance {sig}/10)"
    body = f"""<h2>⚡ SEGNALE: {ticker}</h2>
<p><strong>{item.get('title','')}</strong></p>
<p>{item.get('snippet','')}</p><hr>
<p><b>Categoria:</b> {cat} | <b>Significance:</b> {sig}/10 | <b>Sentiment:</b> {item.get('sentiment','neutral')}</p>
<p><i>Claude: "{item.get('reasoning','')}"</i></p>
<p>Fonte: {item.get('source','')} — {item.get('date','')}</p>
<p><a href="{base_url}/chat?ticker={ticker}">→ Approfondisci con l'agente</a></p>"""
    return subject, body
```

- [ ] **Step 4: Run — expect PASS**
```bash
pytest tests/test_classifier.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**
```bash
git add modules/news_classifier.py tests/test_classifier.py
git commit -m "Add news classifier: Claude Haiku categories + significance + alert email"
```

---

### Task 4: ChromaDB ingestion in `main.py` + news alerts in `xscan.py`

**Files:**
- Modify: `main.py` (after `generate_html_report`)
- Modify: `xscan.py` (replace main body)
- Modify: `.env.template` (add NGROK_URL)

- [ ] **Step 1: Add ingestion block to `main.py`**

After the line `generate_html_report(all_scores, str(report_dir / "report.html"), ...)`, insert:

```python
    # ── ChromaDB ingestion ────────────────────────────────────────────────
    try:
        from modules.memory import Memory
        mem = Memory(str(BASE_DIR / "data" / "chromadb"))
        for s in all_scores:
            mem.add_score(s["ticker"], today, s)
        log.info(f"ChromaDB: ingested {len(all_scores)} scores")
    except Exception as e:
        log.warning(f"ChromaDB ingestion failed: {e}")
```

- [ ] **Step 2: Update `xscan.py` main() — add classification + alerts**

Replace the inner loop in `xscan.py` (the `for company in companies:` block) with:

```python
    from modules.memory import Memory
    from modules.news_classifier import classify_news_item, should_alert, build_alert_email
    from modules.researcher import fetch_google_news

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
```

Also add `NGROK_URL=https://your-subdomain.ngrok-free.app` to `.env.template`.

- [ ] **Step 3: Run full tests**
```bash
pytest tests/ -q
```
Expected: 17+ passed

- [ ] **Step 4: Commit**
```bash
git add main.py xscan.py .env.template
git commit -m "Add ChromaDB ingestion + news-based alert emails via xscan"
```

---

### Task 5: `agent.py` — FastAPI server + agent logic

**Files:**
- Create: `agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write failing tests** — create `tests/test_agent.py`:

```python
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _mock_search(*a, **kw):
    return [{"ticker":"NVDA","title":"NVDA Azure deal","snippet":"Big deal",
             "date":"2026-05-21","source":"Reuters","significance":9}]

def _mock_claude(text):
    m = MagicMock(); m.content = [MagicMock(text=text)]; return m


def test_chat_returns_response():
    with patch("agent.Memory") as MM, patch("agent.anthropic.Anthropic") as MC:
        MM.return_value.search.side_effect = _mock_search
        MM.return_value.get_score_history.return_value = []
        MC.return_value.messages.create.return_value = _mock_claude("NVDA ha score alto.")
        from agent import app
        r = TestClient(app).post("/chat", json={"message":"perché NVDA?","ticker":"NVDA"})
    assert r.status_code == 200
    assert "response" in r.json()


def test_chat_without_ticker():
    with patch("agent.Memory") as MM, patch("agent.anthropic.Anthropic") as MC:
        MM.return_value.search.return_value = []
        MM.return_value.get_score_history.return_value = []
        MC.return_value.messages.create.return_value = _mock_claude("Briefing: NVDA top.")
        from agent import app
        r = TestClient(app).post("/chat", json={"message":"briefing"})
    assert r.status_code == 200


def test_status_endpoint():
    with patch("agent.Memory") as MM:
        MM.return_value.news.count.return_value = 150
        MM.return_value.scores.count.return_value = 67
        from agent import app
        r = TestClient(app).get("/status")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_ui_served():
    from agent import app
    r = TestClient(app).get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
```

- [ ] **Step 2: Run — expect FAIL**
```bash
pytest tests/test_agent.py -v
```

- [ ] **Step 3: Create `agent.py`**

```python
#!/usr/bin/env python3
"""FastAPI agent server. Run: uvicorn agent:app --host 0.0.0.0 --port 8080"""
import os
import sqlite3
from pathlib import Path
from datetime import date

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env", override=True)

app = FastAPI(title="Analista Tech Agent")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DB_PATH       = str(BASE_DIR / "data" / "tech_analyst.db")
CHROMA_PATH   = str(BASE_DIR / "data" / "chromadb")

from modules.memory import Memory
_mem: Memory | None = None

def get_memory() -> Memory:
    global _mem
    if _mem is None:
        _mem = Memory(CHROMA_PATH)
    return _mem

SYSTEM_PROMPT = """Sei un analista finanziario specializzato in AI/chip/datacenter.
Hai accesso a storico completo di news, score giornalieri e filing SEC.
Rispondi in italiano. Cita le fonti quando disponibili.
NON dare consigli di investimento — analizza fatti e segnali."""


def _today_top(limit: int = 5) -> list[dict]:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ticker,name,total_score,reasoning FROM daily_scores "
            "WHERE date=? ORDER BY total_score DESC LIMIT ?",
            (date.today().isoformat(), limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


@app.get("/", response_class=HTMLResponse)
async def chat_ui():
    p = BASE_DIR / "templates" / "chat.html"
    return HTMLResponse(p.read_text() if p.exists() else "<h1>chat.html not found</h1>")


@app.post("/chat")
async def chat(request: Request):
    body    = await request.json()
    message = body.get("message", "").strip()
    ticker  = body.get("ticker")
    if not message:
        return JSONResponse({"response": "Scrivi una domanda.", "sources": []})

    mem     = get_memory()
    sources = mem.search(message, ticker=ticker, k=8)
    history = mem.get_score_history(ticker, days=30) if ticker else []
    top     = _today_top()

    parts = []
    if top:
        parts.append("TOP OGGI: " + ", ".join(f"{r['ticker']}({r['total_score']:.0f})" for r in top))
    if history:
        parts.append("STORICO " + ticker + ": " +
                     " | ".join(f"{r['date']}: {r['total_score']:.0f}" for r in history[:5]))
    if sources:
        parts.append("NEWS:\n" + "\n".join(
            f"- [{s['date']}] {s['title']} ({s['source']}, sig={s.get('significance',5)})"
            for s in sources[:5]))

    context = "\n\n".join(parts) or "Nessun contesto disponibile."
    if not ANTHROPIC_KEY:
        return JSONResponse({"response": "ANTHROPIC_API_KEY mancante.", "sources": []})

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role":"user","content":f"CONTESTO:\n{context}\n\nDOMANDA: {message}"}],
        )
        response_text = msg.content[0].text
    except Exception as e:
        response_text = f"Errore API: {e}"

    return JSONResponse({
        "response": response_text,
        "sources": [{"title":s["title"],"source":s["source"],
                     "date":s["date"],"significance":s.get("significance",5)}
                    for s in sources[:5]]
    })


@app.get("/status")
async def status():
    mem = get_memory()
    try: n_news, n_scores = mem.news.count(), mem.scores.count()
    except: n_news = n_scores = 0
    last = "N/A"
    try:
        lines = (BASE_DIR/"data"/"agent.log").read_text().splitlines()
        done  = [l for l in lines if "Done." in l]
        last  = done[-1].split(" INFO")[0] if done else "N/A"
    except: pass
    return JSONResponse({"status":"ok","news_in_memory":n_news,
                         "scores_in_memory":n_scores,"last_pipeline_run":last})


@app.get("/ticker/{ticker}")
async def ticker_brief(ticker: str):
    ticker = ticker.upper()
    mem    = get_memory()
    return JSONResponse({"ticker":ticker,
                         "recent_news": mem.search(ticker, ticker=ticker, k=5),
                         "score_history": mem.get_score_history(ticker, days=30)})
```

- [ ] **Step 4: Run — expect PASS**
```bash
pytest tests/test_agent.py -v
```
Expected: 4 passed

- [ ] **Step 5: Smoke test**
```bash
uvicorn agent:app --host 0.0.0.0 --port 8080 &
curl -s http://localhost:8080/status | python3 -m json.tool
kill %1
```
Expected: `{"status": "ok", ...}`

- [ ] **Step 6: Commit**
```bash
git add agent.py tests/test_agent.py
git commit -m "Add FastAPI agent server with ChromaDB context retrieval"
```

---

### Task 6: `templates/chat.html` — Dark chat UI

**Files:**
- Create: `templates/chat.html`

- [ ] **Step 1: Create `templates/chat.html`**

```html
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Analista Tech — Agente</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root{--bg:#0a0a0f;--surface:#111118;--border:#1e1e2e;--text:#e4e4ea;--dim:#8a8a9a;--accent:#6366f1;--green:#22c55e;}
    *{box-sizing:border-box;margin:0;padding:0;}
    body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;height:100vh;display:flex;flex-direction:column;}
    header{padding:16px 24px;border-bottom:1px solid var(--border);background:var(--surface);display:flex;align-items:center;gap:12px;}
    .logo{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#a855f7);display:grid;place-items:center;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:14px;}
    h1{font-size:15px;font-weight:600;}
    #dot{width:8px;height:8px;border-radius:50%;background:var(--green);margin-left:auto;box-shadow:0 0 8px var(--green);}
    #msgs{flex:1;overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:16px;}
    .msg{max-width:780px;}
    .msg.user{align-self:flex-end;}
    .msg.agent{align-self:flex-start;}
    .bubble{padding:12px 16px;border-radius:12px;font-size:14px;line-height:1.6;}
    .user .bubble{background:var(--accent);color:#fff;border-bottom-right-radius:4px;}
    .agent .bubble{background:var(--surface);border:1px solid var(--border);border-bottom-left-radius:4px;white-space:pre-wrap;}
    .sources{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;}
    .chip{font-size:11px;padding:2px 8px;border-radius:4px;background:rgba(99,102,241,.15);color:var(--accent);}
    .thinking{color:var(--dim);font-style:italic;font-size:13px;}
    footer{padding:16px 24px;border-top:1px solid var(--border);background:var(--surface);}
    #row{display:flex;gap:10px;}
    textarea{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-family:'Inter',sans-serif;font-size:14px;outline:none;resize:none;}
    textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(99,102,241,.15);}
    button{width:40px;height:40px;border-radius:8px;border:0;background:var(--accent);color:#fff;cursor:pointer;font-size:18px;display:grid;place-items:center;}
    button:hover{opacity:.85;}
    .shortcuts{margin-top:8px;display:flex;gap:8px;}
    .sc{font-size:11px;padding:3px 8px;border-radius:4px;background:var(--border);color:var(--dim);cursor:pointer;}
    .sc:hover{background:var(--accent);color:#fff;}
  </style>
</head>
<body>
<header>
  <div class="logo">AI</div>
  <h1>Analista Tech — Agente</h1>
  <div id="dot"></div>
</header>
<div id="msgs">
  <div class="msg agent"><div class="bubble">👋 Ciao. Sono il tuo analista autonomo.
Posso spiegare segnali, ricercare notizie su singole società, briefing e confronti.

Prova: <code>/briefing</code> o <code>/ticker NVDA</code></div></div>
</div>
<footer>
  <div id="row">
    <textarea id="inp" rows="1" placeholder="Scrivi una domanda..."></textarea>
    <button id="btn">→</button>
  </div>
  <div class="shortcuts">
    <span class="sc" onclick="send('/briefing')">📊 Briefing</span>
    <span class="sc" onclick="send('top 5 segnali oggi')">🔥 Top 5</span>
    <span class="sc" onclick="send('società con accumulo attivo')">📈 Accumulo</span>
    <span class="sc" onclick="send('earnings imminenti con buy signal')">⚡ Catalyst</span>
  </div>
</footer>
<script>
  const ticker = new URLSearchParams(location.search).get('ticker');
  const msgs = document.getElementById('msgs');
  const inp  = document.getElementById('inp');

  function addMsg(role, html, sources=[]) {
    const d = document.createElement('div');
    d.className = `msg ${role}`;
    d.innerHTML = `<div class="bubble">${html}</div>`;
    if(sources.length){
      const s=document.createElement('div'); s.className='sources';
      sources.forEach(src=>{
        const c=document.createElement('span'); c.className='chip';
        c.title=`${src.source} — ${src.date}`;
        c.textContent=`${(src.title||'').substring(0,40)}… (${src.significance}/10)`;
        s.appendChild(c);
      }); d.appendChild(s);
    }
    msgs.appendChild(d); msgs.scrollTop=msgs.scrollHeight; return d;
  }

  async function send(msg) {
    if(!msg.trim()) return;
    addMsg('user', msg.replace(/\n/g,'<br>'));
    inp.value='';
    const t = addMsg('agent','<span class="thinking">🤔 Sto analizzando…</span>');
    try {
      const r = await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:msg, ticker:ticker||undefined})});
      const d = await r.json();
      t.querySelector('.bubble').innerHTML = d.response.replace(/\n/g,'<br>');
      if(d.sources?.length){
        const s=document.createElement('div'); s.className='sources';
        d.sources.forEach(src=>{
          const c=document.createElement('span'); c.className='chip';
          c.textContent=`${(src.title||'').substring(0,35)}… (${src.significance}/10)`;
          s.appendChild(c);
        }); t.appendChild(s);
      }
    } catch(e){ t.querySelector('.bubble').textContent='⚠️ Errore di connessione.'; }
    msgs.scrollTop=msgs.scrollHeight;
  }

  document.getElementById('btn').addEventListener('click',()=>send(inp.value));
  inp.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send(inp.value);}});
  if(ticker) send(`Analisi completa di ${ticker}`);
</script>
</body>
</html>
```

- [ ] **Step 2: Visual test**
```bash
uvicorn agent:app --host 0.0.0.0 --port 8080 &
open http://localhost:8080
# Verify: dark UI loads, shortcuts visible, no console errors
kill %1
```

- [ ] **Step 3: Commit**
```bash
git add templates/chat.html
git commit -m "Add dark chat UI with shortcuts, source chips, ticker auto-brief"
```

---

### Task 7: launchd jobs — agent + ngrok autostart

**Files:**
- Create: `launchd/com.analista.agent.plist`
- Create: `launchd/com.analista.ngrok.plist`
- Modify: `launchd/install.sh`

- [ ] **Step 1: Create `launchd/com.analista.agent.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.analista.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/pietrosabbatini/Desktop/Analista Tech/.venv/bin/python3</string>
        <string>-m</string><string>uvicorn</string>
        <string>agent:app</string>
        <string>--host</string><string>0.0.0.0</string>
        <string>--port</string><string>8080</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/pietrosabbatini/Desktop/Analista Tech</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key>
    <string>/Users/pietrosabbatini/Desktop/Analista Tech/data/agent-server.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/pietrosabbatini/Desktop/Analista Tech/data/agent-server.error.log</string>
</dict>
</plist>
```

- [ ] **Step 2: Create `launchd/com.analista.ngrok.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.analista.ngrok</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/ngrok</string>
        <string>http</string><string>8080</string>
        <string>--log</string>
        <string>/Users/pietrosabbatini/Desktop/Analista Tech/data/ngrok.log</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/pietrosabbatini/Desktop/Analista Tech</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>
```

- [ ] **Step 3: Append to `launchd/install.sh`**

Add these lines at the end of the existing script:
```bash
cp "$PROJECT_DIR/launchd/com.analista.agent.plist"  "$LAUNCH_AGENTS/"
cp "$PROJECT_DIR/launchd/com.analista.ngrok.plist"   "$LAUNCH_AGENTS/"
launchctl load "$LAUNCH_AGENTS/com.analista.agent.plist"
launchctl load "$LAUNCH_AGENTS/com.analista.ngrok.plist"
echo "Agent + ngrok loaded."
launchctl list | grep analista
```

- [ ] **Step 4: Commit**
```bash
git add launchd/com.analista.agent.plist launchd/com.analista.ngrok.plist launchd/install.sh
git commit -m "Add launchd jobs for FastAPI agent and ngrok tunnel"
```

---

### Task 8: Integration + ngrok setup

**Files:**
- Modify: `.env` (add NGROK_URL)

- [ ] **Step 1: Register ngrok free account**

Go to https://dashboard.ngrok.com/signup → get authtoken → run:
```bash
ngrok config add-authtoken <your-token>
```

- [ ] **Step 2: Start agent + ngrok**

```bash
cd "/Users/pietrosabbatini/Desktop/Analista Tech" && source .venv/bin/activate
uvicorn agent:app --host 0.0.0.0 --port 8080 &
ngrok http 8080
# Note URL shown: e.g. https://abc123.ngrok-free.app
```

- [ ] **Step 3: Add NGROK_URL to .env**
```bash
echo "NGROK_URL=https://abc123.ngrok-free.app" >> .env
```

- [ ] **Step 4: Run full test suite**
```bash
pytest tests/ -q
```
Expected: 21+ passed

- [ ] **Step 5: End-to-end test via ngrok**
```bash
curl -s -X POST https://abc123.ngrok-free.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"briefing mattutino"}' | python3 -m json.tool
```
Expected: `{"response": "...", "sources": [...]}`

- [ ] **Step 6: Install launchd**
```bash
bash "/Users/pietrosabbatini/Desktop/Analista Tech/launchd/install.sh"
launchctl list | grep analista
```
Expected: 4 jobs listed (tech, xscan, agent, ngrok)

- [ ] **Step 7: Final commit + push**
```bash
git add .env.template
git commit -m "Integration complete: agent chat + ChromaDB memory + news alerts via ngrok"
git push
```
