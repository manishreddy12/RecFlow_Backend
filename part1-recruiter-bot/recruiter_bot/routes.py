import sqlite3

from flask import Blueprint, current_app, g, jsonify, request

from . import queries
from .matching import score_match
from .utils import get_connection, normalize_availability, normalize_tags

bp = Blueprint("api", __name__)


# All routes and their methods
class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


class DuplicateError(Exception):
    pass


def get_db():
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def error(status, message, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def _require_text(payload, key, errors, max_len=200):
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        errors[key] = "is required"
        return None
    if len(value.strip()) > max_len:
        errors[key] = f"must be at most {max_len} characters"
        return None
    return value.strip()


def _require_non_negative_int(payload, key, errors):
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        errors[key] = "must be a non-negative integer"
        return None
    return value


def _tag_list(payload, key, errors, required):
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        errors[key] = "must be a list of strings"
        return []
    tags = normalize_tags(value)
    if required and not tags:
        errors[key] = "must contain at least one value"
    return tags


def validate_candidate(payload):
    if not isinstance(payload, dict):
        raise ValidationError({"body": "each candidate must be a JSON object"})
    errors = {}
    name = _require_text(payload, "name", errors)
    years = _require_non_negative_int(payload, "experience_years", errors)
    raw_availability = payload.get("availability")
    availability = normalize_availability(raw_availability) if isinstance(raw_availability, str) else None
    if availability is None:
        errors["availability"] = "must be one of: Immediate, 2 weeks, Not looking"
    skills = _tag_list(payload, "skills", errors, required=True)
    traits = _tag_list(payload, "traits", errors, required=False)
    quirk = payload.get("quirk")
    if quirk is not None and not isinstance(quirk, str):
        errors["quirk"] = "must be a string"
    if errors:
        raise ValidationError(errors)
    return {"name": name, "experience_years": years, "availability": availability,
            "quirk": quirk, "skills": skills, "traits": traits}


def validate_job(payload):
    if not isinstance(payload, dict):
        raise ValidationError({"body": "each job must be a JSON object"})
    errors = {}
    title = _require_text(payload, "title", errors)
    min_exp = _require_non_negative_int(payload, "min_experience", errors)
    skills = _tag_list(payload, "required_skills", errors, required=True)
    keywords = _tag_list(payload, "culture_keywords", errors, required=False)
    tagline = payload.get("tagline")
    if tagline is not None and not isinstance(tagline, str):
        errors["tagline"] = "must be a string"
    if errors:
        raise ValidationError(errors)
    return {"title": title, "min_experience": min_exp, "tagline": tagline,
            "required_skills": skills, "culture_keywords": keywords}


def _recompute_for_candidate(conn, candidate_id):
    candidate = queries.to_candidate_profile(queries.get_candidate(conn, candidate_id))
    jobs = [queries.to_job_profile(j) for j in queries.list_jobs(conn)]
    queries.upsert_matches(conn, [score_match(candidate, job) for job in jobs])


def _recompute_for_job(conn, job_id):
    job = queries.to_job_profile(queries.get_job(conn, job_id))
    candidates = [queries.to_candidate_profile(c) for c in queries.list_candidates(conn)]
    queries.upsert_matches(conn, [score_match(c, job) for c in candidates])


def _validate_all(payloads, validator):
    cleaned = []
    for index, payload in enumerate(payloads):
        try:
            cleaned.append(validator(payload))
        except ValidationError as e:
            raise ValidationError({f"[{index}].{k}": v for k, v in e.errors.items()}) from None
    return cleaned


def ingest_candidates(conn, payloads):
    ids = []
    for c in _validate_all(payloads, validate_candidate):
        try:
            with conn:
                candidate_id = queries.insert_candidate(conn, **c)
                _recompute_for_candidate(conn, candidate_id)
        except sqlite3.IntegrityError as e:
            raise DuplicateError(f"candidate already exists ({e})") from None
        ids.append(candidate_id)
    return ids


def ingest_jobs(conn, payloads):
    ids = []
    for j in _validate_all(payloads, validate_job):
        try:
            with conn:
                job_id = queries.insert_job(conn, **j)
                _recompute_for_job(conn, job_id)
        except sqlite3.IntegrityError as e:
            raise DuplicateError(f"job already exists ({e})") from None
        ids.append(job_id)
    return ids


def recompute_all_matches(conn):
    candidates = [queries.to_candidate_profile(c) for c in queries.list_candidates(conn)]
    jobs = [queries.to_job_profile(j) for j in queries.list_jobs(conn)]
    results = [score_match(c, j) for c in candidates for j in jobs]
    with conn:
        queries.delete_all_matches(conn)
        queries.upsert_matches(conn, results)
    return len(results)


def parse_match_query():
    limit = int(request.args.get("limit", 10))
    min_score = float(request.args.get("min_score", 0))
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if not 0 <= min_score <= 100:
        raise ValueError("min score must be between 0 and 100")
    return limit, min_score


def _as_list(body):
    return body if isinstance(body, list) else [body]


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/candidates")
def list_candidates():
    return jsonify(queries.list_candidates(get_db()))


@bp.get("/candidates/<int:candidate_id>")
def get_candidate(candidate_id):
    candidate = queries.get_candidate(get_db(), candidate_id)
    if candidate is None:
        return error(404, f"candidate {candidate_id} not found")
    return jsonify(candidate)


@bp.post("/candidates")
def create_candidates():
    body = request.get_json(silent=True)
    if body is None:
        return error(400, "request body must be JSON")
    try:
        ids = ingest_candidates(get_db(), _as_list(body))
    except ValidationError as e:
        return error(400, "validation failed", e.errors)
    except DuplicateError as e:
        return error(409, str(e))
    return jsonify({"created_ids": ids}), 201


@bp.get("/candidates/<int:candidate_id>/matches")
def candidate_matches(candidate_id):
    db = get_db()
    candidate = queries.get_candidate(db, candidate_id)
    if candidate is None:
        return error(404, f"candidate {candidate_id} not found")
    try:
        limit, min_score = parse_match_query()
    except ValueError as e:
        return error(400, str(e))
    return jsonify({
        "candidate": {"id": candidate["id"], "name": candidate["name"]},
        "matches": queries.get_candidate_matches(db, candidate_id, 0, limit),
    })


@bp.get("/jobs")
def list_jobs():
    return jsonify(queries.list_jobs(get_db()))


@bp.get("/jobs/<int:job_id>")
def get_job(job_id):
    job = queries.get_job(get_db(), job_id)
    return jsonify(job)


@bp.post("/jobs")
def create_jobs():
    body = request.get_json(silent=True)
    if body is None:
        return error(400, "request body must be JSON")
    try:
        ids = ingest_jobs(get_db(), _as_list(body))
    except ValidationError as e:
        return error(400, "validation failed", e.errors)
    except DuplicateError as e:
        return error(409, str(e))
    return jsonify({"created_ids": ids}), 201


@bp.get("/jobs/<int:job_id>/matches")
def job_matches(job_id):
    db = get_db()
    job = queries.get_job(db, job_id)
    if job is None:
        return error(404, f"job {job_id} not found")
    try:
        limit, min_score = parse_match_query()
    except ValueError as e:
        return error(400, str(e))
    return jsonify({
        "job": {"id": job["id"], "title": job["title"]},
        "matches": queries.get_job_matches(db, job_id, min_score, limit),
    })


@bp.post("/matches/recompute")
def recompute_matches():
    count = recompute_all_matches(get_db())
    return jsonify({"recomputed_pairs": count})
