param(
    [switch]$WithVolumes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$env:Path += ";C:\Program Files\Docker\Docker\resources\bin"

function Get-DockerExe {
    $known = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    if (Test-Path $known) { return $known }
    $cmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "docker.exe not found."
}

$docker = Get-DockerExe
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if ($WithVolumes) {
    Write-Host "Stopping stack + removing volumes (DB will be wiped)..." -ForegroundColor Yellow
    & $docker compose down -v
} else {
    Write-Host "Stopping stack..." -ForegroundColor Cyan
    & $docker compose down
}

Write-Host "Done." -ForegroundColor Green