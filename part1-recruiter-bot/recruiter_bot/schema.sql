PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS candidates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL UNIQUE,
    experience_years INTEGER NOT NULL CHECK (experience_years >= 0),
    availability     TEXT    NOT NULL CHECK (availability IN ('immediate', '2_weeks', 'not_looking')),
    quirk            TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT    NOT NULL UNIQUE,
    min_experience INTEGER NOT NULL CHECK (min_experience >= 0),
    tagline        TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS skills (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS candidate_skills (
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id     INTEGER NOT NULL REFERENCES skills(id),
    PRIMARY KEY (candidate_id, skill_id)
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id   INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id),
    PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE IF NOT EXISTS candidate_traits (
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    trait        TEXT    NOT NULL,
    PRIMARY KEY (candidate_id, trait)
);

CREATE TABLE IF NOT EXISTS job_culture_keywords (
    job_id  INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    keyword TEXT    NOT NULL,
    PRIMARY KEY (job_id, keyword)
);

CREATE TABLE IF NOT EXISTS matches (
    candidate_id        INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    job_id              INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    score               REAL    NOT NULL,
    skill_score         REAL    NOT NULL,
    experience_score    REAL    NOT NULL,
    culture_score       REAL    NOT NULL,
    availability_score  REAL    NOT NULL,
    matched_skill_count INTEGER NOT NULL,
    matched_skills      TEXT    NOT NULL,
    reason              TEXT    NOT NULL,
    computed_at         TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (candidate_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_job_score       ON matches (job_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_candidate_score ON matches (candidate_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill  ON candidate_skills (skill_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill        ON job_skills (skill_id);
