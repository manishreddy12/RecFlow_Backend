import argparse
import json
import os
from pathlib import Path

from recruiter_bot import DEFAULT_DB_PATH
from recruiter_bot.routes import DuplicateError, ingest_candidates, ingest_jobs
from recruiter_bot.utils import get_connection, init_schema

DATA_DIR = Path(__file__).with_name("data")


def seed(db_path):
    conn = get_connection(db_path)
    try:
        init_schema(conn)
        jobs = json.loads((DATA_DIR / "jobs.json").read_text(encoding="utf-8"))
        candidates = json.loads((DATA_DIR / "candidates.json").read_text(encoding="utf-8"))
        job_ids = ingest_jobs(conn, jobs)
        candidate_ids = ingest_candidates(conn, candidates)
        return len(job_ids), len(candidate_ids)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("RECRUITER_BOT_DB", DEFAULT_DB_PATH))
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    if args.reset and os.path.exists(args.db):
        os.remove(args.db)
    try:
        n_jobs, n_candidates = seed(args.db)
    except DuplicateError:
        raise SystemExit("Seed data is already loaded. Use --reset to start from scratch.")
    print(f"Seeded {n_jobs} jobs and {n_candidates} candidates into {args.db}")


if __name__ == "__main__":
    main()
