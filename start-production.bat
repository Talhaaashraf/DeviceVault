@echo off
REM DeviceVault - production mode on Windows: nginx serves the built frontend
REM on http://localhost:8080 and proxies /api to uvicorn on 127.0.0.1:8000.
REM
REM Requires nginx for Windows (https://nginx.org/en/download.html).
REM Either add the nginx folder to PATH or set NGINX_HOME, e.g.
REM   set NGINX_HOME=C:\nginx
setlocal
cd /d "%~dp0"

set "NGINX_EXE=nginx.exe"
if defined NGINX_HOME set "NGINX_EXE=%NGINX_HOME%\nginx.exe"
"%NGINX_EXE%" -v >nul 2>&1
if errorlevel 1 (
  echo nginx.exe not found. Install nginx for Windows and add it to PATH or set NGINX_HOME.
  exit /b 1
)

call "%~dp0scripts\setup.bat" || exit /b 1

echo Building frontend ...
pushd frontend
call npm run build || (popd & exit /b 1)
popd

if not exist "deploy\windows\runtime" mkdir "deploy\windows\runtime"

echo Starting API on http://127.0.0.1:8000 ...
start "devicevault-api" /min cmd /c "cd /d ""%~dp0backend"" && .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --proxy-headers"

echo Starting nginx on http://localhost:8080 ...
"%NGINX_EXE%" -p "%~dp0." -e deploy/windows/runtime/error.log -c deploy/windows/nginx.conf -t || exit /b 1
start "devicevault-nginx" /b "%NGINX_EXE%" -p "%~dp0." -e deploy/windows/runtime/error.log -c deploy/windows/nginx.conf

echo.
echo DeviceVault is running at http://localhost:8080
echo Login: admin@company.com / Admin123!
echo Run stop-production.bat to stop it.
endlocal
