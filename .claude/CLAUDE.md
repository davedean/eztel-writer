# LMU Telemetry Logger - Claude Instructions

## Project Overview

This is a background telemetry logger for Le Mans Ultimate (LMU) that automatically captures and exports telemetry data to CSV files. The project uses a **cross-platform development strategy**: develop on macOS with mocks, then test/deploy on Windows with real LMU data.

**Current Status**: Phases 1-6 complete (core system fully functional, tested on Windows with live LMU, auto-update system implemented), Phase 7 in progress (executable built, final validation pending)

## Development Philosophy

### Test-Driven Development (TDD)
- **ALWAYS write tests before code** when implementing new features
- Tests should fail first, then write code to make them pass
- Current coverage: **175/175 tests passing, 100% coverage of implemented modules** (includes 54 auto-update tests)
- If tests can't pass after trying, ask user before modifying tests

### Cross-Platform Architecture
- Abstract platform-specific code behind interfaces
- `src/telemetry/telemetry_interface.py` - defines `TelemetryReaderInterface`
- `src/telemetry/telemetry_mock.py` - macOS implementation (simulates telemetry)
- `src/telemetry/telemetry_real.py` - Windows implementation ✅ COMPLETE
- Platform detection: `sys.platform == 'win32'` → real, else → mock

## Project Architecture

### Core Components (All Complete ✅)

1. **TelemetryReader** (`src/telemetry/`)
   - Interface-based design for cross-platform support
   - Mock reader simulates realistic racing data with lap progression
   - Real reader uses `pyRfactor2SharedMemory` (Windows only)

2. **ProcessMonitor** (`src/process_monitor.py`)
   - Auto-detects target process (LMU.exe on Windows, configurable on macOS)
   - Uses `psutil` for cross-platform process detection
   - Case-insensitive, partial name matching

3. **SessionManager** (`src/session_manager.py`)
   - Tracks session state: IDLE → DETECTED → LOGGING → (lap complete)
   - Detects lap changes by monitoring lap number
   - Buffers telemetry samples for current lap (with automatic normalization)
   - Generates unique session IDs (timestamp-based)
   - Integrates SampleNormalizer for data conversion

4. **SampleNormalizer** (`src/mvp_format.py`)
   - Converts raw telemetry to canonical MVP format
   - Handles fractional to percentage conversion (0-1 → 0-100% for throttle/brake/steering)
   - Sector estimation using track length
   - Ensures consistent field naming and units

5. **TelemetryLoop** (`src/telemetry_loop.py`)
   - Main polling loop (~100Hz by default)
   - Integrates ProcessMonitor, SessionManager, TelemetryReader
   - Triggers callbacks on lap completion
   - Supports pause/resume, start/stop

6. **CSVFormatter** (`src/csv_formatter.py`)
   - Formats telemetry data to **LMUTelemetry v2 MVP format**
   - 2 sections: metadata preamble (Key,Value pairs) + telemetry samples (12 columns)
   - Metadata: Format, Version, Player, TrackName, CarName, SessionUTC, LapTime [s], TrackLen [m]
   - 12 telemetry columns: LapDistance, LapTime, Sector, Speed, EngineRevs, ThrottlePercentage, BrakePercentage, Steer, Gear, X, Y, Z
   - File size: ~1 MB per lap (down from ~11 MB in old format)
   - See `example.csv` and `telemetry_format_analysis.md` for exact format specification

7. **FileManager** (`src/file_manager.py`)
   - Saves CSV files to disk with configurable naming
   - Default: `{session_id}_lap{lap}.csv`
   - Sanitizes filenames, manages output directory
   - Utilities: list, delete, filter by session

8. **SettingsUI** (`src/settings_ui.py`) ✅ **NEW** (2025-11-20)
   - GUI settings dialog using tkinter (cross-platform, built-in)
   - `SettingsConfig` - backend configuration management
   - `SettingsDialog` - GUI dialog for user settings
   - Configuration: output directory, opponent tracking, poll rate, auto-update preferences
   - Persistence: saves/loads config.json
   - Validation: ensures settings are valid before saving
   - Command-line integration: `python example_app.py --settings`

9. **Auto-Update System** ✅ **NEW** (2025-11-20)
   - **Version Manager** (`src/version.py`) - Version comparison and validation
   - **Update Checker** (`src/update_checker.py`) - GitHub releases API integration
     - Check for new releases from GitHub
     - Download .exe files with progress reporting
     - SHA256 checksum verification
     - HTTPS-only downloads for security
   - **Update UI** (`src/update_ui.py`) - User interface components
     - `UpdateDialog` - Tkinter dialog for update notifications
     - `UpdateNotification` - System tray balloon notifications
   - **Update Manager** (`src/update_manager.py`) - Orchestration layer
     - Background update checking on startup
     - Handle user responses (install, skip, remind later)
     - Track skipped versions
     - Launch external updater script
   - **External Updater** (`updater.py`) - Standalone script for .exe replacement
     - Waits for app to exit
     - Backs up old .exe
     - Replaces with new .exe
     - Relaunches app
   - **Integration**:
     - `tray_app.py` - Auto-check on startup, "Check for Updates" menu
     - Settings UI checkbox for "Check for updates on startup"
   - **54 comprehensive tests** covering all update components
   - See `AUTO_UPDATE_IMPLEMENTATION_PLAN.md` for complete details

