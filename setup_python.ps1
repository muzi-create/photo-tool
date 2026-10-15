$ErrorActionPreference = "Stop"

Push-Location -LiteralPath $PSScriptRoot
try {
    $projectPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $projectPython)) {
        python -m venv venv
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    & $projectPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $projectPython -m phototool.dependencies --profile all
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
