#Requires -Version 5.1
<#
.SYNOPSIS
  Bootstrap the project using Miniforge/Conda on Windows.

.DESCRIPTION
  Creates (or updates) the conda environment defined in environment.yml,
  then creates required data/output directories.

.EXAMPLE
  .\scripts\setup.ps1
#>
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Get-CondaExe {
    if ($env:CONDA_EXE -and (Test-Path $env:CONDA_EXE)) {
        return $env:CONDA_EXE
    }
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

Write-Host "==> Checking conda ..."
$CondaExe = Get-CondaExe
if (-not $CondaExe) {
    Write-Error "conda not found. Install Miniforge, open 'Miniforge Prompt', and run this script again."
}

Write-Host "==> Creating/updating conda environment 'dm-south-sudan' ..."
& $CondaExe env create -f "$Root\environment.yml" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $CondaExe env update -f "$Root\environment.yml" --prune
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create or update conda environment."
    }
}

Write-Host "==> Creating project directories ..."
& $CondaExe run -n dm-south-sudan python "$Root\scripts\create_dirs.py"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create project directories."
}

Write-Host ""
Write-Host "Setup complete."
Write-Host ""
Write-Host "Next steps (in Miniforge Prompt or after 'conda activate dm-south-sudan'):"
Write-Host "  1. conda activate dm-south-sudan"
Write-Host "  2. python scripts\download_datasets.py"
Write-Host "  3. python scripts\explore_datasets.py"
Write-Host "  4. python scripts\visualize_data_validation.py"
Write-Host "  5. python scripts\build_road_network_topology.py"
Write-Host "  6. python scripts\visualize_road_topology.py"
Write-Host "  7. python scripts\merge_health_facilities.py"
Write-Host ""
Write-Host "Or run the full pipeline:"
Write-Host "  .\scripts\bootstrap.ps1"
