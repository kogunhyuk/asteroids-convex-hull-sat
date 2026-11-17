@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo [1/3] pygame, pyinstaller 설치 확인...
python -m pip install --upgrade pygame pyinstaller
if errorlevel 1 goto :error

echo [2/3] 실행 파일 만드는 중... (1~2분 걸릴 수 있습니다)
python -m PyInstaller --onefile --windowed --noconfirm --name AsteroidsCollision main.py
if errorlevel 1 goto :error

echo [3/3] 완료: dist\AsteroidsCollision.exe
explorer dist
pause
exit /b 0

:error
echo.
echo 오류가 발생했습니다. 위 메시지를 확인하세요.
echo (python 명령을 찾을 수 없다면 Anaconda Prompt에서 이 파일을 실행하세요)
pause
exit /b 1
