@echo off
cd /d %~dp0
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
if "%BAGER_ADMIN_PASSWORD%"=="" set /p BAGER_ADMIN_PASSWORD=Set dispatcher password: 
set COOKIE_SECURE=0
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
