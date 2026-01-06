@echo off
chcp 65001 >nul
echo ===================================================
echo       正在啟動 ETF 追蹤系統 (Starting System)
echo ===================================================

echo 1. 啟動後端伺服器 (Starting Backend)...
start "ETF Backend Server" cmd /k "python start.py"

echo 2. 啟動前端介面 (Starting Frontend)...
cd frontend
start "ETF Frontend" cmd /k "npm run dev"
cd ..

echo 3. 等待系統就緒 (Waiting)...
timeout /t 5 >nul

echo 4. 開啟瀏覽器 (Opening Browser)...
start http://localhost:5173

echo ===================================================
echo 系統已啟動！請勿關閉跳出的兩個黑色視窗。
echo System Started! Please keep the new windows open.
echo ===================================================
pause
