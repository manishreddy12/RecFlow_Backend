import json

from .matching import CandidateProfile, JobProfile


def get_or_create_skill(conn, name):
    conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (name,))
    return conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()["id"]


def insert_candidate(conn, name, experience_years, availability, quirk, skills, traits):
    cur = conn.execute(
        """
        INSERT INTO candidates (name, experience_years, availability, quirk)
        VALUES (?, ?, ?, ?)
        """,
        (name, experience_years, availability, quirk),
    )
    candidate_id = cur.lastrowid
    for skill in skills:
        conn.execute(
            "INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (?, ?)",
            (candidate_id, get_or_create_skill(conn, skill)),
        )
    conn.executemany(
        "INSERT INTO candidate_traits (candidate_id, trait) VALUES (?, ?)",
        [(candidate_id, trait) for trait in traits],
    )
    return candidate_id


def insert_job(conn, title, min_experience, tagline, required_skills, culture_keywords):
    cur = conn.execute(
        "INSERT INTO jobs (title, min_experience, tagline) VALUES (?, ?, ?)",
        (title, min_experience, tagline),
    )
    job_id = cur.lastrowid
    for skill in required_skills:
        conn.execute(
            "INSERT INTO job_skills (job_id, skill_id) VALUES (?, ?)",
            (job_id, get_or_create_skill(conn, skill)),
        )
    conn.executemany(
        "INSERT INTO job_culture_keywords (job_id, keyword) VALUES (?, ?)",
        [(job_id, kw) for kw in culture_keywords],
    )
    return job_id


CANDIDATE_SELECT = """
    SELECT c.id, c.name, c.experience_years, c.availability, c.quirk,
           (SELECT json_group_array(s.name)
              FROM candidate_skills cs JOIN skills s ON s.id = cs.skill_id
             WHERE cs.candidate_id = c.id) AS skills,
           (SELECT json_group_array(ct.trait)
              FROM candidate_traits ct
             WHERE ct.candidate_id = c.id) AS traits
      FROM candidates c
"""

JOB_SELECT = """
    SELECT j.id, j.title, j.min_experience, j.tagline,
           (SELECT json_group_array(s.name)
              FROM job_skills js JOIN skills s ON s.id = js.skill_id
             WHERE js.job_id = j.id) AS required_skills,
           (SELECT json_group_array(k.keyword)
              FROM job_culture_keywords k
             WHERE k.job_id = j.id) AS culture_keywords
      FROM jobs j
"""


def _candidate_row_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "experience_years": row["experience_years"],
        "availability": row["availability"],
        "quirk": row["quirk"],
        "skills": sorted(json.loads(row["skills"])),
        "traits": sorted(json.loads(row["traits"])),
    }


def _job_row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "min_experience": row["min_experience"],
        "tagline": row["tagline"],
        "required_skills": sorted(json.loads(row["required_skills"])),
        "culture_keywords": sorted(json.loads(row["culture_keywords"])),
    }


def list_candidates(conn):
    rows = conn.execute(CANDIDATE_SELECT + " ORDER BY c.id").fetchall()
    return [_candidate_row_to_dict(r) for r in rows]


def get_candidate(conn, candidate_id):
    row = conn.execute(CANDIDATE_SELECT + " WHERE c.id = ?", (candidate_id,)).fetchone()
    return _candidate_row_to_dict(row) if row else None


def list_jobs(conn):
    rows = conn.execute(JOB_SELECT + " ORDER BY j.id").fetchall()
    return [_job_row_to_dict(r) for r in rows]


def get_job(conn, job_id):
    row = conn.execute(JOB_SELECT + " WHERE j.id = ?", (job_id,)).fetchone()
    return _job_row_to_dict(row) if row else None


def to_candidate_profile(c):
    return CandidateProfile(c["id"], c["name"], c["experience_years"], c["availability"],
                            set(c["skills"]), set(c["traits"]))


def to_job_profile(j):
    return JobProfile(j["id"], j["title"], j["min_experience"],
                      set(j["required_skills"]), set(j["culture_keywords"]))


def upsert_matches(conn, results):
    conn.executemany(
        """
        INSERT INTO matches (candidate_id, job_id, score, skill_score, experience_score,
                             culture_score, availability_score, matched_skill_count,
                             matched_skills, reason, computed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT (candidate_id, job_id) DO UPDATE SET
            score               = excluded.score,
            skill_score         = excluded.skill_score,
            experience_score    = excluded.experience_score,
            culture_score       = excluded.culture_score,
            availability_score  = excluded.availability_score,
            matched_skill_count = excluded.matched_skill_count,
            matched_skills      = excluded.matched_skills,
            reason              = excluded.reason,
            computed_at         = excluded.computed_at
        """,
        [
            (r.candidate_id, r.job_id, r.score, r.skill_score, r.experience_score,
             r.culture_score, r.availability_score, r.matched_skill_count,
             json.dumps(r.matched_skills), r.reason)
            for r in results
        ],
    )


def delete_all_matches(conn):
    conn.execute("DELETE FROM matches")


def get_job_matches(conn, job_id, min_score, limit):
    rows = conn.execute(
        """
        SELECT m.candidate_id, c.name AS candidate_name, m.score, m.reason,
               m.skill_score, m.experience_score, m.culture_score, m.availability_score,
               m.matched_skills
          FROM matches m
          JOIN candidates c ON c.id = m.candidate_id
         WHERE m.job_id = ?
           AND m.score >= ?
         ORDER BY m.score DESC
         LIMIT ?
        """,
        (job_id, min_score, limit),
    ).fetchall()
    return [_match_row_to_dict(r, rank) for rank, r in enumerate(rows)]


def get_candidate_matches(conn, candidate_id, min_score, limit):
    rows = conn.execute(
        """
        SELECT m.job_id, j.title AS job_title, m.score, m.reason,
               m.skill_score, m.experience_score, m.culture_score, m.availability_score,
               m.matched_skills
          FROM matches m
          JOIN jobs j ON j.id = m.job_id
         WHERE m.candidate_id = ?
           AND m.score >= ?
         ORDER BY m.score DESC
         LIMIT ?
        """,
        (candidate_id, min_score, limit),
    ).fetchall()
    return [_match_row_to_dict(r, rank) for rank, r in enumerate(rows)]


def _match_row_to_dict(row, rank):
    d = dict(row)
    breakdown = {
        "skills": d.pop("skill_score"),
        "experience": d.pop("experience_score"),
        "culture": d.pop("culture_score"),
        "availability": d.pop("availability_score"),
    }
    d["matched_skills"] = json.loads(d["matched_skills"])
    return {"rank": rank, **d, "breakdown": breakdown}
