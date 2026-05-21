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
