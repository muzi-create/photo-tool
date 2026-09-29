$ErrorActionPreference = "Stop"

python -m reflex export --frontend-only --no-zip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python phototool\patch_exported_frontend.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path -LiteralPath ".web\build\client\index.html")) {
    throw "Reflex export did not produce .web\build\client\index.html"
}

# Tauri initially loads a local asset while the Python sidecar unpacks.  This
# page deliberately contains no Reflex client so it cannot try connecting to
# tauri.localhost before the shell navigates to the ready sidecar.
@'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PhotoTool Loading</title>
  <style>
    :root { color-scheme: light; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #f4f7fb; color: #1b2942; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
    main { width: min(340px, calc(100vw - 48px)); text-align: center; }
    .mark { width: 54px; height: 54px; margin: 0 auto 18px; display: grid; place-items: center; border-radius: 16px; background: linear-gradient(145deg, #2584f4, #125bc8); color: #fff; font-size: 16px; font-weight: 800; box-shadow: 0 10px 24px rgba(23,105,224,.24); }
    h1 { margin: 0 0 8px; font-size: 20px; letter-spacing: -.3px; }
    p { margin: 0 0 22px; color: #718097; font-size: 14px; }
    .progress { height: 8px; overflow: hidden; border-radius: 999px; background: #dce8f6; box-shadow: inset 0 1px 2px rgba(20, 50, 92, .08); }
    .progress::after { content: ""; display: block; width: 42%; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #1769e0, #54a6ff); animation: loading 1.25s ease-in-out infinite; }
    @keyframes loading { 0% { transform: translateX(-120%); } 55% { transform: translateX(135%); } 100% { transform: translateX(135%); } }
  </style>
</head>
<body><main><div class="mark">PT</div><h1>PhotoTool</h1><p>&#27491;&#22312;&#21551;&#21160;&#26412;&#22320;&#22270;&#29255;&#22788;&#29702;&#26381;&#21153;&#8230;</p><div class="progress" role="progressbar" aria-label="Loading"></div></main></body>
</html>
'@ | Set-Content -LiteralPath ".web\build\client\loading.html" -Encoding utf8
