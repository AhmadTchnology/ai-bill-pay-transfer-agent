@echo off
chcp 65001 >nul
title Bill Pay ^& Transfer Agent - Demo

echo ============================================
echo  Bill Pay ^& Transfer Agent - starting demo
echo ============================================

cd /d "%~dp0"

echo [1/3] Starting mock wallet API on http://127.0.0.1:8001 ...
start "wallet-api" cmd /c "py -m uvicorn wallet_api.main:app --port 8001"

timeout /t 4 /nobreak >nul

echo [2/3] Starting web UI on http://127.0.0.1:8000 ...
start "web-ui" cmd /c "py -m uvicorn web.app:app --port 8000"

timeout /t 4 /nobreak >nul

echo [3/3] Opening browser ...
start http://127.0.0.1:8000

echo.
echo Demo running. Close both server windows to stop.
echo Note: for live NLU, put your GLM endpoint+key in .env (see .env.example)
pause >nul
