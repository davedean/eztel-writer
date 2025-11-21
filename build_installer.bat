@echo off
REM =============================================================================
REM 1Lap - Complete Build Script
REM =============================================================================
REM This script builds both the PyInstaller executable and the Inno Setup installer
REM
REM Prerequisites:
REM   1. Python 3.8+ with all dependencies installed (see requirements.txt)
REM   2. PyInstaller (pip install pyinstaller)
REM   3. Inno Setup 6 installed (download from https://jrsoftware.org/isdl.php)
REM
REM Usage:
REM   build_installer.bat              - Build both exe and installer
REM   build_installer.bat --exe-only   - Build only the PyInstaller executable
REM   build_installer.bat --help       - Show this help message
REM =============================================================================

setlocal enabledelayedexpansion

REM Parse command line arguments
set BUILD_EXE=1
set BUILD_INSTALLER=1

if "%1"=="--exe-only" (
    set BUILD_INSTALLER=0
    echo Build mode: PyInstaller executable only
    echo.
)

if "%1"=="--help" (
    echo Usage: build_installer.bat [--exe-only] [--help]
    echo.
    echo Options:
    echo   --exe-only    Build only the PyInstaller executable, skip installer
    echo   --help        Display this help message
    echo.
    exit /b 0
)

echo =============================================================================
echo 1Lap - Complete Build Process
echo =============================================================================
echo.

REM =============================================================================
REM Step 1: Build PyInstaller Executable
REM =============================================================================

if %BUILD_EXE%==1 (
    echo [Step 1/3] Building PyInstaller executable...
    echo.
    echo Running build.bat to create executable...
    call build.bat

    if errorlevel 1 (
        echo.
        echo ERROR: PyInstaller build failed!
        echo Please check the error messages above.
        pause
        exit /b 1
    )

    echo.
    echo [Step 1/3] Executable build complete!
    echo.
) else (
    echo [Step 1/3] Skipping executable build (using existing build)
    echo.
)

REM =============================================================================
REM Step 2: Verify PyInstaller Output
REM =============================================================================

echo [Step 2/3] Verifying PyInstaller output...
echo.

if not exist "dist\1Lap\1Lap.exe" (
    echo ERROR: PyInstaller executable not found!
    echo Expected location: dist\1Lap\1Lap.exe
    echo.
    echo Please run build.bat first to create the executable.
    pause
    exit /b 1
)

echo Found: dist\1Lap\1Lap.exe
echo Verification complete!
echo.

REM =============================================================================
REM Step 3: Build Inno Setup Installer
REM =============================================================================

if %BUILD_INSTALLER%==0 (
    echo [Step 3/3] Skipping installer build (--exe-only mode)
    echo.
    echo Build complete! Executable is ready at:
    echo dist\1Lap\1Lap.exe
    echo.
    pause
    exit /b 0
)

echo [Step 3/3] Building Inno Setup installer...
echo.

REM Check if Inno Setup is installed
set INNO_SETUP_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set INNO_SETUP_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set INNO_SETUP_PATH=C:\Program Files\Inno Setup 6\ISCC.exe
)

if "%INNO_SETUP_PATH%"=="" (
    echo ERROR: Inno Setup 6 not found!
    echo.
    echo Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo Expected location:
    echo   - C:\Program Files (x86)\Inno Setup 6\ISCC.exe
    echo   - C:\Program Files\Inno Setup 6\ISCC.exe
    echo.
    pause
    exit /b 1
)

echo Found Inno Setup compiler at:
echo %INNO_SETUP_PATH%
echo.

REM Run Inno Setup compiler
echo Compiling installer script...
"%INNO_SETUP_PATH%" "installer\1Lap_Setup.iss"

if errorlevel 1 (
    echo.
    echo ERROR: Inno Setup compilation failed!
    echo Please check the error messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo [Step 3/3] Installer build complete!
echo.

REM =============================================================================
REM Build Complete
REM =============================================================================

echo =============================================================================
echo Build Complete!
echo =============================================================================
echo.
echo Installer created successfully:
for %%f in (installer\output\1Lap_Setup_*.exe) do (
    echo   %%f
    set INSTALLER_SIZE=%%~zf
    set /a INSTALLER_SIZE_MB=!INSTALLER_SIZE! / 1048576
    echo   Size: !INSTALLER_SIZE_MB! MB
)
echo.
echo You can now distribute this installer to users.
echo.
echo Next steps:
echo   1. Test the installer on a clean Windows system
echo   2. Verify all features work correctly
echo   3. Upload to GitHub releases
echo.
pause
