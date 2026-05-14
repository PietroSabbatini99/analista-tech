import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            ticker      TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            sector      TEXT NOT NULL,
            cap_tier    TEXT,
            added_at    TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_scores (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker            TEXT NOT NULL,
            date              TEXT NOT NULL,
            score_revenue     REAL,
            score_margins     REAL,
            score_news        REAL,
            score_influencer  REAL,
            score_momentum    REAL,
            total_score       REAL,
            narrative         TEXT,
            UNIQUE(ticker, date)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            date        TEXT NOT NULL,
            alert_type  TEXT NOT NULL,
            message     TEXT NOT NULL,
            notified    INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS news_cache (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker  TEXT NOT NULL,
            date    TEXT NOT NULL,
            source  TEXT,
            title   TEXT,
            url     TEXT,
            snippet TEXT,
            UNIQUE(ticker, url)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_scores_ticker_date
            ON daily_scores(ticker, date);

        CREATE INDEX IF NOT EXISTS idx_alerts_date
            ON alerts(date);
    """)
    conn.commit()
    conn.close()
