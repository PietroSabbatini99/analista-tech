from unittest.mock import patch, MagicMock
import pandas as pd
from modules.collector import fetch_financial_snapshot, fetch_edgar_filings


def _mock_ticker(info_override=None, hist_empty=False):
    mock = MagicMock()
    mock.info = {
        "totalRevenue": 60_000_000_000,
        "revenueGrowth": 0.35,
        "grossMargins": 0.72,
        "totalCash": 10_000_000_000,
        "priceToSalesTrailing12Months": 25.0,
        "marketCap": 3_000_000_000_000,
        **(info_override or {}),
    }
    if hist_empty:
        mock.history.return_value = pd.DataFrame()
    else:
        dates = pd.date_range("2025-05-01", periods=60, freq="B")
        mock.history.return_value = pd.DataFrame({
            "Close":  [100 + i * 0.5 for i in range(60)],
            "Volume": [50_000_000] * 60,
        }, index=dates)
    return mock


def test_fetch_financial_snapshot_returns_expected_keys():
    with patch("modules.collector.yf.Ticker", return_value=_mock_ticker()):
        result = fetch_financial_snapshot("NVDA")
    assert result["ticker"] == "NVDA"
    assert "revenue_growth" in result
    assert "gross_margin" in result
    assert "momentum_20_60" in result
    assert "volume_spike" in result


def test_fetch_financial_snapshot_handles_missing_data():
    with patch("modules.collector.yf.Ticker", return_value=_mock_ticker(
        info_override={"totalRevenue": None, "revenueGrowth": None},
        hist_empty=True
    )):
        result = fetch_financial_snapshot("BADTICKER")
    assert result["revenue_growth"] == 0.0
    assert result["momentum_20_60"] == 0.0


def test_fetch_edgar_filings_returns_list():
    fake_response = {"hits": {"hits": [
        {"_source": {"period_of_report": "2026-04-01",
                     "display_names": ["NVIDIA Corp"],
                     "file_date": "2026-04-02",
                     "form_type": "8-K"}},
    ]}}
    with patch("modules.collector.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake_response
        filings = fetch_edgar_filings("NVIDIA", days=30)
    assert isinstance(filings, list)
    assert filings[0]["form_type"] == "8-K"
