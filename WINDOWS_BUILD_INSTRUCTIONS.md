# Windows Build Instructions

This guide explains how to build the LMU Telemetry Logger executable on Windows for testing the v0.2.0 release with opponent lap tracking.

## Prerequisites

1. **Python 3.10 or higher**
   - Download from: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation

2. **Git** (to clone the repository)
   - Download from: https://git-scm.com/download/win

3. **Le Mans Ultimate** (for testing with real telemetry)

4. **LMU Runtime Dependencies** (Required!)
   - Navigate to: `C:\Program Files (x86)\Steam\steamapps\common\Le Mans Ultimate\support\runtimes\`
   - Install **all** runtime installers:
     - `vc_redist.x64.exe` (Visual C++ Redistributable) - **Required!**
     - Any other installers present
   - Restart your computer (recommended)
   - **Note**: If you've already played LMU, these may already be installed

## Build Steps

### 1. Clone the Repository

Open Command Prompt or PowerShell:

```cmd
cd C:\
git clone https://github.com/davedean/eztel-writer.git
cd eztel-writer
```

Or download specific release:
```cmd
cd C:\
git clone --branch v0.2.0 https://github.com/davedean/eztel-writer.git
cd eztel-writer
```

### 2. Create Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your command prompt.

### 3. Install Dependencies

```cmd
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-windows.txt
pip install pyinstaller
```

### 4. Run Tests (Optional but Recommended)

```cmd
pytest -v
```

Expected: **91/91 tests passing**

### 5. Build Executable

```cmd
build.bat
```

This will:
- Clean previous builds
- Build single executable using PyInstaller
- Create `dist\LMU_Telemetry_Logger.exe`

Build takes ~1-2 minutes.

### 6. Test the Executable

```cmd
cd dist
LMU_Telemetry_Logger.exe
```

The logger will:
1. Wait for Le Mans Ultimate to start
2. Automatically capture player laps
3. Automatically capture opponent laps (fastest only)
4. Save CSV files to `./telemetry_output/`

## Expected Output

When you complete a lap:
```
*** Lap 3 completed!
    Lap time: 125.234s
    Samples: 5432
    [OK] Saved to: ./telemetry_output/2025-11-20_14-30_bahrain-international-circuit_toyota-gr010_dean-davids_lap3_t125.234s.csv
```

When an opponent completes a lap:
```
*** Opponent lap completed: Alice Johnson
    Lap 3: 122.156s
    Position: P2
    Car: Ferrari 499P
    Samples: 5387
    Fastest: True
    [OK] Saved to: ./telemetry_output/2025-11-20_14-30_bahrain-international-circuit_ferrari-499p_alice-johnson_lap3_t122.156s.csv
```

## Configuration

Edit `example_app.py` to customize:

```python
self.telemetry_loop = TelemetryLoop({
    'target_process': 'Le Mans Ultimate',  # Process name
    'poll_interval': 0.01,                 # 100Hz polling
    'track_opponents': True,                # Enable opponent tracking
    'track_opponent_ai': False,            # Don't track AI (remote players only)
})
```

## Troubleshooting

### "Python not found"
- Reinstall Python and check "Add to PATH"
- Or use full path: `C:\Python310\python.exe`

### "pyinstaller not found"
- Ensure virtual environment is activated: `venv\Scripts\activate`
- Reinstall: `pip install pyinstaller`

### "LMU not detected"
- Check process name in Task Manager
- Update `target_process` in `example_app.py` if different
- Default: `'Le Mans Ultimate'`

### Build errors
- Try cleaning: `rmdir /s /q build dist`
- Rebuild: `build.bat`

### No telemetry data or "Shared memory not available"
- **Install LMU runtimes** (see Prerequisites #4 above) - most common cause!
- Ensure rF2SharedMemoryMapPlugin is installed and enabled in LMU
- Check LMU settings for shared memory plugin
- Restart your computer after installing runtimes

### DLL load errors or "Failed to load shared memory library"
- **Install LMU runtimes** from `LMU/support/runtimes/` (see Prerequisites #4)
- Ensure you installed the x64 version of Visual C++ Redistributable
- Restart your computer after installation
- Verify LMU itself runs properly (if LMU doesn't work, the logger won't either)

## Testing Opponent Tracking

To test opponent lap tracking:

1. **Join Multiplayer Session**
   - Online race or practice session with other drivers
   - Or use AI drivers (enable `track_opponent_ai: True`)

2. **Expected Behavior**
   - Logger tracks all remote players automatically
   - Saves only fastest lap per opponent
   - Status shows: `Opponents: N` (number of tracked opponents)

3. **File Naming**
   - Player laps: `{date}_{time}_{track}_{car}_dean-davids_lap{N}_t{time}s.csv`
   - Opponent laps: `{date}_{time}_{track}_{car}_alice-johnson_lap{N}_t{time}s.csv`

4. **Validation**
   - Check opponent CSV files have correct driver name in metadata
   - Verify lap times are realistic
   - Compare telemetry data quality with player laps

## Report Issues

Found a bug? Report at:
https://github.com/davedean/eztel-writer/issues

Include:
- Error message
- Build output
- Python version: `python --version`
- LMU version
- Steps to reproduce
