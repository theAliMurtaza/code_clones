param(
    [ValidateSet('start', 'status', 'stop', 'copy-key')]
    [string]$Action = 'start'
)
$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.laptop-model'
if ($Action -eq 'copy-key') {
    $keyFile = Join-Path $runtime 'model-key.txt'
    if (-not (Test-Path -LiteralPath $keyFile)) { throw 'Start the model first.' }
    Set-Clipboard -Value ((Get-Content -LiteralPath $keyFile -Raw).Trim())
    Write-Host 'Model key copied. Paste it only into the Render backend SEMANTIC_API_KEY value.'
    exit
}
$pythonExe = Join-Path (Split-Path $PSScriptRoot) '.venv311\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Missing backend\.venv311. See LAPTOP-SETUP.md for Python 3.11 installation.'
}
& $pythonExe (Join-Path $PSScriptRoot 'laptop_model.py') $Action
if ($LASTEXITCODE -ne 0) { throw 'Laptop model command failed; see .laptop-model\launcher.log.' }