### Integration Example
- `example_app.py` - Complete working application
- Demonstrates all components working together
- Run with: `python example_app.py` (uses saved config)
- Configure settings: `python example_app.py --settings` (shows GUI dialog)

## Testing Requirements

### Running Tests
```bash
# All tests
pytest -v

# Specific module
pytest tests/test_telemetry_loop.py -v

# With coverage
pytest --cov=src --cov-report=html
```

### Test Organization
- Each module has corresponding test file: `test_<module>.py`
- Use pytest fixtures for setup/teardown (see `test_file_manager.py`)
- Mock time-dependent behavior when needed
- Test edge cases and error conditions

### Test Coverage by Module
- `test_telemetry_mock.py` - 7 tests
- `test_process_monitor.py` - 5 tests
- `test_session_manager.py` - 8 tests
- `test_telemetry_loop.py` - 13 tests
- `test_csv_formatter.py` - 6 tests (updated for MVP format)
- `test_sample_normalizer.py` - 5 tests (NEW - MVP format normalization)
- `test_file_manager.py` - 16 tests
- `test_settings_ui.py` - 13 tests (NEW - Settings UI configuration)
- `test_opponent_tracker.py` - 11 tests
- `test_example_app_integration.py` - 4 tests
- `test_telemetry_real.py` - 2 tests
- `test_tray_ui.py` - 15 tests (NEW - System Tray UI)
- `test_version.py` - 11 tests (NEW - Auto-update version management)
- `test_update_checker.py` - 16 tests (NEW - Auto-update GitHub integration)
- `test_update_ui.py` - 12 tests (NEW - Auto-update UI components)
- `test_update_manager.py` - 15 tests (NEW - Auto-update orchestration)
- **Total: 175 tests passing** (including 54 auto-update tests)

## Phase Status

### Phase Progress (Phases 1-6 Complete; Phase 7 In Progress)
- [x] Phase 1: Setup & Cross-Platform Development Foundation
- [x] Phase 2: Core Logger Service Development
- [x] Phase 3: CSV Formatter Implementation (MVP format)
- [x] Phase 4: File Management & Configuration
- [x] Phase 5: System Tray UI & User Controls ✅ **COMPLETE** (2025-11-20)
  - [x] System tray icon and menu ✅ **COMPLETE**
  - [x] Start/Stop/Pause controls via tray ✅ **COMPLETE**
  - [x] Settings/configuration UI ✅ **COMPLETE**
    - [x] Settings dialog with tkinter GUI
    - [x] Output directory, opponent tracking, poll rate configuration
    - [x] Save/Load/Validate config.json
    - [x] Integrated with `example_app.py` and `tray_app.py` (--settings flag)
    - [x] 13 comprehensive tests
  - [x] Status display in tray with tooltips ✅ **COMPLETE**
  - [x] Icon state indicators (gray/yellow/green/orange/red) ✅ **COMPLETE**
  - [x] Open Output Folder menu item ✅ **COMPLETE**
  - [x] Threading integration (telemetry in background, tray in main thread) ✅ **COMPLETE**
  - **Implementation**:
    - `src/tray_ui.py` - TrayUI class with pystray integration
    - `tray_app.py` - New entry point for system tray mode
    - `tests/test_tray_ui.py` - 15 comprehensive tests
    - All Must Have and Nice to Have requirements met
  - **Usage**: `python tray_app.py` or `python tray_app.py --settings`
- [x] Phase 6: Windows Testing & Real Telemetry
  - [x] `RealTelemetryReader` implemented using `pyRfactor2SharedMemory`
  - [x] Tested with live LMU on Windows
  - [x] CSV output validated (MVP format)
  - [x] All 60 tests passing
  - [x] MVP format refactor complete
    - [x] `SampleNormalizer` for data conversion
    - [x] `CSVFormatter` updated to 12-column format
    - [x] Input scaling (0-100% for throttle/brake/steer)

### 🔄 Current Phase: Phase 7 - Distribution
**Status**: Installer implemented, ready for testing and release

