@echo off
title AI PDF Chatbot Launcher
cd /d "%~dp0"

echo ========================================================
echo                AI PDF Chatbot Assistant
echo ========================================================
echo.

REM Detect appropriate Python launcher (py or python)
set PYTHON_CMD=py
py --version >nul 2>&1
if errorlevel 1 (
    set PYTHON_CMD=python
)

echo Using Python command: %PYTHON_CMD%
echo.
echo [1/2] Starting FastAPI Backend on port 8000...
start "FastAPI Backend (Port 8000)" cmd /k "cd /d ""%~dp0"" && %PYTHON_CMD% -m uvicorn backend.main:app --reload --port 8000"

echo FastAPI Backend started: http://127.0.0.1:8000
echo Swagger API Docs:        http://127.0.0.1:8000/docs
echo.

echo Waiting 3 seconds for backend to initialize...
timeout /t 3 /nobreak >nul

echo [2/2] Starting Streamlit Frontend on port 8501...
echo Streamlit UI:            http://localhost:8501
echo.

%PYTHON_CMD% -m streamlit run frontend/app.py --server.port 8501 --server.headless true

pause
