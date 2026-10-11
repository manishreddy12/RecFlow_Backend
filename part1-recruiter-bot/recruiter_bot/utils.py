import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

AVAILABILITY_ALIASES = {
    "immediate": "immediate",
    "immediately": "immediate",
    "now": "immediate",
    "2 weeks": "2_weeks",
    "2_weeks": "2_weeks",
    "2-weeks": "2_weeks",
    "two weeks": "2_weeks",
    "not looking": "not_looking",
    "not_looking": "not_looking",
    "not-looking": "not_looking",
}


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def normalize_tag(value):
    return "-".join(value.strip().lower().replace("_", " ").split())


def normalize_tags(values):
    seen = {}
    for value in values:
        tag = normalize_tag(value)
        if tag:
            seen[tag] = None
    return list(seen)


def normalize_availability(value):
    return AVAILABILITY_ALIASES.get(" ".join(value.strip().lower().split()))
