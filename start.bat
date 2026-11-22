@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
echo ==========================================
echo   HuluXia Check-in (standalone)
echo   http://127.0.0.1:5002
echo ==========================================
python app.py
pause
