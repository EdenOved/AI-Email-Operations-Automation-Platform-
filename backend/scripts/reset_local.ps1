param(
    [switch] $SkipMigrations
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = Split-Path -Parent $ScriptRoot
$RepoRoot = Split-Path -Parent $BackendRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    docker compose up -d | Out-Null
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        docker compose exec -T postgres pg_isready -U postgres -d email_ops_clean 1>$null 2>$null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "Postgres did not become ready" }
}
finally {
    Pop-Location
}

if (-not $SkipMigrations) {
    Push-Location $BackendRoot
    try {
        & $VenvPython -m alembic upgrade head
    }
    finally {
        Pop-Location
    }
}

$sql = @"
TRUNCATE TABLE integration_attempts RESTART IDENTITY CASCADE;
TRUNCATE TABLE integration_jobs RESTART IDENTITY CASCADE;
TRUNCATE TABLE human_reviews RESTART IDENTITY CASCADE;
TRUNCATE TABLE approval_requests RESTART IDENTITY CASCADE;
TRUNCATE TABLE routing_decisions RESTART IDENTITY CASCADE;
TRUNCATE TABLE extraction_runs RESTART IDENTITY CASCADE;
TRUNCATE TABLE email_events RESTART IDENTITY CASCADE;
TRUNCATE TABLE audit_logs RESTART IDENTITY CASCADE;
TRUNCATE TABLE golden_case_candidates RESTART IDENTITY CASCADE;
TRUNCATE TABLE eval_run_case_results RESTART IDENTITY CASCADE;
TRUNCATE TABLE eval_runs RESTART IDENTITY CASCADE;
TRUNCATE TABLE emails RESTART IDENTITY CASCADE;
UPDATE tenants SET settings_json = '{}'::json;
"@

Push-Location $RepoRoot
try {
    $sql | docker compose exec -T postgres psql -U postgres -d email_ops_clean -v ON_ERROR_STOP=1
}
finally {
    Pop-Location
}

Write-Host "Reset complete."
