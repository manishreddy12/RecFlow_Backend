import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent


def main():
    conn = sqlite3.connect(":memory:")
    conn.executescript((HERE / "schema_and_seed.sql").read_text(encoding="utf-8"))
    sql = (HERE / "sql_detective.sql").read_text(encoding="utf-8")
    parts = re.split(r"^(-- Q\d.*)$", sql, flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        print(parts[i].strip())
        cur = conn.execute(parts[i + 1].strip())
        print([d[0] for d in cur.description])
        for row in cur.fetchall():
            print(row)
        print()


if __name__ == "__main__":
    main()
