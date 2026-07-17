@echo off
cd /d "%~dp0"

echo =========================================
echo   rwmod :: Skip build, start now
echo =========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] .venv not found, run from PowerShell: uv sync
    pause
    exit /b 1
)

if not exist "static\index.html" (
    echo [!] static\index.html not found -- frontend not built yet.
    echo     Run start.bat to build frontend, or:
    echo       cd frontend ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
)

echo [*] Skipping frontend build -- using existing static files.
echo [*] Starting server on http://localhost:8000 ...
start "" http://localhost:8000
.venv\Scripts\python.exe -m uvicorn rwmod.server:app --host 0.0.0.0 --port 8000

pause
