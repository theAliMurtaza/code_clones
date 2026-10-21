$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.laptop-model'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$target = Join-Path $runtime 'cloudflared.exe'
# Pin and verify the official Windows x64 release; no admin or machine-wide install.
$version = '2026.10.1'
$expected = '4d2490e74082c5d48dbfedaf92576fa5bd1702379ab88eb7faa0cfbe8dc891b6'
if ((Test-Path -LiteralPath $target) -and
    (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -eq $expected) {
    Write-Host "Verified cloudflared $version is already installed."
    exit
}
$download = Join-Path $runtime 'cloudflared.download'
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/download/$version/cloudflared-windows-amd64.exe" -OutFile $download
if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw 'cloudflared checksum mismatch. The downloaded file will not be executed.'
}
Move-Item -LiteralPath $download -Destination $target -Force
& $target --version
if ($LASTEXITCODE -ne 0) { throw 'cloudflared could not run.' }
