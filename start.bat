@echo off
echo Starting Backend Server...
start "Backend" cmd /k "cd /d d:\testcode\audata && python main.py"
timeout /t 3 /nobreak >nul
echo Starting Frontend Server...
start "Frontend" cmd /k "cd /d d:\testcode\audata\frontend && npm start"
echo.
echo Services are starting...
echo Backend: http://localhost:9001
echo Frontend: http://localhost:3000
echo.
pause