Completed:
- [x] PyInstaller build script (`build.bat`)
- [x] Executable created (`LMU_Telemetry_Logger_v1.0/LMU_Telemetry_Logger.exe`)
- [x] User documentation (`USER_GUIDE.md`)
- [x] Windows installer implementation ✅ **NEW** (2025-11-20)
  - [x] Inno Setup installer script (`installer/LMU_Telemetry_Logger_Setup.iss`)
  - [x] Build automation script (`build_installer.bat`)
  - [x] Default configuration template (`installer/config_default.json`)
  - [x] Installer documentation (`installer/README.md`)
  - [x] Updated USER_GUIDE.md with installation instructions
  - [x] Custom output directory selection during installation
  - [x] Upgrade detection with data preservation
  - [x] Uninstall with optional data cleanup
  - [x] Start Menu shortcuts (app, output folder, user guide, uninstall)
  - [x] Optional desktop shortcut and auto-start with Windows
  - [x] Registry integration (Programs & Features)

Remaining:
- [ ] Build and test the installer on Windows
- [ ] Final validation of v1.0 installer
- [ ] Performance optimization (address 43Hz capture rate - currently acceptable)
- [ ] Release preparation (GitHub release, changelog)
- [ ] Optional: Code signing certificate (future enhancement)

## Important Code Patterns

### 1. Platform Detection
```python
from src.telemetry.telemetry_interface import get_telemetry_reader

# Automatically returns correct implementation
reader = get_telemetry_reader()  # Mock on macOS, Real on Windows
```

### 2. Lap Completion Callback
```python
def on_lap_complete(lap_data, lap_summary):
    # lap_data: List[Dict] - all samples
    # lap_summary: Dict - lap time, sectors, etc.
    csv = formatter.format_lap(lap_data, lap_summary, session_info)
    file_manager.save_lap(csv, lap_summary, session_info)

loop = TelemetryLoop({'on_lap_complete': on_lap_complete})
```

### 3. Telemetry Data Structure

**Raw telemetry** (from TelemetryReader) includes 100+ fields - see `telemetry_mock.py` for complete list.

**Normalized telemetry** (after SampleNormalizer) uses canonical MVP field names:
```python
{
    'LapDistance [m]': float,      # Lap distance in meters
    'LapTime [s]': float,           # Lap time in seconds
    'Sector [int]': int,            # Current sector (0-3)
    'Speed [km/h]': float,          # Speed in km/h
    'EngineRevs [rpm]': float,      # Engine RPM
    'ThrottlePercentage [%]': float,  # 0-100%
    'BrakePercentage [%]': float,     # 0-100%
    'Steer [%]': float,               # -100 to +100%
    'Gear [int]': int,              # Current gear
    'X [m]': float,                 # X position (or None)
    'Y [m]': float,                 # Y position (or None)
    'Z [m]': float,                 # Z position (or None)
}
```
See `telemetry_format_analysis.md` for complete MVP format specification.

## Common Commands

### Development
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Windows-specific dependencies (when on Windows)
pip install -r requirements-windows.txt

# Run tests
pytest -v

# Run example app
python example_app.py
```

### Git Workflow
```bash
# Check status
git status

# Run tests before committing
pytest -v

# Commit with tests passing
git add -A
git commit -m "descriptive message"

# Create PR (when ready)
gh pr create --draft
```

### Bug Tracking Workflow

**IMPORTANT**: When fixing bugs listed in the `bugs/` folder, always update the bug file to reflect the resolution.

**When resolving a bug:**
1. **Update the bug file** - Add a status section at the top:
   ```markdown
   ## Status: ✅ RESOLVED

   **Resolved:** YYYY-MM-DD
   **Commit:** <commit-hash>
   **Branch:** <branch-name>

   **Solution:** Brief description of how the bug was fixed.

   ---
   ```

2. **Keep the original description** - Don't delete the bug details; they provide valuable context and history

3. **Commit the bug file updates** - Include bug file updates in the same commit or a follow-up commit

**Example workflow:**
```bash
# 1. Fix the bug
# 2. Run tests
pytest -v

# 3. Get the commit hash
git log --oneline -1

# 4. Update the bug file with status
# 5. Commit both code and bug documentation
git add src/fixed_file.py bugs/bug_description.md
git commit -m "Fix bug: description"
```

**Why this matters:**
- Provides historical record of when and how bugs were fixed
- Helps prevent duplicate work on already-resolved issues
- Makes it easy to see which bugs are still open
- Documents the solution for future reference

## Important Files & References

### Key Files
- `telemetry_format_analysis.md` - **MVP format specification** (LMUTelemetry v2, 12 channels)
- `example.csv` - **Reference CSV output** (MVP format example)
- `MVP_LOGGING_PLAN.md` - MVP format implementation checklist
- `TECHNICAL_SPEC.md` - Detailed component specifications
- `TELEMETRY_LOGGER_PLAN.md` - High-level architecture and plan
- `example_app.py` - Working integration example
- `BUGS.md` - Known issues and performance notes

### Configuration Patterns
```python
# ProcessMonitor
config = {'target_process': 'LMU.exe'}  # or 'python' for testing

