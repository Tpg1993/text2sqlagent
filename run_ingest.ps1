$env:PYTHONIOENCODING = "utf-8"
$BackendDir = Resolve-Path (Join-Path $PSScriptRoot "backend") | Select-Object -ExpandProperty Path
$env:PYTHONPATH = $BackendDir
& (Join-Path $BackendDir ".venv\Scripts\python.exe") -m app.rag.ingest
