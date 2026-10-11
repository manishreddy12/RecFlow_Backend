# Recruiter Bot (Part 1)

Backend that loads candidates and jobs and ranks matches both ways. Python + Flask + SQLite, all SQL handwritten (no ORM), see `recruiter_bot/schema.sql` and `recruiter_bot/queries.py`.

## Setup

```bash
cd part1-recruiter-bot
python -m venv .venv
.venv\Scripts\activate        # mac/linux: source .venv/bin/activate
pip install -r requirements.txt
python seed.py --reset
python app.py
```

Runs on http://127.0.0.1:5000.

## Tests (curl)

Tests are plain curl calls. Each one checks the HTTP status and part of the response. Start the server on a freshly seeded DB (`python seed.py --reset`, then `python app.py`), then in another terminal, from `part1-recruiter-bot`:

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File tests\curl_tests.ps1
```

```bash
# macOS / Linux / Git Bash
bash tests/curl_tests.sh
```

On Windows, don't run `bash ...` from PowerShell: `bash` there is WSL, not Git Bash. Use the `.ps1` script, or open a Git Bash terminal. Both scripts run the same 19 checks.

It covers health, listing, matches in both directions, bad query params (400), unknown ids (404), adding candidates/jobs (201), validation errors (400) and duplicates (409). Names in the POST tests get a timestamp, so the script can be re-run.

## Endpoints

- `GET /health`
- `GET /candidates`, `GET /candidates/{id}`, `POST /candidates` (object or list)
- `GET /jobs`, `GET /jobs/{id}`, `POST /jobs` (object or list)
- `GET /jobs/{id}/matches?limit=10&min_score=0`
- `GET /candidates/{id}/matches?limit=10&min_score=0`
- `POST /matches/recompute`

```bash
curl "http://localhost:5000/jobs/1/matches?limit=3"
curl "http://localhost:5000/candidates/1/matches"
curl -X POST http://localhost:5000/candidates -H "Content-Type: application/json" \
  -d '{"name":"Hercule P.","skills":["deduction","Pattern Recognition"],"experience_years":30,"availability":"Immediate","traits":["analytical"]}'
curl -X POST http://localhost:5000/jobs -H "Content-Type: application/json" \
  -d '{"title":"Chemistry Consultant","required_skills":["chemistry"],"min_experience":5}'
```

Every match has a `score` (0-100), a `reason` string and a `breakdown` of the parts.

## Decisions

**Scoring.** score = 100 × (0.55·skills + 0.25·experience + 0.12·culture + 0.08·availability)

- skills: how many of the job's required skills the candidate has
- experience: full marks if at or above the minimum, partial if below. No extra credit for being way above the minimum, so a 20-year candidate doesn't automatically beat a 10-year one on a 2-year role.
- culture: job culture keywords matched by candidate traits (a trait also matches a word inside a hyphenated keyword, so `calm` matches `calm-under-pressure`)
- availability: immediate 1, 2 weeks 0.7, not looking 0.2

Skills get the biggest weight since they matter most. Culture and availability are small, mostly to separate similar candidates. If a candidate has none of the required skills, the score is capped at 20 so experience alone can't push them up.

**Schema.** Skills are their own table, with candidate_skills and job_skills join tables, so overlap is a join on skill id. Input gets normalised first ("Public Speaking" → `public-speaking`). Traits and culture keywords are just text tables. Name/title are UNIQUE, so re-adding the same person gives 409.

**Matches are stored**, not computed on every request. When a candidate or job is added, its matches get computed and saved in the `matches` table, and the GET endpoints just read and sort it. Reads are cheap, but if the weights change you have to call `/matches/recompute`.

**Seed** uses the same ingest functions as the POST endpoints.

## Incomplete

- No update or delete endpoints for candidates/jobs. Records can only be added.
- No pagination beyond `limit`, and no auth.
- Tests are only the curl script. There are no unit tests for the scoring functions themselves.

## Known bugs

- **Batch POSTs aren't all-or-nothing.** If item 3 of 5 is a duplicate, you get a 409 but items 1–2 are already saved.
  *Fix:* `ingest_candidates` / `ingest_jobs` open a transaction (`with conn:`) per item inside the loop. Move the `with conn:` outside the loop so the whole batch commits or rolls back together.
- **Equal scores have no tie-breaker.** Matches are ordered by `score` only, so candidates with the same score can come back in any order, and `limit` may cut a different one each time.

## What I'd improve

Clean up the code a bit and add some comments, add a few more tests, and make this README clearer.

## AI usage

I used an AI coding assistant (Anti Gravity) while building this. It helped scaffold the Flask app, the SQL and the tests from the assignment spec. I architected the app, ran it and tested the endpoints myself.

## Part 2

See `../part2-sql-detective/sql_detective.sql`.
