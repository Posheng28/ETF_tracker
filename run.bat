@echo off
:: ==========================================
:: ETF Tracker - Launcher
:: ==========================================

echo [INFO] Starting System...

echo.
echo 1. Starting Backend Server...
start "ETF Backend Server" cmd /k "python start.py"

echo.
echo 2. Starting Frontend Interface...
cd frontend
start "ETF Frontend" cmd /k "npm run dev"
cd ..

echo.
echo 3. Waiting for services to initialize...
timeout /t 5 >nul

echo.
echo 4. Opening Browser...
start http://localhost:5173

echo.
echo ==========================================
echo [SUCCESS] System Started!
echo Please keep the two black windows open.
echo ==========================================
pause
