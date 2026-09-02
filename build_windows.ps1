$ErrorActionPreference = "Stop"

python -m reflex compile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m PyInstaller --clean --noconfirm PhotoTool.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Build complete: dist\PhotoTool\PhotoTool.exe"
