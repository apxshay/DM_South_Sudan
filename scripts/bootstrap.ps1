#Requires -Version 5.1
<#
.SYNOPSIS
  Run the full data pipeline on Windows (Phase 1 + Phase 2 completed steps).

.PARAMETER SkipDownload
  Skip HDX raw dataset download and reuse existing data/raw/.

.PARAMETER From
  Start at a specific step: explore | validate | roads | topology | merge

.EXAMPLE
  .\scripts\bootstrap.ps1
  .\scripts\bootstrap.ps1 -SkipDownload
  .\scripts\bootstrap.ps1 -From merge
#>
param(
    [switch]$SkipDownload,
    [ValidateSet("all", "explore", "validate", "roads", "topology", "merge")]
    [string]$From = "all"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Get-CondaExe {
    if ($env:CONDA_EXE -and (Test-Path $env:CONDA_EXE)) { return $env:CONDA_EXE }
    $candidates = @(
        "$env:USERPROFILE\miniforge3\Scripts\conda.exe",
        "$env:USERPROFILE\miniforge3\condabin\conda.bat",
        "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
        "$env:LOCALAPPDATA\miniforge3\Scripts\conda.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    $conda = Get-Command conda -ErrorAction SilentlyContinue
    if ($conda) { return $conda.Source }
    return $null
}

function Invoke-ProjectPython {
    param([string[]]$ScriptArgs)
    $CondaExe = Get-CondaExe
    if ($env:CONDA_DEFAULT_ENV -eq "dm-south-sudan") {
        & python @ScriptArgs
        return
    }
    if ($CondaExe) {
        & $CondaExe run --no-capture-output -n dm-south-sudan python @ScriptArgs
        return
    }
    if (Test-Path "$Root\data_env\Scripts\python.exe") {
        & "$Root\data_env\Scripts\python.exe" @ScriptArgs
        return
    }
    throw "Python environment not found. Run .\scripts\setup.ps1 first."
}

function Test-ShouldRun {
    param([string]$Step)
    switch ($From) {
        "all" { return $true }
        "explore" { return $Step -in @("explore", "validate", "roads", "topology", "merge") }
        "validate" { return $Step -in @("validate", "roads", "topology", "merge") }
        "roads" { return $Step -in @("roads", "topology", "merge") }
        "topology" { return $Step -in @("topology", "merge") }
        "merge" { return $Step -eq "merge" }
    }
    return $false
}

function Run-Step {
    param([string]$Name, [string]$Script)
    Write-Host ""
    Write-Host "==> $Name"
    Invoke-ProjectPython @("$Root\scripts\$Script")
}

Write-Host "==> Creating directories"
Invoke-ProjectPython @("$Root\scripts\create_dirs.py")

if (-not $SkipDownload -and (Test-ShouldRun "explore")) {
    Run-Step "Downloading raw datasets (HDX)" "download_datasets.py"
}
elseif ($SkipDownload) {
    Write-Host ""
    Write-Host "==> Skipping download (-SkipDownload)"
}

if (Test-ShouldRun "explore") { Run-Step "Phase 1 profiling" "explore_datasets.py" }
if (Test-ShouldRun "validate") { Run-Step "Phase 1 validation map" "visualize_data_validation.py" }
if (Test-ShouldRun "roads") { Run-Step "Road network topology (OSMnx)" "build_road_network_topology.py" }
if (Test-ShouldRun "topology") { Run-Step "Road topology validation map" "visualize_road_topology.py" }
if (Test-ShouldRun "merge") { Run-Step "Phase 2 — health facility merge" "merge_health_facilities.py" }

Write-Host ""
Write-Host "Bootstrap complete."
