import sqlite3
import os
import logging
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "bets.db")

def get_db_connection():
    """Returns a connection to the SQLite database."""
    # Ensure the directory exists if DB_PATH contains subdirectories
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    
    # Increase timeout to 20 seconds to avoid "database is locked" errors under load
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    
    # Enable Write-Ahead Logging (WAL) which allows concurrent reading and writing
    conn.execute('PRAGMA journal_mode=WAL;')
    
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't exist."""
    conn = get_db_connection()
    c = conn.cursor()

    # Table for tracking evaluated matches and edges
    c.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            league TEXT,
            kickoff DATETIME,
            home_team TEXT,
            away_team TEXT,
            home_xg REAL,
            away_xg REAL,
            status TEXT DEFAULT 'PENDING',
            home_score INTEGER,
            away_score INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table for tracking bets placed
    c.execute('''
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            market TEXT,
            selection TEXT,
            bookmaker TEXT,
            fair_odds REAL,
            best_odds REAL,
            edge REAL,
            kelly_stake REAL,
            confidence TEXT,
            bet_status TEXT DEFAULT 'PENDING',
            pnl REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(match_id) REFERENCES matches(id)
        )
    ''')

    # Table for rate limiting API calls persistently
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_usage (
            service TEXT,
            call_date DATE,
            call_count INTEGER,
            PRIMARY KEY (service, call_date)
        )
    ''')

    conn.commit()
    conn.close()
    logging.info(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
