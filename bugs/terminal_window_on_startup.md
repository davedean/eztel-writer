## Status: ✅ RESOLVED

**Resolved:** 2025-11-21
**Component:** Build Configuration / PyInstaller

**Solution:** The `--noconsole` flag was already present in build.bat (line 18). The issue was that the user was running an older build. Verified that the current build.bat configuration is correct and will suppress the console window when rebuilt.

---

# Terminal Window Opens on Startup

**Date Reported:** 2025-11-21
**Priority:** High
**Component:** Build Configuration / PyInstaller

## Description

When the LMU_Telemetry_Logger.exe is launched, a terminal/console window opens alongside the application, even though the application is designed to run in system tray mode only.

## Expected Behavior

The application should start silently in the system tray without any console window appearing.

## Actual Behavior

A console/terminal window opens when the .exe starts, which:
- Is unnecessary for a system tray application
- Creates a poor user experience
- May confuse users who expect a silent background service

## Environment

- **Platform:** Windows
- **Build Tool:** PyInstaller
- **Entry Point:** tray_app.py

## Root Cause

User was running an older build from before `--noconsole` flag was added to build.bat.

## Resolution

Verified that build.bat (line 18) already includes `--noconsole` flag:
```batch
pyinstaller --onedir --noconsole ^
    --name "LMU_Telemetry_Logger" ^
    ...
```

User needs to rebuild using `build.bat` to get the updated executable.

## Related Files

- `build.bat` - PyInstaller build script (line 18)
- `tray_app.py` - Main entry point

## Impact

Medium - Application functions correctly but provides poor UX
