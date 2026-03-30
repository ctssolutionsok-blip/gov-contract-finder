from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path("gov_contracts.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sam_opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notice_id TEXT UNIQUE,
        title TEXT,
        agency TEXT,
        notice_type TEXT,
        set_aside TEXT,
        naics_code TEXT,
        response_date TEXT,
        state TEXT,
        url TEXT,
        posted_date TEXT,
        raw_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usaspending_awards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        award_id TEXT UNIQUE,
        recipient_name TEXT,
        awarding_agency TEXT,
        naics_code TEXT,
        award_amount REAL,
        start_date TEXT,
        end_date TEXT,
        place_of_performance TEXT,
        raw_json TEXT
    )
    """)

    conn.commit()
    conn.close()

def read_sam_opportunities():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM sam_opportunities", conn)
    conn.close()
    return df

def read_usaspending_awards():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM usaspending_awards", conn)
    conn.close()
    return df