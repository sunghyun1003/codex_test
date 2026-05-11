$ErrorActionPreference = "Stop"

$Python = "C:\Users\sungh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Venv = ".venv"

& $Python -m venv $Venv
& "$Venv\Scripts\python.exe" -m pip install --upgrade pip
& "$Venv\Scripts\python.exe" -m pip install tzdata

Write-Host "Done. Use .venv\Scripts\python.exe scripts\run_weekly.py --root ."
