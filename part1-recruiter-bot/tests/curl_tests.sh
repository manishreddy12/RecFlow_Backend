#!/usr/bin/env bash
BASE="${BASE:-http://127.0.0.1:5000}"
RUN=$(date +%s)
BODY=$(mktemp)
PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" method="$3" path="$4" data="$5" contains="$6"
  local status
  if [ -n "$data" ]; then
    status=$(curl -s -o "$BODY" -w "%{http_code}" -X "$method" "$BASE$path" -H "Content-Type: application/json" -d "$data")
  else
    status=$(curl -s -o "$BODY" -w "%{http_code}" -X "$method" "$BASE$path")
  fi
  if [ "$status" = "$expected" ] && { [ -z "$contains" ] || grep -q "$contains" "$BODY"; }; then
    echo "PASS  $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL  $name (got $status, expected $expected${contains:+ containing '$contains'})"
    cat "$BODY"; echo
    FAIL=$((FAIL + 1))
  fi
}

check "health"                          200 GET  "/health" "" '"ok"'
check "list candidates"                 200 GET  "/candidates" "" "Sherlock H."
check "list jobs"                       200 GET  "/jobs" "" "Backend Detective"
check "get candidate"                   200 GET  "/candidates/1" "" "deduction"
check "unknown candidate"               404 GET  "/candidates/999" ""
check "sherlock tops backend detective" 200 GET  "/jobs/1/matches?limit=1" "" "Sherlock H."
check "match has reason"                200 GET  "/jobs/1/matches?limit=1" "" '"reason"'
check "olivia -> incident commander"    200 GET  "/candidates/12/matches?limit=1" "" "Incident Commander"
check "limit not a number"              400 GET  "/jobs/1/matches?limit=abc" ""
check "limit zero"                      400 GET  "/jobs/1/matches?limit=0" ""
check "min_score too high"              400 GET  "/jobs/1/matches?min_score=200" ""
check "matches for unknown job"         404 GET  "/jobs/999/matches" ""
check "add candidate"                   201 POST "/candidates" "{\"name\":\"Hercule P. $RUN\",\"skills\":[\"deduction\",\"Pattern Recognition\"],\"experience_years\":30,\"availability\":\"Immediate\",\"traits\":[\"analytical\"]}" "created_ids"
check "invalid candidate"               400 POST "/candidates" '{"name":"","experience_years":-1,"availability":"someday","skills":[]}' "validation failed"
check "duplicate candidate"             409 POST "/candidates" '{"name":"Sherlock H.","skills":["deduction"],"experience_years":8,"availability":"Immediate"}'
check "add job"                         201 POST "/jobs" "{\"title\":\"Chemistry Consultant $RUN\",\"required_skills\":[\"chemistry\"],\"min_experience\":5}" "created_ids"
check "body is not json"                400 POST "/jobs" ""
check "recompute matches"               200 POST "/matches/recompute" "" "recomputed_pairs"
check "unknown route"                   404 GET  "/nope" ""

rm -f "$BODY"
echo
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
