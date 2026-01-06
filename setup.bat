@echo off
:: ==========================================
:: ETF Tracker - One Click Setup
:: ==========================================

echo [INFO] Checking Administrator Privileges...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator.
) else (
    echo [WARNING] Not running as Administrator.
    echo Please right-click and select "Run as Administrator" if installation fails.
    echo.
)

echo.
echo [1/3] Checking System Environment...

:: Check Python
where python >nul 2>nul
if %errorlevel% neq 0 goto InstallPython
echo [OK] Python is installed.
goto CheckNode

:InstallPython
echo [!] Python not found. Attempting auto-install via Winget...
winget install -e --id Python.Python.3.12 --scope machine --accept-package-agreements --accept-source-agreements
if %errorlevel% neq 0 goto PythonFail
echo [OK] Python installed successfully.
echo Please close this window and run setup.bat again to refresh environment variables.
pause
exit

:PythonFail
echo.
echo [ERROR] Failed to install Python automatically.
echo Please download it manually: https://www.python.org/downloads/
pause
exit /b

:CheckNode
:: Check Node.js
where npm >nul 2>nul
if %errorlevel% neq 0 goto InstallNode
echo [OK] Node.js is installed.
goto InstallBackend

:InstallNode
echo [!] Node.js not found. Attempting auto-install via Winget...
winget install -e --id OpenJS.NodeJS.LTS --scope machine --accept-package-agreements --accept-source-agreements
if %errorlevel% neq 0 goto NodeFail
echo [OK] Node.js installed successfully.
echo Please close this window and run setup.bat again to refresh environment variables.
pause
exit

:NodeFail
echo.
echo [ERROR] Failed to install Node.js automatically.
echo Please download it manually: https://nodejs.org/
pause
exit /b

:InstallBackend
echo.
echo [2/3] Installing Backend Dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 goto BackendFail
cd ..
goto InstallFrontend

:BackendFail
echo [ERROR] Failed to install backend packages.
echo Try upgrading pip: python -m pip install --upgrade pip
pause
exit /b

:InstallFrontend
echo.
echo [3/3] Installing Frontend Dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 goto FrontendFail
cd ..
goto Finish

:FrontendFail
echo [ERROR] Failed to install frontend packages.
pause
exit /b

:Finish
echo.
echo ==========================================
echo [SUCCESS] Setup Complete!
echo ==========================================
echo You can now run 'run.bat' to start the system.
pause
