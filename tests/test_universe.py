import yaml
import tempfile
import os
from modules.universe import load_universe


def _write_config(tickers):
    cfg = {
        "universe": {"tickers": tickers},
        "alerts": {}, "rss_feeds": [], "x_accounts": [], "report": {}
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(cfg, f)
        return f.name


def test_load_universe_returns_list_of_dicts():
    cfg_path = _write_config([
        {"ticker": "NVDA", "name": "NVIDIA", "sector": "chip"},
        {"ticker": "AMD",  "name": "AMD",    "sector": "chip"},
    ])
    try:
        companies = load_universe(cfg_path)
        assert len(companies) == 2
        assert companies[0]["ticker"] == "NVDA"
        assert companies[0]["name"] == "NVIDIA"
        assert companies[0]["sector"] == "chip"
    finally:
        os.unlink(cfg_path)


def test_load_universe_adds_cap_tier_key():
    cfg_path = _write_config([{"ticker": "NVDA", "name": "NVIDIA", "sector": "chip"}])
    try:
        companies = load_universe(cfg_path)
        assert "cap_tier" in companies[0]
    finally:
        os.unlink(cfg_path)
