Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:Path += ";C:\Program Files\Docker\Docker\resources\bin"

function Get-DockerExe {
    $known = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    if (Test-Path $known) { return $known }
    $cmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "docker.exe not found. Is Docker Desktop installed and running?"
}

$docker = Get-DockerExe

# repo root = scripts klasörünün bir üstü
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& $docker version | Out-Null

Write-Host "Starting stack (build included)..." -ForegroundColor Cyan
& $docker compose up -d --build

Write-Host "`nRunning containers:" -ForegroundColor Cyan
& $docker ps

Write-Host "`nOpen:" -ForegroundColor Green
Write-Host "  API docs:     http://127.0.0.1:8000/docs"
Write-Host "  Healthz:      http://127.0.0.1:8000/healthz"
Write-Host "  phpMyAdmin:   http://127.0.0.1:8080"