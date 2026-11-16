@echo off
rem Job Apply launcher for Windows. Double-click or run from a terminal.
setlocal
cd /d "%~dp0"
if not exist config.json (
  echo No config.json found - running first-time setup.
  call :python setup.py
)
echo Starting Job Apply (keep this window open; press Ctrl+C to stop)
call :python app\server.py %*
pause
exit /b

:python
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 %*
) else (
  python %*
)
exit /b
