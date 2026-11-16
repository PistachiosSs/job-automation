# Job Apply launcher for Windows PowerShell:  .\start.ps1 [--port 8766] [--no-browser]
Set-Location $PSScriptRoot
$python = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
$prefix = if ($python -eq 'py') { @('-3') } else { @() }
if (-not (Test-Path 'config.json')) {
    Write-Host 'No config.json found - running first-time setup.'
    & $python @prefix setup.py
}
Write-Host 'Starting Job Apply (keep this window open; press Ctrl+C to stop)'
& $python @prefix app\server.py @args
