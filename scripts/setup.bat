@echo off
REM DeviceVault - first-time setup on Windows (safe to re-run).
REM Creates the backend virtualenv, installs dependencies and creates backend\.env.
setlocal
cd /d "%~dp0.."

where python >nul 2>&1 || (echo Python 3.11+ is required: https://www.python.org/downloads/ & exit /b 1)
where npm >nul 2>&1 || (echo Node.js 20.19+ is required: https://nodejs.org/ & exit /b 1)

if not exist "backend\.venv\Scripts\python.exe" (
  echo Creating backend virtual environment ...
  python -m venv backend\.venv || exit /b 1
  backend\.venv\Scripts\python.exe -m pip install --upgrade pip >nul
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || exit /b 1
)

if not exist "backend\.env" (
  echo Creating backend\.env with a random SECRET_KEY ...
  backend\.venv\Scripts\python.exe -c "import pathlib,secrets; p=pathlib.Path('backend'); t=(p/'.env.example').read_text(); (p/'.env').write_text(t.replace('change-me-in-production-use-a-long-random-string', secrets.token_urlsafe(48)))" || exit /b 1
)

if not exist "frontend\node_modules" (
  echo Installing frontend dependencies ...
  pushd frontend
  call npm ci --no-audit --no-fund || (popd & exit /b 1)
  popd
)

echo Setup complete.
endlocal
