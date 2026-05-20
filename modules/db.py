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
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker              TEXT NOT NULL,
            date                TEXT NOT NULL,
            score_revenue       REAL,
            score_margins       REAL,
            score_news          REAL,
            score_influencer    REAL,
            score_momentum      REAL,
            total_score         REAL,
            narrative           TEXT,
            name                TEXT,
            sector              TEXT,
            cap_tier            TEXT,
            accumulation        INTEGER DEFAULT 0,
            price_change_20     REAL    DEFAULT 0,
            trailing_pe         REAL    DEFAULT 0,
            forward_pe          REAL    DEFAULT 0,
            sector_avg_pe       REAL    DEFAULT 0,
            analyst_target      REAL    DEFAULT 0,
            analyst_upside      REAL    DEFAULT 0,
            analyst_count       INTEGER DEFAULT 0,
            short_percent       REAL    DEFAULT 0,
            short_ratio         REAL    DEFAULT 0,
            next_earnings       TEXT,
            days_until_earnings INTEGER,
            insider_filings_30d INTEGER DEFAULT 0,
            institutional_pct   REAL    DEFAULT 0,
            top_holder          TEXT,
            tv_recommendation   TEXT,
            tv_rsi              REAL    DEFAULT 50,
            tv_macd             REAL    DEFAULT 0,
            tv_ema_cross        REAL    DEFAULT 0,
            tv_buy              INTEGER DEFAULT 0,
            tv_sell             INTEGER DEFAULT 0,
            earnings_history    TEXT,
            is_trending         INTEGER DEFAULT 0,
            gross_margin        REAL    DEFAULT 0,
            operating_margin    REAL    DEFAULT 0,
            net_margin          REAL    DEFAULT 0,
            roe                 REAL    DEFAULT 0,
            roa                 REAL    DEFAULT 0,
            ev_ebitda           REAL    DEFAULT 0,
            price_to_book       REAL    DEFAULT 0,
            free_cash_flow      REAL    DEFAULT 0,
            total_revenue       REAL    DEFAULT 0,
            net_income          REAL    DEFAULT 0,
            ebitda              REAL    DEFAULT 0,
            debt_to_equity      REAL    DEFAULT 0,
            current_ratio       REAL    DEFAULT 0,
            perf_1m             REAL    DEFAULT 0,
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

    # Migrate existing DB — add new columns if missing
    new_cols = [
        ("name",                "TEXT"),
        ("sector",              "TEXT"),
        ("cap_tier",            "TEXT"),
        ("accumulation",        "INTEGER DEFAULT 0"),
        ("price_change_20",     "REAL DEFAULT 0"),
        ("trailing_pe",         "REAL DEFAULT 0"),
        ("forward_pe",          "REAL DEFAULT 0"),
        ("sector_avg_pe",       "REAL DEFAULT 0"),
        ("analyst_target",      "REAL DEFAULT 0"),
        ("analyst_upside",      "REAL DEFAULT 0"),
        ("analyst_count",       "INTEGER DEFAULT 0"),
        ("short_percent",       "REAL DEFAULT 0"),
        ("short_ratio",         "REAL DEFAULT 0"),
        ("next_earnings",       "TEXT"),
        ("days_until_earnings", "INTEGER"),
        ("insider_filings_30d", "INTEGER DEFAULT 0"),
        ("institutional_pct",   "REAL DEFAULT 0"),
        ("top_holder",          "TEXT"),
        ("tv_recommendation",   "TEXT"),
        ("tv_rsi",              "REAL DEFAULT 50"),
        ("tv_macd",             "REAL DEFAULT 0"),
        ("tv_ema_cross",        "REAL DEFAULT 0"),
        ("tv_buy",              "INTEGER DEFAULT 0"),
        ("tv_sell",             "INTEGER DEFAULT 0"),
        # earnings + trending (missing from previous migration)
        ("earnings_history",    "TEXT"),
        ("is_trending",         "INTEGER DEFAULT 0"),
        # TV batch fundamentals
        ("gross_margin",        "REAL DEFAULT 0"),
        ("operating_margin",    "REAL DEFAULT 0"),
        ("net_margin",          "REAL DEFAULT 0"),
        ("roe",                 "REAL DEFAULT 0"),
        ("roa",                 "REAL DEFAULT 0"),
        ("ev_ebitda",           "REAL DEFAULT 0"),
        ("price_to_book",       "REAL DEFAULT 0"),
        ("free_cash_flow",      "REAL DEFAULT 0"),
        ("total_revenue",       "REAL DEFAULT 0"),
        ("net_income",          "REAL DEFAULT 0"),
        ("ebitda",              "REAL DEFAULT 0"),
        ("debt_to_equity",      "REAL DEFAULT 0"),
        ("current_ratio",       "REAL DEFAULT 0"),
        ("perf_1m",             "REAL DEFAULT 0"),
    ]
    for col, col_type in new_cols:
        try:
            conn.execute(f"ALTER TABLE daily_scores ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # column already exists
    conn.commit()
    conn.close()
