$pythonPath = "c:\Users\Tejas\Downloads\APPS\text2sql rag\.venv\Scripts\python.exe"
Write-Output "Starting Backend Server with $pythonPath..."

# Set PYTHONPATH to include the current directory so 'app' module is found
$env:PYTHONPATH = "$PWD"

& $pythonPath -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
