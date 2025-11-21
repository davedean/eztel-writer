@echo off
echo ============================================================
echo Building 1Lap Executable
echo ============================================================
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build main executable
echo.
echo Building with PyInstaller...
python -m PyInstaller --onedir --noconsole ^
    --name "1Lap" ^
    --icon=NONE ^
    --add-data "src;src" ^
    --hidden-import psutil ^
    --hidden-import datetime ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --collect-all src ^
    tray_app.py

echo.
echo Building updater executable...
pyinstaller --onefile --noconsole ^
    --name "updater" ^
    --icon=NONE ^
    --hidden-import psutil ^
    updater.py

REM Copy updater.exe to main app directory
echo.
echo Copying updater.exe to main app directory...
copy /Y dist\updater.exe dist\1Lap\updater.exe

echo.
echo ============================================================
echo Build Complete!
echo.
echo Executable location: dist\1Lap\1Lap.exe
echo Updater location:    dist\1Lap\updater.exe
echo.
echo The executable is in a directory bundle with all dependencies.
echo To distribute, use the installer: run build_installer.bat
echo ============================================================
pause
