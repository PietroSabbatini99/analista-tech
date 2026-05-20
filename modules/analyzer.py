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
- Cap Tier: {cap_tier} | Market Cap: ${market_cap:,.0f}
- Revenue (TTM): ${total_revenue:,.0f} | Net Income: ${net_income:,.0f}
- EBITDA: ${ebitda:,.0f} | Free Cash Flow: ${free_cash_flow:,.0f}
- Gross Margin: {gross_margin:.1f}% | Operating Margin: {operating_margin:.1f}% | Net Margin: {net_margin:.1f}%
- ROE: {roe:.1f}% | ROA: {roa:.1f}% | D/E: {debt_to_equity:.2f}x
- P/E: {trailing_pe:.1f}x (sector avg: {sector_avg_pe:.1f}x) | EV/EBITDA: {ev_ebitda:.1f}x | P/B: {price_to_book:.1f}x
- P/S: {price_to_sales:.1f}x | Current Ratio: {current_ratio:.2f}
- 1M Price Performance: {perf_1m:+.1f}%
- Price Momentum (20d vs 60d avg): {momentum_20_60:+.1%}
- Price Change (20d): {price_change_20:+.1%}
- Volume Spike (20d vs 60d avg): {volume_spike:+.1%}
- Accumulation Signal: {accumulation} (price flat + volume rising = smart money building)
- Trending on Yahoo Finance: {is_trending} (retail attention — currently being searched)

ANALYST CONSENSUS ({analyst_count} analysts):
- Target Price: ${analyst_target:.2f} | Upside vs current: {analyst_upside:+.1f}%

SHORT INTEREST:
- Short % of Float: {short_percent:.1f}% | Days to Cover: {short_ratio:.1f}

EARNINGS CALENDAR:
- Next Earnings: {next_earnings} ({days_until_earnings} days away)

INSIDER ACTIVITY (last 30d):
- Form 4 filings: {insider_filings_30d}

INSTITUTIONAL OWNERSHIP:
- Top holders total: {institutional_pct:.1f}% | Largest: {top_holder}

TRADINGVIEW TECHNICAL ANALYSIS:
- Signal: {tv_recommendation} (Buy: {tv_buy}, Sell: {tv_sell}, Neutral: {tv_neutral})
- RSI (14): {tv_rsi}
- MACD: {tv_macd}
- EMA20 vs EMA50 cross: {tv_ema_cross:+.2f}%

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
    tv_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tv = tv_data or {"recommendation": "N/A", "buy": 0, "sell": 0, "neutral": 0,
                     "rsi": 50.0, "macd": 0.0, "ema_cross": 0.0}
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _SCORE_PROMPT.format(
        name=financial.get("name", financial["ticker"]),
        ticker=financial["ticker"],
        revenue_growth=financial["revenue_growth"],
        total_cash=financial.get("total_cash", 0.0),
        price_to_sales=financial.get("price_to_sales", 0.0),
        market_cap=financial.get("market_cap", 0.0),
        trailing_pe=financial.get("trailing_pe", 0.0),
        forward_pe=financial.get("forward_pe", 0.0),
        sector_avg_pe=financial.get("sector_avg_pe", 0.0),
        # TV batch fundamentals
        total_revenue=financial.get("total_revenue", 0.0),
        net_income=financial.get("net_income", 0.0),
        ebitda=financial.get("ebitda", 0.0),
        free_cash_flow=financial.get("free_cash_flow", 0.0),
        gross_margin=financial.get("gross_margin_tv", financial.get("gross_margin", 0.0)),
        operating_margin=financial.get("operating_margin", 0.0),
        net_margin=financial.get("net_margin", 0.0),
        roe=financial.get("roe", 0.0),
        roa=financial.get("roa", 0.0),
        debt_to_equity=financial.get("debt_to_equity", 0.0),
        ev_ebitda=financial.get("ev_ebitda", 0.0),
        price_to_book=financial.get("price_to_book", 0.0),
        current_ratio=financial.get("current_ratio", 0.0),
        perf_1m=financial.get("perf_1m", 0.0),
        analyst_count=financial.get("analyst_count", 0),
        analyst_target=financial.get("analyst_target", 0.0),
        analyst_upside=financial.get("analyst_upside", 0.0),
        short_percent=financial.get("short_percent", 0.0),
        short_ratio=financial.get("short_ratio", 0.0),
        next_earnings=financial.get("next_earnings") or "N/A",
        days_until_earnings=financial.get("days_until_earnings") or "N/A",
        insider_filings_30d=financial.get("insider_filings_30d", 0),
        institutional_pct=financial.get("institutional_pct", 0.0),
        top_holder=financial.get("top_holder") or "N/A",
        cap_tier=financial.get("cap_tier", "large"),
        is_trending=financial.get("is_trending", False),
        momentum_20_60=financial["momentum_20_60"],
        price_change_20=financial.get("price_change_20", 0.0),
        volume_spike=financial["volume_spike"],
        accumulation=financial.get("accumulation", False),
        tv_recommendation=tv["recommendation"],
        tv_buy=tv["buy"],
        tv_sell=tv["sell"],
        tv_neutral=tv["neutral"],
        tv_rsi=tv["rsi"],
        tv_macd=tv["macd"],
        tv_ema_cross=tv["ema_cross"],
        news_block=_news_block(news_items),
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
    except Exception:
        return {k: 0 for k in ["score_revenue", "score_margins", "score_news",
                                "score_influencer", "score_momentum"]} | {
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
