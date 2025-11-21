# FileManager Directory Creation Blocks Startup

**Date Reported:** 2025-11-21
**Priority:** Low
**Component:** FileManager, Startup Performance

## Description

The FileManager initializes synchronously during app startup and creates the output directory immediately using `mkdir(parents=True, exist_ok=True)`. This could block the systray icon from appearing if the output directory is on slow storage.

## Expected Behavior

The systray icon should appear within 1-2 seconds of launching the app, regardless of output directory location.

## Actual Behavior

If the output directory is on a network drive, slow HDD, or being scanned by antivirus, directory creation could delay startup by several seconds.

## Impact

**Low** - Most users have output directory on fast local storage (SSD).

**Medium** - For users with output directory on:
- Network-mapped drives
- NAS storage
- Slow HDDs
- Directories being scanned by antivirus software

## Root Cause

In `src/file_manager.py:37`, the `__init__` method performs synchronous I/O:

```python
def __init__(self, config: Dict[str, Any] = None):
    self.config = config or {}
    self.output_dir = Path(self.config.get('output_dir', './telemetry_output'))
    self.filename_format = self.config.get(
        'filename_format',
        '{session_id}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv'
    )

    # Create output directory if it doesn't exist
    self.output_dir.mkdir(parents=True, exist_ok=True)  # <-- BLOCKS STARTUP
```

This happens in `tray_app.py:102` during `TrayTelemetryApp.__init__`, which runs **before** the systray icon is created (line 121).

## Startup Order

Current initialization sequence:
1. Load config (line 93) ✅ Fast
2. Initialize CSVFormatter (line 101) ✅ Fast
3. **Initialize FileManager (line 102)** ⚠️ **Creates directory synchronously**
4. Initialize telemetry reader (line 103) ✅ Fast (REST API now lazy)
5. Initialize TelemetryLoop (line 106) ✅ Fast
6. **Initialize TrayUI (line 121)** - Systray icon appears here
7. Show systray icon (line 410)

## Potential Solutions

### Option 1: Defer Directory Creation (Recommended)
Move `mkdir()` to first file write operation:
- Directory only created when first lap is saved
- Startup remains fast regardless of storage speed
- Add lazy initialization in `save_lap()` method

### Option 2: Async Directory Creation
Create directory in background thread:
- More complex implementation
- Requires thread synchronization
- Must handle race condition if lap saved before directory exists

### Option 3: Validate Path Only
During init, only validate path format (don't create):
- Create directory on first write
- Simple to implement
- Maintains fast startup

## Workarounds

For users experiencing slow startup:
1. Use local SSD path for output directory (not network drive)
2. Add app/directory to antivirus exclusions
3. Pre-create the output directory manually

## Related Files

- `src/file_manager.py` (line 37) - Directory creation
- `tray_app.py` (line 102) - FileManager initialization

## Testing

To reproduce slow startup:
1. Set output directory to network-mapped drive or slow storage
2. Launch app
3. Measure time until systray icon appears

Expected delay: 2-10 seconds depending on storage speed

## Notes

This is a **low-priority optimization** as:
- Directory creation is usually very fast (<10ms on local SSD)
- Most users use default local directory
- The REST API fix (already implemented) was the main bottleneck
- Directory must exist before first lap can be saved

**Recommendation:** Monitor user feedback. Only implement if users report slow startup after REST API fix.
