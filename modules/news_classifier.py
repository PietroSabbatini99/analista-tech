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
