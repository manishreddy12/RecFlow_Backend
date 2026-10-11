# SQL Detective (Part 2)

- `schema_and_seed.sql`: the given tables and data, unchanged
- `sql_detective.sql`: answers, one query per question
- `run_queries.py`: loads everything into in-memory SQLite and prints the results

```bash
python run_queries.py
```

Notes:
- Ananya Rao is in applicants twice (ids 1 and 2) with slightly different emails.
- There's no applications table, so "applied to a posting" means having an interview for that posting.
- Postings 1, 2 and 7 all have the title "Backend Engineer I" but are different postings.
- Q5 uses `RANK()`, so if two recruiters tie in a department, both are shown.
- Only tested on SQLite.
