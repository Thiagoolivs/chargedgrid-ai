@echo off
title ChargeGrid AI
set "PYTHONPATH=%~dp0"
cd /d "%~dp0"
echo.
echo  Iniciando ChargeGrid AI em http://localhost:8001
echo.
"%~dp0..\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8001
pause
