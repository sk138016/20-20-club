@echo off
SET PROJECT_DIR=C:\Users\rlatp\Documents\Claude\Projects\2. Stock Projects\1. 20-20 Club
SET PYTHON=%PROJECT_DIR%\venv\Scripts\python.exe

cd /d "%PROJECT_DIR%"
call "%PROJECT_DIR%\venv\Scripts\activate.bat"
"%PYTHON%" "%PROJECT_DIR%\main.py"

echo [%DATE% %TIME%] exit code=%ERRORLEVEL% >> "%PROJECT_DIR%\logs\scheduler.log"
exit /b %ERRORLEVEL%