# TelemetryLoop
config = {
    'target_process': 'LMU.exe',
    'poll_interval': 0.01,  # 100Hz
    'on_lap_complete': callback_function
}

# FileManager
config = {
    'output_dir': './telemetry_output',
    'filename_format': '{session_id}_lap{lap}.csv'
}
```

## Known Issues & Performance Notes

### Performance Issue: Low Capture Rate (From BUGS.md)
- **Target**: 100Hz (0.01s poll interval)
- **Actual**: ~20Hz observed in testing
- **Impact**: Lower resolution data, may miss fast transients
- **Potential causes**:
  - Shared memory read overhead
  - CSV formatting blocking the loop
  - Windows I/O latency
- **Status**: Open - needs profiling and optimization
- **File**: See `BUGS.md` for full details and tracking

### Windows-Specific Notes

**RealTelemetryReader** (completed):
- Uses `pyRfactor2SharedMemory` library for shared memory access
- Requires LMU to be running for `is_available()` to return True
- Falls back to MockTelemetryReader if library not installed
- Handles unit conversions (Kelvin→Celsius, m/s→km/h, etc.)
- Maps 100+ shared memory fields to telemetry dictionary

**Testing on Windows**:
- Install dependencies: `pip install -r requirements-windows.txt`
- Tests use mocking to avoid requiring live LMU
- Integration testing requires LMU running
- Check `BUGS.md` for known platform-specific issues

## Code Style & Conventions

- **Docstrings**: All functions/classes have Google-style docstrings
- **Type hints**: Use when helpful, especially for function signatures
- **Imports**: Group by stdlib, third-party, local
- **Naming**:
  - snake_case for functions/variables
  - PascalCase for classes
  - UPPER_CASE for constants
- **Line length**: Keep reasonable (~100 chars when possible)

## Troubleshooting

### Tests failing?
1. Check virtual environment is activated
2. Ensure all dependencies installed
3. Read test output carefully - tests are descriptive
4. Run single test file to isolate issue

### Example app not detecting process?
- macOS: Change `target_process` to a running process (e.g., 'python', 'Chrome')
- Windows: Ensure LMU.exe is running

### CSV format doesn't match?
- Compare with `example.csv` line by line (MVP format reference)
- Should have metadata preamble followed by 12-column telemetry data
- Check field names match exactly (e.g., `LapDistance [m]`, not `LapDistance`)
- Verify input percentages are 0-100, not 0-1
- See `telemetry_format_analysis.md` for complete specification

## Next Session Checklist

When continuing development:

1. Pull latest code from git
2. Activate virtual environment (`venv\Scripts\activate`)
3. Run tests to verify everything works (`pytest -v`)
4. Read this file for context
5. Check `BUGS.md` for current known issues
6. Review Phase 7 remaining tasks (see Phase Status above)

## Questions to Ask User

Before making significant changes:
- **Adding new dependencies?** → Ask first
- **Changing test behavior?** → Only if tests can't pass after thorough attempts
- **Modifying core architecture?** → Discuss rationale
- **Platform-specific code?** → Ensure cross-platform compatibility maintained

## Success Criteria

### ✅ Phase 5 (System Tray UI & User Controls) - COMPLETE
- [x] System tray icon displays on Windows/macOS
- [x] Tray menu shows: Start/Stop, Pause/Resume, Open Folder, Quit
- [x] Status indicator in tray (Idle, Detecting, Logging) via tooltips
- [x] Settings dialog for output directory configuration (tkinter GUI)
- [x] Icon state indicators (gray/yellow/green/orange/red)
- [x] Graceful startup and shutdown
- [x] Dynamic menu items based on state
- [x] Cross-platform Open Folder support (Windows/macOS/Linux)
- [x] 15 comprehensive unit tests
- [ ] Balloon notifications for lap completion (not implemented - optional)
- [ ] Auto-start with Windows option (not implemented - optional)

### ✅ Phase 6 (Windows Testing) - COMPLETE
- [x] RealTelemetryReader implemented
- [x] Reads data from LMU shared memory
- [x] Example app works on Windows with live LMU
- [x] CSV files generated match MVP format specification
- [x] All 60 tests passing (with proper mocking for cross-platform)
- [x] MVP format refactor complete

### 🔄 Phase 7 (Distribution) - IN PROGRESS
- [x] PyInstaller builds working .exe
- [x] Basic user documentation (USER_GUIDE.md)
- [ ] .exe final validation and testing
- [ ] Performance optimization (20Hz→100Hz issue)
- [ ] Documentation review and polish
- [ ] Release preparation (version, changelog, etc.)

---

**Remember**: This project follows TDD - write tests first, make them fail, then implement to make them pass. The user values this approach, so maintain it throughout.
