@echo off
echo ==========================================
echo    Starting Cygnus UI Navigator Project
echo ==========================================

:: Start Backend in a new terminal window
echo [Step 1/2] Starting Backend...
start cmd /k "title Cygnus Backend && echo Starting FastAPI Server... && call cygnusVenv\Scripts\activate && uvicorn backend.main:app --reload --port 8000"

:: Wait a moment for backend to initialize
timeout /t 2 >nul

:: Start Frontend in a new terminal window
echo [Step 2/2] Starting Frontend...
start cmd /k "title Cygnus Frontend && echo Starting React Development Server... && cd frontend && npm start"

echo.
echo Components are starting in separate terminal windows.
echo Please keep both windows open while using the app.
echo.
pause
