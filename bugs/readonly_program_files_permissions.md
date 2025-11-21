## Status: ✅ RESOLVED

**Resolved:** 2025-11-21
**Branch:** claude/fix-readonly-permissions-01DzJrpGCEDntuv45hodQfL4
**Version Fixed:** 0.3.1

**Solution:** Moved configuration and log files from Program Files directory to user's AppData folder using platform-appropriate paths:
- Windows: `%LOCALAPPDATA%\LMU Telemetry Logger\`
- macOS: `~/Library/Application Support/LMU Telemetry Logger/`
- Linux: `~/.local/share/lmu-telemetry-logger/`

---

# Bug: Permission Denied When Writing to Program Files

## Description

The application crashed on startup with a `PermissionError` when trying to write log files to the Program Files directory.

## Error Message

```
C:\Program Files\LMU Telemetry Logger>LMU_Telemetry_Logger.exe
Traceback (most recent call last):
  File "tray_app.py", line 75, in <module>
  File "tray_app.py", line 65, in setup_logging
  File "logging\__init__.py", line 1231, in __init__
  File "logging\__init__.py", line 1263, in _open
PermissionError: [Errno 13] Permission denied: 'C:\\Program Files\\LMU Telemetry Logger\\telemetry_logger.log'
[PYI-26556:ERROR] Failed to execute script 'tray_app' due to unhandled exception!
```

## Root Cause

The application attempted to write files (logs and config) to `C:\Program Files\LMU Telemetry Logger\`, which is a read-only directory for normal users on Windows. This is a common mistake in Windows application development.

**Why Program Files is read-only:**
- Windows enforces UAC (User Access Control) restrictions
- Normal users don't have write permissions to `C:\Program Files\`
- Only administrators can write to Program Files
- This is by design to prevent malware and maintain system integrity

## Affected Files

The following files were being written to the installation directory:
1. `telemetry_logger.log` - Application log file
2. `config.json` - User configuration file

## Impact

- **Severity**: Critical (application crash on startup)
- **Affected Versions**: v0.3.0 and earlier
- **Workaround**: Run as administrator (not recommended for normal use)

## Solution

### Implementation

Created a new `src/app_paths.py` module that provides platform-appropriate directories for application data:

```python
def get_app_data_dir() -> Path:
    """Get the platform-appropriate application data directory

    Returns:
        Path to application data directory (created if doesn't exist)

    Examples:
        - Windows: C:\\Users\\username\\AppData\\Local\\LMU Telemetry Logger\\
        - macOS: ~/Library/Application Support/LMU Telemetry Logger/
        - Linux: ~/.local/share/lmu-telemetry-logger/
    """
```

### Changes Made

1. **Created `src/app_paths.py`:**
   - `get_app_data_dir()` - Returns platform-appropriate app data directory
   - `get_config_file_path()` - Returns path to config.json in app data
   - `get_log_file_path()` - Returns path to log file in app data
   - `migrate_config_if_needed()` - Migrates config from old location

2. **Updated `tray_app.py`:**
   - `setup_logging()` now uses `get_log_file_path()`
   - `main()` now uses `get_config_file_path()` with migration support
   - Added import for `app_paths` module

3. **Updated `example_app.py`:**
   - `main()` now uses `get_config_file_path()` with migration support
   - Added import for `app_paths` module

4. **Updated `USER_GUIDE.md`:**
   - Documented new file locations
   - Explained why files are in AppData
   - Provided typical paths for users

### New File Locations

**Windows:**
- Config: `C:\Users\<username>\AppData\Local\LMU Telemetry Logger\config.json`
- Logs: `C:\Users\<username>\AppData\Local\LMU Telemetry Logger\telemetry_logger.log`

**macOS:**
- Config: `~/Library/Application Support/LMU Telemetry Logger/config.json`
- Logs: `~/Library/Application Support/LMU Telemetry Logger/telemetry_logger.log`

**Linux:**
- Config: `~/.local/share/lmu-telemetry-logger/config.json`
- Logs: `~/.local/share/lmu-telemetry-logger/telemetry_logger.log`

### Migration Strategy

The fix includes automatic migration of existing config files:
1. On first run with new version, checks for `config.json` in old location
2. If found and new location doesn't exist, copies to new location
3. User's settings are preserved automatically
4. No manual intervention required

## Testing

- ✅ Verified `app_paths` module imports correctly
- ✅ Verified `tray_app.py` imports correctly
- ✅ Verified `example_app.py` imports correctly
- ✅ Verified USER_GUIDE.md updated with new locations
- Remaining: Full integration test on Windows with installer

## Prevention

**Best Practices for Windows Applications:**
1. Never write user data to Program Files
2. Use `%LOCALAPPDATA%` for user-specific config/logs
3. Use `%APPDATA%` for roaming user data
4. Use `%PROGRAMDATA%` for machine-wide config (requires admin)
5. Follow platform conventions for all OSes

## References

- Windows folder structure: https://docs.microsoft.com/en-us/windows/win32/shell/knownfolderid
- macOS Application Support: https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/FileSystemOverview/FileSystemOverview.html
- XDG Base Directory Specification (Linux): https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
