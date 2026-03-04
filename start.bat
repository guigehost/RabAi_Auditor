@echo off
echo ========================================
echo Starting Intelligent Audit Tool
echo ========================================

echo.
echo [1/4] Checking Python environment...
python --version
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.10+
    pause
    exit /b 1
)

echo.
echo [2/4] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [3/4] Starting backend server...
start "Backend Server" cmd /k "python main.py"

echo.
echo [4/4] Starting frontend development server...
cd frontend
if exist node_modules (
    echo Node modules found, starting dev server...
    start "Frontend Server" cmd /k "npm start"
) else (
    echo Installing frontend dependencies...
    call npm install
    start "Frontend Server" cmd /k "npm start"
)

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to exit this window...
pause > nul
