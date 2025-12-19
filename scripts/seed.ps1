param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ProjectName = "shop",
    [string]$ProdEnvName = "prod",
    [string]$DevEnvName  = "dev",
    [string]$ProdKey = "demo",
    [string]$DevKey  = "demo-dev"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Wait-ApiReady([int]$MaxTries = 60) {
    for ($i=1; $i -le $MaxTries; $i++) {
        try {
            $h = Invoke-RestMethod -Method Get -Uri "$BaseUrl/healthz" -TimeoutSec 3
            if ($h -eq $true -or $h.ok -eq $true -or $h.status -eq "ok") { return }
        } catch {
            # ignore and retry
        }
        Start-Sleep -Milliseconds 500
    }
    throw "API is not ready at $BaseUrl (healthz never became OK)"
}

Wait-ApiReady


function Json($obj, [int]$depth = 10) { return ($obj | ConvertTo-Json -Depth $depth) }
function Get-All($path) { return Invoke-RestMethod -Method Get -Uri "$BaseUrl$path" }
function Post($path, $body) { return Invoke-RestMethod -Method Post -Uri "$BaseUrl$path" -ContentType "application/json" -Body (Json $body) }
function Patch($path, $body) { return Invoke-RestMethod -Method Patch -Uri "$BaseUrl$path" -ContentType "application/json" -Body (Json $body) }

$projects = Get-All "/admin/v1/projects"
$project = $projects | Where-Object { $_.name -eq $ProjectName } | Select-Object -First 1
if (-not $project) { $project = Post "/admin/v1/projects" @{ name = $ProjectName } }
$projectId = [int]$project.id

$envs = Get-All "/admin/v1/envs"
$prodEnv = $envs | Where-Object { $_.project_id -eq $projectId -and $_.name -eq $ProdEnvName } | Select-Object -First 1
if (-not $prodEnv) { $prodEnv = Post "/admin/v1/envs" @{ name = $ProdEnvName; project_id = $projectId } }
$prodEnvId = [int]$prodEnv.id

$devEnv = $envs | Where-Object { $_.project_id -eq $projectId -and $_.name -eq $DevEnvName } | Select-Object -First 1
if (-not $devEnv) { $devEnv = Post "/admin/v1/envs" @{ name = $DevEnvName; project_id = $projectId } }
$devEnvId = [int]$devEnv.id

$keys = Get-All "/admin/v1/keys"
$prodKeyObj = $keys | Where-Object { $_.key -eq $ProdKey -and $_.project_id -eq $projectId -and $_.environment_id -eq $prodEnvId } | Select-Object -First 1
if (-not $prodKeyObj) { $prodKeyObj = Post "/admin/v1/keys" @{ key = $ProdKey; project_id = $projectId; environment_id = $prodEnvId } }

$devKeyObj = $keys | Where-Object { $_.key -eq $DevKey -and $_.project_id -eq $projectId -and $_.environment_id -eq $devEnvId } | Select-Object -First 1
if (-not $devKeyObj) { $devKeyObj = Post "/admin/v1/keys" @{ key = $DevKey; project_id = $projectId; environment_id = $devEnvId } }

$flags = Get-All "/admin/v1/flags"
$flag = $flags | Where-Object { $_.project_id -eq $projectId -and $_.key -eq "enable_dark_mode" } | Select-Object -First 1
if (-not $flag) {
  $flag = Post "/admin/v1/flags" @{ key="enable_dark_mode"; project_id=$projectId; on=$true; default_variant="off"; status="published" }
}
$flagId = [int]$flag.id

$variants = Get-All "/admin/v1/flags/$flagId/variants"
if (-not ($variants | Where-Object { $_.name -eq "dark" } | Select-Object -First 1)) {
  Post "/admin/v1/flags/$flagId/variants" @{ name="dark"; payload=@{ theme="dark" } } | Out-Null
}

$rules = Get-All "/admin/v1/flags/$flagId/rules"
if (-not ($rules | Where-Object { $_.environment_id -eq $prodEnvId -and $_.priority -eq 1 } | Select-Object -First 1)) {
  Post "/admin/v1/flags/$flagId/rules" @{ priority=1; environment_id=$prodEnvId; predicate=@{attr="country";op="==";value="TR"}; distribution=@{dark=30;off=70} } | Out-Null
}

# Configs (global + prod)
$configs = Get-All "/admin/v1/configs"
function FindCfg($envId) {
  return ($configs | Where-Object {
    $_.project_id -eq $projectId -and $_.key -eq "support_email" -and (
      ($null -eq $envId -and $null -eq $_.environment_id) -or ($envId -ne $null -and $_.environment_id -eq $envId)
    )
  } | Select-Object -First 1)
}

$g = FindCfg $null
if (-not $g) { Post "/admin/v1/configs" @{ project_id=$projectId; environment_id=$null; key="support_email"; value="support@shop.com" } | Out-Null }
else { Patch "/admin/v1/configs/$($g.id)" @{ value="support@shop.com" } | Out-Null }

$configs = Get-All "/admin/v1/configs"
$p = FindCfg $prodEnvId
if (-not $p) { Post "/admin/v1/configs" @{ project_id=$projectId; environment_id=$prodEnvId; key="support_email"; value="support-prod@shop.com" } | Out-Null }
else { Patch "/admin/v1/configs/$($p.id)" @{ value="support-prod@shop.com" } | Out-Null }

$prodResp = Invoke-RestMethod -Method Get -Uri "$BaseUrl/sdk/v1/flags?env=$ProdEnvName" -Headers @{ "X-SDK-Key" = $ProdKey }
$devResp  = Invoke-RestMethod -Method Get -Uri "$BaseUrl/sdk/v1/flags?env=$DevEnvName"  -Headers @{ "X-SDK-Key" = $DevKey  }

"PROD support_email = $($prodResp.configs.support_email)"
"DEV  support_email = $($devResp.configs.support_email)"