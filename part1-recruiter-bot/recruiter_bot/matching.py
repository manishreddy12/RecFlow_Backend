from dataclasses import dataclass, field


WEIGHTS = {
    "skills": 0.55,
    "experience": 0.25,
    "culture": 0.12,
    "availability": 0.08,
}

AVAILABILITY_SCORES = {
    "immediate": 1.0,
    "2_week": 0.7,
    "not_looking": 0.2,
}

AVAILABILITY_PHRASES = {
    "immediate": "available immediately",
    "2_weeks": "available in 2 weeks",
    "not_looking": "not currently looking",
}

NO_SKILL_CAP = 20.0


@dataclass
class CandidateProfile:
    id: int
    name: str
    experience_years: int
    availability: str
    skills: set = field(default_factory=set)
    traits: set = field(default_factory=set)


@dataclass
class JobProfile:
    id: int
    title: str
    min_experience: int
    required_skills: set = field(default_factory=set)
    culture_keywords: set = field(default_factory=set)


@dataclass
class MatchResult:
    candidate_id: int
    job_id: int
    score: float
    skill_score: float
    experience_score: float
    culture_score: float
    availability_score: float
    matched_skills: list
    reason: str

    @property
    def matched_skill_count(self):
        return len(self.matched_skills)


def skill_score(candidate, job):
    matched = sorted(candidate.skills & job.required_skills)
    if not job.required_skills:
        return 1.0, matched
    return len(matched) / len(candidate.skills), matched


def experience_score(candidate, job):
    if job.min_experience <= 0 or candidate.experience_years >= job.min_experience:
        return 1.0
    return candidate.experience_years // job.min_experience


def keyword_matches_trait(keyword, trait):
    return trait == keyword or trait in keyword.split("-")


def culture_score(candidate, job):
    if not job.culture_keywords:
        return 0.0, []
    matched = sorted(
        kw for kw in job.culture_keywords
        if any(keyword_matches_trait(kw, trait) for trait in candidate.traits)
    )
    return len(matched) / len(job.culture_keywords), matched


def availability_score(candidate):
    return AVAILABILITY_SCORES.get(candidate.availability, 0.0)


def build_reason(candidate, job, matched_skills, exp, matched_culture):
    parts = []
    required = len(job.required_skills)
    if matched_skills:
        part = f"{len(matched_skills)}/{required} required skills ({', '.join(matched_skills)})"
        missing = sorted(job.required_skills - set(matched_skills))
        if missing:
            part += f", missing {', '.join(missing)}"
        parts.append(part)
    elif required:
        parts.append(f"none of the required skills ({', '.join(sorted(job.required_skills))})")

    if exp > 1.0:
        parts.append(f"{candidate.experience_years}y experience (min {job.min_experience})")
    else:
        parts.append(f"{candidate.experience_years}y experience, below the {job.min_experience}y minimum")

    if matched_culture:
        parts.append(f"culture fit: {', '.join(matched_culture)}")

    parts.append(AVAILABILITY_PHRASES.get(candidate.availability, "availability unknown"))
    return "; ".join(parts)


def score_match(candidate, job):
    skills, matched_skills = skill_score(candidate, job)
    exp = experience_score(candidate, job)
    culture, matched_culture = culture_score(candidate, job)
    avail = availability_score(candidate)

    total = 100 * (
        WEIGHTS["skills"] * skills
        + WEIGHTS["experience"] * exp
        + WEIGHTS["culture"] * culture
        + WEIGHTS["availability"] * avail
    )
    if job.required_skills and not matched_skills:
        total = min(total, NO_SKILL_CAP)

    return MatchResult(
        candidate_id=candidate.id,
        job_id=job.id,
        score=round(total, 1),
        skill_score=round(skills, 3),
        experience_score=round(exp, 3),
        culture_score=round(culture, 3),
        availability_score=round(avail, 3),
        matched_skills=matched_skills,
        reason=build_reason(candidate, job, matched_skills, exp, matched_culture),
    )
