param([switch]$Full)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$reviewPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $reviewPython)) { throw 'Existing project .venv not found. Copy these files into the project root first.' }
$reviewConfig = if ($Full) { 'configs/review.yaml' } else { 'configs/review_smoke.yaml' }
& $reviewPython src/run_review.py --config $reviewConfig
if ($LASTEXITCODE -ne 0) { throw 'Experiment failed. Do not analyze an incomplete run.' }
$reviewOutputRoot = if ($Full) { 'data/review_runs' } else { 'data/review_smoke' }
$reviewLatest = Get-ChildItem $reviewOutputRoot -Directory | Sort-Object Name -Descending | Select-Object -First 1
& $reviewPython src/analyze_review.py --run-dir $reviewLatest.FullName
if ($LASTEXITCODE -ne 0) { throw 'Analysis failed.' }
& $reviewPython -m pip freeze | Set-Content -Encoding UTF8 (Join-Path $reviewLatest.FullName 'analysis-environment.txt')
Write-Host ('Completed: ' + $reviewLatest.FullName)
