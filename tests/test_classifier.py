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
