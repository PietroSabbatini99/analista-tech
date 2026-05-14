import os
import json
import subprocess
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from typing import Any


def generate_html_report(
    scores: list[dict[str, Any]],
    output_path: str,
    template_dir: str = "templates",
    sector_correlations: dict | None = None,
) -> None:
    env  = Environment(loader=FileSystemLoader(template_dir))
    html = env.get_template("dashboard.html").render(
        companies=scores,
        run_date=date.today().isoformat(),
        sector_correlations=sector_correlations or {},
    )
    with open(output_path, "w") as f:
        f.write(html)


def generate_md_report(scores: list[dict[str, Any]], output_path: str) -> None:
    lines = [
        f"# AI Sector Analyst — {date.today().isoformat()}", "",
        "## Top Signals", "",
        "| Ticker | Score | Signal |", "|--------|-------|--------|",
    ]
    for c in scores[:20]:
        lines.append(f"| **{c['ticker']}** | {c['total_score']:.0f} | {c.get('reasoning','')[:80]} |")
    lines += ["", "## Full Universe", "", "| Ticker | Score |", "|--------|-------|"]
    for c in scores:
        lines.append(f"| {c['ticker']} | {c['total_score']:.0f} |")
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def save_alerts_json(
    scores: list[dict[str, Any]], output_path: str, threshold: float = 75.0
) -> None:
    with open(output_path, "w") as f:
        json.dump([c for c in scores if c["total_score"] >= threshold], f, indent=2)


def send_macos_notification(ticker: str, score: float, reason: str) -> None:
    msg    = f"{ticker} — Score {score:.0f}: {reason[:60]}"
    script = f'display notification "{msg}" with title "AI Analyst 🔬" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def send_weekly_email(
    scores: list[dict[str, Any]],
    gmail_address: str,
    app_password: str,
    to_address: str,
    template_dir: str = "templates",
) -> None:
    env  = Environment(loader=FileSystemLoader(template_dir))
    html = env.get_template("email.html").render(
        companies=scores, run_date=date.today().isoformat()
    )
    msg             = MIMEMultipart("alternative")
    msg["Subject"]  = f"AI Analyst Weekly — {date.today().isoformat()}"
    msg["From"]     = gmail_address
    msg["To"]       = to_address
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(gmail_address, app_password)
        s.sendmail(gmail_address, to_address, msg.as_string())
