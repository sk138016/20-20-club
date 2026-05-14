@echo off
cd /d "%~dp0"
echo 최신 데이터 가져오는 중...
git pull
echo.
echo 대시보드 시작 중... (브라우저가 자동으로 열립니다)
start http://localhost:8080
python -m http.server 8080 --directory docs
pause
