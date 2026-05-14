import yaml
from typing import Any


def load_universe(config_path: str) -> list[dict[str, Any]]:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    companies = []
    for entry in cfg["universe"]["tickers"]:
        companies.append({
            "ticker":   entry["ticker"],
            "name":     entry["name"],
            "sector":   entry.get("sector", "unknown"),
            "cap_tier": entry.get("cap_tier", "unknown"),
        })
    return companies
