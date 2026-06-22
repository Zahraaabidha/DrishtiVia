@echo off
echo Starting ViolaVision 2.0...
echo.

:: Start FastAPI backend
start "ViolaVision API" cmd /k "cd /d %~dp0 && python -m uvicorn api:app --reload --port 8000"

:: Wait a moment then start React frontend
timeout /t 2 /nobreak >nul
start "ViolaVision UI" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Both servers starting...
echo   API:      http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API docs: http://localhost:8000/docs
echo.
pause
