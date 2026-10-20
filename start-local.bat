@echo off
REM DeviceVault - development mode on Windows (hot reload).
REM Backend: http://localhost:8000   Frontend: http://localhost:3000 (proxies /api to the backend)
setlocal
cd /d "%~dp0"

call "%~dp0scripts\setup.bat" || exit /b 1

echo Starting backend on http://localhost:8000 ...
start "devicevault-backend" cmd /k "cd /d ""%~dp0backend"" && .venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting frontend on http://localhost:3000 ...
start "devicevault-frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo Open http://localhost:3000
echo Login: admin@company.com / Admin123!
endlocal
