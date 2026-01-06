@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo ETF Trace 系統一鍵安裝腳本 (Auto Setup)
echo ==========================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] 檢測到管理員權限 (Administrator Mode: ON)
) else (
    echo [WARNING] 建議右鍵選擇「以系統管理員身分執行」此腳本，
    echo 以確保自動安裝功能正常運作。
    echo.
)

echo.
echo [1/3] 檢查與安裝系統環境 (Checking System)...

:: Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] 找不到 Python，正在嘗試自動安裝...
    echo 正在呼叫 Windows Package Manager (winget)...
    winget install -e --id Python.Python.3.12 --scope machine --accept-package-agreements --accept-source-agreements
    
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] 自動安裝 Python 失敗。
        echo 請手動下載: https://www.python.org/downloads/
        pause
        exit /b
    )
    echo Python 安裝完成！請關閉此視窗並重新執行 setup.bat 以讀取新的環境變數。
    pause
    exit
) else (
    echo Python: 已安裝 (OK)
)

:: Check Node.js
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] 找不到 Node.js，正在嘗試自動安裝...
    echo 正在呼叫 Windows Package Manager (winget)...
    winget install -e --id OpenJS.NodeJS.LTS --scope machine --accept-package-agreements --accept-source-agreements
    
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] 自動安裝 Node.js 失敗。
        echo 請手動下載: https://nodejs.org/
        pause
        exit /b
    )
    echo Node.js 安裝完成！請關閉此視窗並重新執行 setup.bat 以讀取新的環境變數。
    pause
    exit
) else (
    echo Node.js: 已安裝 (OK)
)

echo.
echo [2/3] 安裝後端依賴 (Installing Backend)...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] 後端套件安裝失敗。建議升級 pip (python -m pip install --upgrade pip) 後重試。
    pause
    exit /b
)
cd ..

echo.
echo [3/3] 安裝前端依賴 (Installing Frontend)...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] 前端套件安裝失敗。
    pause
    exit /b
)
cd ..

echo.
echo ==========================================
echo ★ 安裝全部完成！(Setup Complete)
echo ==========================================
echo 請執行 run.bat 啟動系統。
pause
