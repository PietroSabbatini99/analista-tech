from unittest.mock import patch, MagicMock
from modules.researcher import fetch_exa_news, fetch_rss_news, fetch_x_mentions


def test_fetch_exa_news_returns_list():
    mock_exa = MagicMock()
    mock_result = MagicMock()
    mock_result.results = [
        MagicMock(title="NVDA signs AI deal", url="https://example.com/1",
                  published_date="2026-05-09", text="NVIDIA announced..."),
    ]
    mock_exa.search_and_contents.return_value = mock_result

    with patch("modules.researcher.Exa", return_value=mock_exa):
        items = fetch_exa_news("NVIDIA", "NVDA", exa_api_key="fake")

    assert isinstance(items, list)
    assert items[0]["title"] == "NVDA signs AI deal"
    assert items[0]["source"] == "exa"


def test_fetch_rss_news_no_crash_on_empty():
    fake_feed = MagicMock()
    fake_feed.entries = []
    with patch("modules.researcher.feedparser.parse", return_value=fake_feed):
        items = fetch_rss_news(
            "NVIDIA", "NVDA",
            feeds=[{"url": "https://fake.rss", "name": "FakeFeed"}]
        )
    assert isinstance(items, list)


def test_fetch_x_mentions_returns_list():
    mock_exa = MagicMock()
    mock_result = MagicMock()
    mock_result.results = [
        MagicMock(title="Jensen Huang on NVDA", url="https://x.com/jensen_huang/status/1",
                  published_date="2026-05-09", text="NVIDIA AI chips dominate..."),
    ]
    mock_exa.search_and_contents.return_value = mock_result

    with patch("modules.researcher.Exa", return_value=mock_exa):
        items = fetch_x_mentions("NVIDIA", "NVDA", exa_api_key="fake", accounts=["jensen_huang"])

    assert isinstance(items, list)
    assert items[0]["source"] == "x"
