#Requires -Version 5.1
<#
.SYNOPSIS
  Run the full data pipeline on Windows (Phase 1 + Phase 2 completed steps).

.PARAMETER SkipDownload
  Skip HDX raw dataset download and reuse existing data/raw/.

.PARAMETER From
  Start at a specific step: explore | validate | roads | topology | merge | network

.EXAMPLE
  .\scripts\bootstrap.ps1
  .\scripts\bootstrap.ps1 -SkipDownload
  .\scripts\bootstrap.ps1 -From merge
  .\scripts\bootstrap.ps1 -From network
#>
param(
    [switch]$SkipDownload,
    [ValidateSet("all", "explore", "validate", "roads", "topology", "merge", "network")]
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
        "explore" { return $Step -in @("explore", "validate", "roads", "topology", "merge", "network") }
        "validate" { return $Step -in @("validate", "roads", "topology", "merge", "network") }
        "roads" { return $Step -in @("roads", "topology", "merge", "network") }
        "topology" { return $Step -in @("topology", "merge", "network") }
        "merge" { return $Step -in @("merge", "network") }
        "network" { return $Step -eq "network" }
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
if (Test-ShouldRun "network") {
    Run-Step "Phase 2 — network integration" "integrate_network.py"
    Run-Step "Augmented network validation map" "visualize_augmented_network.py"
    Run-Step "Phase 2 — admin dimensions" "build_admin_dimensions.py"
    Run-Step "Phase 2 — displacement sites" "build_displacement_sites.py"
    Run-Step "Phase 2 — reference data" "build_reference_data.py"
    Run-Step "Phase 2 — DB import layers" "prepare_db_import_layers.py"
}

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host ""
Write-Host "Generated artifacts (local only, not in git):"
Write-Host "  data/raw/          raw HDX + Geofabrik downloads"
Write-Host "  data/processed/    road graph, facilities, network, admin, reference"
Write-Host "  output/            HTML validation maps"
Write-Host ""
Write-Host "Open in a browser:"
Write-Host "  output/south_sudan_data_validation.html"
Write-Host "  output/south_sudan_road_topology_validation.html"
Write-Host "  output/south_sudan_augmented_network_validation.html"
Write-Host ""
Write-Host "Next: Phase 3 database population — see AGENT_PHASE3.md"
