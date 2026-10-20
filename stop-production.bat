@echo off
REM Stops the nginx + API processes started by start-production.bat
setlocal
cd /d "%~dp0"

set "NGINX_EXE=nginx.exe"
if defined NGINX_HOME set "NGINX_EXE=%NGINX_HOME%\nginx.exe"

echo Stopping nginx ...
"%NGINX_EXE%" -p "%~dp0." -e deploy/windows/runtime/error.log -c deploy/windows/nginx.conf -s quit 2>nul

echo Stopping API ...
taskkill /fi "WINDOWTITLE eq devicevault-api*" /t /f >nul 2>&1

echo Stopped.
endlocal
