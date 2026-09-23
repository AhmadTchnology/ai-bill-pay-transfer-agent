@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting mock wallet API on http://127.0.0.1:8001 (needed by tests) ...
start "wallet-api" cmd /c "py -m uvicorn wallet_api.main:app --port 8001"
timeout /t 4 /nobreak >nul

echo Running test suite (replay mode - no API key needed) ...
py tests\run_tests.py --replay
echo.
echo To run live-mode tests with the real GLM-5.3 NLU: py tests\run_tests.py --live
pause
