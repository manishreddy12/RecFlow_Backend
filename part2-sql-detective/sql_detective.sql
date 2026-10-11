-- Q1
SELECT jp.id AS job_posting_id,
       jp.title,
       jp.department,
       jp.opened_date,
       r.name AS recruiter_name
  FROM job_postings jp
  LEFT JOIN recruiters r ON r.id = jp.recruiter_id
 WHERE jp.status = 'open'
 ORDER BY jp.opened_date, jp.id;


-- Q2
SELECT jp.id AS job_posting_id,
       jp.title,
       COUNT(DISTINCT i.applicant_id) AS applicants_reached_final
  FROM job_postings jp
  LEFT JOIN interviews i ON i.job_posting_id = jp.id
                        AND i.stage = 'Final'
 GROUP BY jp.id, jp.title
 ORDER BY jp.id;


-- Q3
SELECT LOWER(TRIM(a.email)) AS email,
       MIN(a.full_name) AS full_name,
       COUNT(DISTINCT i.job_posting_id) AS postings_applied_to
  FROM applicants a
  JOIN interviews i ON i.applicant_id = a.id
 GROUP BY LOWER(TRIM(a.email))
HAVING COUNT(DISTINCT i.job_posting_id) > 1
 ORDER BY full_name;


-- Q4
SELECT r.id AS recruiter_id,
       r.name AS recruiter_name,
       COUNT(*) AS final_interviews,
       SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) AS final_passed,
       ROUND(100.0 * SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 2) AS conversion_rate_pct
  FROM recruiters r
  JOIN job_postings jp ON jp.recruiter_id = r.id
  JOIN interviews i ON i.job_posting_id = jp.id
 WHERE i.stage = 'Final'
 GROUP BY r.id, r.name
HAVING COUNT(*) >= 3
 ORDER BY conversion_rate_pct DESC;


-- Q5
WITH placements AS (
    SELECT jp.department,
           r.name AS recruiter_name,
           COUNT(*) AS placements
      FROM interviews i
      JOIN job_postings jp ON jp.id = i.job_posting_id
      JOIN recruiters r ON r.id = jp.recruiter_id
     WHERE i.stage = 'Final'
       AND i.outcome = 'passed'
     GROUP BY jp.department, r.name
),
ranked AS (
    SELECT department,
           recruiter_name,
           placements,
           RANK() OVER (PARTITION BY department ORDER BY placements DESC) AS rn
      FROM placements
)
SELECT department, recruiter_name, placements
  FROM ranked
 WHERE rn = 1
 ORDER BY department;
