# Release Notes - v0.2.0: Opponent Lap Tracking

**Release Date**: 2025-11-20

## What's New

### 🏁 Opponent Lap Tracking (Multiplayer)

This release adds automatic opponent lap tracking during multiplayer sessions! The telemetry logger now captures data from other drivers and saves their fastest laps for comparison.

**Key Features**:
- ✅ **Fastest Lap Only**: Only saves fastest lap per opponent to control storage (~20MB for 20-driver session)
- ✅ **Smart Filtering**: Tracks remote players by default, AI optional
- ✅ **Consistent Naming**: Uses same filename format as player laps (includes track, car, driver, lap time)
- ✅ **Configurable**: Enable/disable opponent tracking, choose to include AI or not
- ✅ **Non-Blocking**: Opponent tracking errors won't crash the main logger

**Example Filenames**:
```
Player lap:
2025-11-20_14-30_bahrain-international-circuit_toyota-gr010_dean-davids_lap3_t125.234s.csv

Opponent lap:
2025-11-20_14-30_bahrain-international-circuit_ferrari-499p_alice-johnson_lap3_t122.156s.csv
```

### Configuration

In `example_app.py` or your custom app:
```python
TelemetryLoop({
    'track_opponents': True,        # Enable opponent tracking (default: True)
    'track_opponent_ai': False,     # Track AI opponents (default: False)
    'on_opponent_lap_complete': callback_function,
})
```

### Storage Impact

**Comparison**:
- **Option 2 (Fastest only)**: 20 drivers × 1 lap × 1MB = **20MB** ✅ IMPLEMENTED
- Option 1 (All laps): 20 drivers × 10 laps × 1MB = 200MB

### Testing Status

- ✅ **91/91 tests passing** (including 11 new OpponentTracker tests)
- ✅ **Tested on macOS** with mock opponents
- ⏳ **Windows testing pending** - needs real LMU multiplayer session

## Installation & Usage

### Windows Users (Production)

#### Prerequisites (Important!)

Before running the telemetry logger, you must install the LMU runtime dependencies:

1. Navigate to your LMU installation folder:
   - Default: `C:\Program Files (x86)\Steam\steamapps\common\Le Mans Ultimate\`
2. Open the `support\runtimes\` folder
3. Install **all** runtime installers:
   - `vc_redist.x64.exe` (Visual C++ Redistributable) - **Required!**
   - Any other installers present
4. Restart your computer (recommended)

**Note**: If you've already run LMU successfully, these may already be installed.

#### Running the Logger

1. Download the release and extract
2. Run `LMU_Telemetry_Logger.exe`
3. Start Le Mans Ultimate with multiplayer session
4. Logger will automatically capture player and opponent laps
5. Find CSV files in `./telemetry_output/` folder

**Note**: To build from source on Windows, run `build.bat` (requires Python 3.10+)

### Developers (macOS/Linux)

```bash
# Clone and setup
git clone <repo>
cd telemetry_writer
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest -v

# Run example app
python example_app.py
```

## Known Issues

- Windows multiplayer testing pending
- Opponent lap timing needs validation in real sessions
- Lap validity flag (`mCountLapFlag`) not yet checked

## What's Next (v0.3.0)

Potential future enhancements:
- Configuration UI for opponent tracking settings
- Persistent settings storage
- Advanced filtering (position-based, lap validity checks)
- Storage usage monitoring and cleanup

## Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete list of changes.

---

**Questions or Issues?**
Report at: https://github.com/davedean/eztel-writer/issues
