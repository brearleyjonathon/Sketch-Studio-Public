@echo off
title Sketch Styler
cd /d "%~dp0"

:: ── Check for Python ──────────────────────────────────────────────────────────
where python >nul 2>&1
if %errorlevel% neq 0 (
  echo Python not found. Please install Python from python.org
  pause
  exit /b 1
)

:: ── Find a free port and start local server ───────────────────────────────────
set PORT=8741

:: Kill any existing server on that port (ignore errors)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8741 "') do (
  taskkill /PID %%a /F >nul 2>&1
)

:: Start proxy server in background
start /min "" python server.py

:: Wait a moment for the server to start
timeout /t 1 /nobreak >nul

:: ── Open in browser ───────────────────────────────────────────────────────────
set "URL=http://127.0.0.1:%PORT%/sketch_styler.html"
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "CHROME86=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
set "EDGE64=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"

if exist "%CHROME%"   ( start "" "%CHROME%"   --new-window "%URL%" & goto :done )
if exist "%CHROME86%" ( start "" "%CHROME86%" --new-window "%URL%" & goto :done )
if exist "%EDGE64%"   ( start "" "%EDGE64%"   --new-window "%URL%" & goto :done )
if exist "%EDGE%"     ( start "" "%EDGE%"     --new-window "%URL%" & goto :done )

:: Fallback
start "" "%URL%"

:done
echo Server running at %URL%
echo Close this window to stop the server.
pause >nul
