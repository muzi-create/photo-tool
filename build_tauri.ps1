$ErrorActionPreference = "Stop"

$projectPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $projectPython)) { $projectPython = "python" }
& $projectPython -m phototool.dependencies --profile build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& "$PSScriptRoot\build_frontend.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# The one-file sidecar embeds the Python source and exported web assets.  Always
# rebuild it so that an existing executable cannot silently package stale code.
& $projectPython -m PyInstaller --clean --noconfirm --distpath "build\sidecar-output" sidecar.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

New-Item -ItemType Directory -Force -Path "build\tauri-resources\sidecar" | Out-Null
Copy-Item -LiteralPath "build\sidecar-output\PhotoToolSidecar.exe" -Destination "build\tauri-resources\sidecar\PhotoToolSidecar.exe" -Force

npx tauri build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Tauri build complete: src-tauri\target\release\bundle\nsis"
Write-Host "Distribute and launch only PhotoTool_*_x64-setup.exe; PhotoToolSidecar.exe is an internal background service."
