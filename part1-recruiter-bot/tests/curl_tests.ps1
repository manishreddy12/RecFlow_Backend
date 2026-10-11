param([string]$Base = "http://127.0.0.1:5000")

$run = [int][double]::Parse((Get-Date -UFormat %s))
$bodyFile = [System.IO.Path]::GetTempFileName()
$dataFile = [System.IO.Path]::GetTempFileName()
$script:pass = 0
$script:fail = 0

function Check($name, $expected, $method, $path, $data, $contains) {
    $curlArgs = @("-s", "-o", $bodyFile, "-w", "%{http_code}", "-X", $method, "$Base$path")
    if ($data) {
        [System.IO.File]::WriteAllText($dataFile, $data)
        $curlArgs += @("-H", "Content-Type: application/json", "--data-binary", "@$dataFile")
    }
    $status = & curl.exe @curlArgs
    $body = Get-Content $bodyFile -Raw
    if ($status -eq "$expected" -and (-not $contains -or ($body -and $body.Contains($contains)))) {
        Write-Host "PASS  $name"
        $script:pass++
    } else {
        Write-Host "FAIL  $name (got $status, expected $expected $(if ($contains) { "containing '$contains'" }))"
        Write-Host $body
        $script:fail++
    }
}

Check "health"                          200 GET  "/health" $null '"ok"'
Check "list candidates"                 200 GET  "/candidates" $null "Sherlock H."
Check "list jobs"                       200 GET  "/jobs" $null "Backend Detective"
Check "get candidate"                   200 GET  "/candidates/1" $null "deduction"
Check "unknown candidate"               404 GET  "/candidates/999" $null $null
Check "sherlock tops backend detective" 200 GET  "/jobs/1/matches?limit=1" $null "Sherlock H."
Check "match has reason"                200 GET  "/jobs/1/matches?limit=1" $null '"reason"'
Check "olivia -> incident commander"    200 GET  "/candidates/12/matches?limit=1" $null "Incident Commander"
Check "limit not a number"              400 GET  "/jobs/1/matches?limit=abc" $null $null
Check "limit zero"                      400 GET  "/jobs/1/matches?limit=0" $null $null
Check "min_score too high"              400 GET  "/jobs/1/matches?min_score=200" $null $null
Check "matches for unknown job"         404 GET  "/jobs/999/matches" $null $null
Check "add candidate"                   201 POST "/candidates" "{`"name`":`"Hercule P. $run`",`"skills`":[`"deduction`",`"Pattern Recognition`"],`"experience_years`":30,`"availability`":`"Immediate`",`"traits`":[`"analytical`"]}" "created_ids"
Check "invalid candidate"               400 POST "/candidates" '{"name":"","experience_years":-1,"availability":"someday","skills":[]}' "validation failed"
Check "duplicate candidate"             409 POST "/candidates" '{"name":"Sherlock H.","skills":["deduction"],"experience_years":8,"availability":"Immediate"}' $null
Check "add job"                         201 POST "/jobs" "{`"title`":`"Chemistry Consultant $run`",`"required_skills`":[`"chemistry`"],`"min_experience`":5}" "created_ids"
Check "body is not json"                400 POST "/jobs" $null $null
Check "recompute matches"               200 POST "/matches/recompute" $null "recomputed_pairs"
Check "unknown route"                   404 GET  "/nope" $null $null

Remove-Item $bodyFile, $dataFile -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "$($script:pass) passed, $($script:fail) failed"
if ($script:fail -gt 0) { exit 1 }
