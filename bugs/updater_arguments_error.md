## Status: ✅ RESOLVED

**Resolved:** 2025-11-21
**Commit:** Pending

**Solution:**
1. Modified `update_manager.py` to build and launch updater as separate .exe when frozen
2. Updated `build.bat` to build `updater.exe` using PyInstaller and copy it to the main app directory
3. Added proper subprocess creation flags to suppress console window

Changes:
- `src/update_manager.py` (lines 199-236): Check if frozen, look for updater.exe, launch it directly
- `build.bat` (lines 30-40): Build updater.exe as --onefile and copy to dist directory

---

# Updater Script - Arguments Not Recognized

**Date Reported:** 2025-11-21
**Priority:** High
**Component:** Auto-Update System / External Updater

## Description

When clicking the "Install Update" button (leftmost button) in the update dialog, the application crashes with an argument parsing error:

```
usage: LMU_Telemetry_Logger.exe [-h] [--settings] [--config CONFIG]
LMU_Telemetry_Logger.exe: error: unrecognized arguments: C:\Program Files\LMU Telemetry Logger\_internal\updater.py C:\Program Files\LMU Telemetry Logger\LMU_Telemetry_Logger.exe C:\Users\david\AppData\Local\Temp\LMU_Telemetry_Logger_v0.3.2.exe
```

## Expected Behavior

When user clicks "Install Update":
1. Application should launch external updater script
2. Updater should run independently (not through argparse)
3. Main application should exit gracefully
4. Updater replaces .exe and relaunches app

## Actual Behavior

The application tries to parse updater arguments through its own argparse, causing an error.

## Root Cause

When bundled as .exe, `sys.executable` points to `LMU_Telemetry_Logger.exe`, not a Python interpreter. The code was trying to run:
```
LMU_Telemetry_Logger.exe updater.py old.exe new.exe
```
This caused the main app's argparse to fail because it doesn't recognize those arguments.

## Resolution

**1. Build updater as separate .exe:**
Added to build.bat:
```batch
pyinstaller --onefile --noconsole ^
    --name "updater" ^
    --icon=NONE ^
    --hidden-import psutil ^
    updater.py
copy /Y dist\updater.exe dist\LMU_Telemetry_Logger\updater.exe
```

**2. Launch updater.exe directly when frozen:**
Updated `src/update_manager.py`:
```python
if getattr(sys, 'frozen', False):
    # Look for bundled updater.exe
    updater_exe = app_dir / "updater.exe"
    subprocess.Popen([
        str(updater_exe),
        str(current_exe),
        str(new_exe)
    ], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
```

## Environment

- **Platform:** Windows
- **Installation Path:** C:\Program Files\LMU Telemetry Logger\
- **PyInstaller Build:** Yes (bundled .exe)

## Related Files

- `src/update_manager.py` - `download_and_install()` method (lines 199-236)
- `updater.py` - External updater script
- `build.bat` - PyInstaller build script (lines 30-40)

## Impact

Critical - Update functionality completely broken, users cannot install updates
