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
