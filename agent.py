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
    return HTMLResponse(p.read_text() if p.exists() else "<h1>chat.html not found — run Task 6</h1>")


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
    try: n_news, n_scores = int(mem.news.count()), int(mem.scores.count())
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
