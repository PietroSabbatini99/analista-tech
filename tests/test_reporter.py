import os
import json
import tempfile
from unittest.mock import patch
from modules.reporter import (
    generate_html_report, generate_md_report,
    save_alerts_json, send_macos_notification
)

SAMPLE = [
    {"ticker": "NVDA", "name": "NVIDIA", "total_score": 88, "score_revenue": 80,
     "score_margins": 75, "score_news": 85, "score_influencer": 70,
     "score_momentum": 90, "reasoning": "Strong.", "narrative": "Thesis."},
    {"ticker": "AMD",  "name": "AMD",    "total_score": 62, "score_revenue": 60,
     "score_margins": 55, "score_news": 65, "score_influencer": 60,
     "score_momentum": 70, "reasoning": "Decent.", "narrative": "AMD."},
]


def test_generate_html_report_creates_file():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "report.html")
        generate_html_report(SAMPLE, out, template_dir="templates")
        assert os.path.exists(out)
        assert "NVDA" in open(out).read()


def test_generate_md_report_creates_file():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "report.md")
        generate_md_report(SAMPLE, out)
        assert os.path.exists(out)
        assert "NVDA" in open(out).read()


def test_save_alerts_json_filters_by_threshold():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "alerts.json")
        save_alerts_json(SAMPLE, out, threshold=75)
        data = json.loads(open(out).read())
        assert any(a["ticker"] == "NVDA" for a in data)
        assert not any(a["ticker"] == "AMD" for a in data)


def test_send_macos_notification_calls_osascript():
    with patch("modules.reporter.subprocess.run") as mock_run:
        send_macos_notification("NVDA", 88, "Partnership announced")
        assert "osascript" in mock_run.call_args[0][0]
