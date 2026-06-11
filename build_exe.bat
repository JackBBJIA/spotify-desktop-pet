@echo off
chcp 65001 >nul
echo ========================================
echo   桌面宠物 — 打包为 EXE
echo ========================================
echo.

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM Install dependencies
echo [1/3] 安装依赖...
pip install winsdk requests pillow syncedlyrics pyinstaller -q

REM Clean old build
echo [2/3] 清理旧文件...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Build
echo [3/3] 打包中...
pyinstaller --onefile --windowed --name "PixelBunny" --add-data "src;src" src/main.py

echo.
echo ========================================
echo   完成！EXE 在 dist\PixelBunny.exe
echo ========================================
pause
