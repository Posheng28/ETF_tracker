@echo off
chcp 65001 >nul
echo ==========================================
echo ETF Trace 系統安裝腳本 (System Setup)
echo ==========================================

echo [1/3] 檢查環境 (Checking Environment)...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 找不到 Python (Python not found)
    echo 請前往 https://www.python.org/downloads/ 下載並安裝 Python。
    echo ★重要: 安裝時請務必勾選 "Add Python to PATH" 選項。
    echo.
    pause
    exit /b
)
echo Python: OK

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 找不到 Node.js (Node.js not found)
    echo 請前往 https://nodejs.org/ 下載並安裝 Node.js (建議下載 LTS 版本)。
    echo.
    pause
    exit /b
)
echo Node.js: OK

echo.
echo [2/3] 安裝後端依賴 (Installing Backend)...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] 後端安裝失敗 (Backend install failed)
    pause
    exit /b
)
cd ..

echo.
echo [3/3] 安裝前端依賴 (Installing Frontend)...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] 前端安裝失敗 (Frontend install failed)
    pause
    exit /b
)
cd ..

echo.
echo ==========================================
echo ★ 安裝完成！(Setup Complete)
echo 請直接執行 run.bat 啟動系統。
echo ==========================================
pause
