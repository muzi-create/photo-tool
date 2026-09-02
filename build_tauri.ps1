$ErrorActionPreference = "Stop"

python -m reflex compile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path -LiteralPath "dist\sidecar\PhotoToolSidecar.exe")) {
    python -m PyInstaller --clean --noconfirm sidecar.spec
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    New-Item -ItemType Directory -Force -Path "dist\sidecar" | Out-Null
    Copy-Item -LiteralPath "dist\PhotoToolSidecar\PhotoToolSidecar.exe" -Destination "dist\sidecar\PhotoToolSidecar.exe" -Force
}

npx tauri build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Tauri build complete: src-tauri\target\release\bundle\nsis"
