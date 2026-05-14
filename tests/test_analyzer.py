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
