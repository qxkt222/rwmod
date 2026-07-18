@echo off
cd /d "%~dp0"

echo =========================================
echo   rwmod :: RimWorld Mod Manager
echo =========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] .venv not found, run from PowerShell: uv sync
    pause
    exit /b 1
)

echo [1/2] Building frontend...
set NPX_CMD=npx.cmd
if exist "D:\DevTools\links\npx.cmd" set NPX_CMD=D:\DevTools\links\npx.cmd
if not exist "%NPX_CMD%" (
    where /R "%APPDATA%\npm" npx.cmd >nul 2>&1 && set "NPX_CMD=npx.cmd"
)

cd frontend
if not exist "%NPX_CMD%" (
    echo     npx not found, skipping frontend build.
    echo     If frontend looks outdated, run in terminal:
    echo       cd frontend ^&^& npx vite build --outDir ../static --emptyOutDir
    cd ..
    goto :start
)

echo     Building...
call "%NPX_CMD%" vite build --outDir ../static --emptyOutDir
if errorlevel 1 (
    echo [!] Build failed, using existing static files.
    cd ..
    goto :start
)
cd ..

:start
echo [2/2] Starting server on http://localhost:8000 ...
start "" http://localhost:8000
.venv\Scripts\python.exe -m uvicorn rwmod.server:app --host 0.0.0.0 --port 8000

pause
