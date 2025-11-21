# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-11-20

### Added

#### System Tray UI (Phase 5 Complete)
- **System tray icon** with visual state indicators:
  - Gray: Idle (waiting for LMU)
  - Yellow: Process detected (LMU running, waiting for session)
  - Green: Logging (actively capturing telemetry)
  - Orange: Paused (session paused)
  - Red: Error state
- **Tray menu controls**:
  - Start/Stop logging
  - Pause/Resume session
  - Open Output Folder (cross-platform support)
  - Settings dialog
  - Check for Updates
  - Quit application
- **Status tooltips** showing current state and session info
- **Threading integration** for background telemetry capture
- **15 comprehensive unit tests**
- New entry point: `tray_app.py`

#### Settings UI (Phase 5 Complete)
- **GUI settings dialog** using tkinter (cross-platform)
- **Configuration options**:
  - Output directory path
  - Opponent tracking (enable/disable)
  - Track opponent AI (enable/disable)
  - Poll rate (Hz)
  - Auto-update preferences (check on startup, skipped versions)
- **Persistent configuration** saved to `config.json`
- **Settings validation** ensures valid values before saving
- **Command-line integration**: `python tray_app.py --settings`
- **13 comprehensive unit tests**
- Backend: `SettingsConfig` class
- Frontend: `SettingsDialog` class

#### Auto-Update System (Phases 6-7 Complete)
- **Version Manager** (`src/version.py`):
  - Semantic versioning support (MAJOR.MINOR.PATCH)
  - Version comparison and validation
  - 11 unit tests
- **Update Checker** (`src/update_checker.py`):
  - GitHub releases API integration
  - Download .exe files with progress reporting
  - SHA256 checksum verification for security
  - HTTPS-only downloads
  - 16 unit tests
- **Update UI** (`src/update_ui.py`):
  - Tkinter dialog for update notifications
  - System tray balloon notifications
  - 12 unit tests
- **Update Manager** (`src/update_manager.py`):
  - Background update checking on startup
  - Handle user responses (install, skip, remind later)
  - Track skipped versions
  - Launch external updater script
  - 15 unit tests
- **External Updater** (`updater.py`):
  - Standalone script for .exe replacement
  - Waits for app to exit
  - Backs up old .exe
  - Replaces with new .exe and relaunches app
- **Tray Integration**:
  - Auto-check on startup (configurable)
  - "Check for Updates" menu item
- **Total: 54 auto-update tests**

#### Windows Installer (Phase 7 Complete)
- **Inno Setup installer** (`installer/LMU_Telemetry_Logger_Setup.iss`)
- **Build automation** script (`build_installer.bat`)
- **Installation features**:
  - Custom output directory selection
  - Upgrade detection with data preservation
  - Uninstall with optional data cleanup
  - Start Menu shortcuts (app, output folder, user guide, uninstall)
  - Optional desktop shortcut
  - Optional auto-start with Windows
  - Registry integration (Programs & Features)
- **Default configuration** template included
- **Comprehensive documentation** (`installer/README.md`)

### Fixed
- **Terminal window visibility bug**: Console window now properly hidden in production builds
- **Opponent lap tracking bugs**:
  - Prevent duplicate lap captures
  - Fix partial lap detection to avoid incomplete data
  - Updated tests to validate fixes
- **Filename format inconsistencies**: Player and opponent laps now use consistent naming format

### Changed
- **Bug tracking workflow**: Added status updates to bug files when resolved
- **Cleaned up bugs/ folder**: Removed 14 resolved bug files to reduce clutter
- **Documentation improvements**: Updated USER_GUIDE.md with installation instructions
- **Test coverage**: Increased from 121 to **175 tests passing** (100% coverage of implemented modules)

### Developer Notes
- All 175 tests passing (including 54 auto-update tests)
- Cross-platform development maintained (develop on macOS, test on Windows)
- TDD approach continued throughout Phase 5-7 implementations
- Complete Phase 5, 6, and 7 implementation

## [0.2.0] - 2025-11-20

### Added
- **Opponent Lap Tracking** for multiplayer sessions
  - Automatically captures telemetry from other drivers
  - "Fastest lap only" strategy to control storage (Option 2)
  - Filters by control type (remote players vs AI)
  - Configuration options: `track_opponents`, `track_opponent_ai`
  - OpponentTracker class with 11 unit tests
  - TelemetryReaderInterface.get_all_vehicles() for accessing opponent data
  - Mock and Real implementations for cross-platform development
  - Consistent file naming with player laps: `{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv`

### Changed
- Reorganized `BUGS.md` into `bugs/` folder with separate files:
  - `bugs/capture_opponent_laps.md` - Opponent tracking documentation
  - `bugs/performance_notes.md` - Performance analysis
  - `bugs/future_enhancements.md` - Future feature ideas
  - `bugs/data_quality.md` - Data quality issues and fixes

### Fixed
- Opponent lap filenames now use same format as player laps (includes track and car)

## [0.1.6] - Previous Releases

See git history for earlier changes.
