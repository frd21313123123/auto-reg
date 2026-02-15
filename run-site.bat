@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"

set "BACKEND_DIR=%~dp0web\backend"
set "FRONTEND_DIR=%~dp0web\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

if not exist "%BACKEND_DIR%\app\main.py" (
  echo [ERROR] Backend not found: "%BACKEND_DIR%\app\main.py"
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] Frontend not found: "%FRONTEND_DIR%\package.json"
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Command python not found in PATH.
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Command npm not found in PATH.
  pause
  exit /b 1
)

echo.
echo [1/4] Installing backend Python dependencies...
pushd "%BACKEND_DIR%"
python -m pip install -r requirements.txt
if errorlevel 1 (
  popd
  echo [ERROR] Failed to install backend dependencies.
  pause
  exit /b 1
)
popd

echo.
echo [2/4] Installing frontend npm dependencies (if needed)...
pushd "%FRONTEND_DIR%"
if not exist "node_modules" (
  call npm install
  if errorlevel 1 (
    popd
    echo [ERROR] Failed to install frontend dependencies.
    pause
    exit /b 1
  )
) else (
  echo node_modules already exists, skipping npm install.
)
popd

echo.
echo [3/4] Starting backend on port %BACKEND_PORT%...
start "Auto-reg Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port %BACKEND_PORT%"

echo [4/4] Starting frontend on port %FRONTEND_PORT%...
start "Auto-reg Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && npm run dev -- --port %FRONTEND_PORT%"

echo.
echo Website started:
echo   Backend:  http://localhost:%BACKEND_PORT%
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo.
echo Stop services in the separate Backend/Frontend windows.
pause

exit /b 0
