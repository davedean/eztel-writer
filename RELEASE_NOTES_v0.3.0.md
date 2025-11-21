# Release Notes - v0.3.0: System Tray UI & Auto-Update

**Release Date**: 2025-11-20
**Version**: 0.3.0
**Status**: 🚀 **Feature Complete - System Tray & Auto-Update**

---

## 🎉 What's New in v0.3.0

Version 0.3.0 brings a complete system tray interface, automatic updates, professional Windows installer, and numerous bug fixes since v0.2.0.

---

## 🚀 Major Features

### 1. System Tray UI (Phase 5 Complete)

The telemetry logger now runs seamlessly in your system tray with a beautiful, intuitive interface!

**Features**:
- ✅ **Visual State Indicators**: Icon color shows current status at a glance
  - 🔘 Gray: Idle (waiting for LMU to start)
  - 🟡 Yellow: Process detected (LMU running, waiting for session)
  - 🟢 Green: Logging (actively capturing telemetry)
  - 🟠 Orange: Paused
  - 🔴 Red: Error state

- ✅ **Right-Click Menu Controls**:
  - Start/Stop logging
  - Pause/Resume session
  - Open Output Folder (opens your telemetry files)
  - Settings (configure app preferences)
  - Check for Updates
  - Quit

- ✅ **Hover Tooltips**: See current state, session info, and lap count without opening menus

- ✅ **Background Operation**: Telemetry runs in background thread, UI stays responsive

- ✅ **New Entry Point**: Run `LMU_Telemetry_Logger.exe` for tray mode (recommended)

---

### 2. Settings UI (Phase 5 Complete)

Configure the application through a user-friendly GUI dialog!

**Configuration Options**:
- ✅ **Output Directory**: Choose where CSV files are saved
- ✅ **Opponent Tracking**: Enable/disable opponent lap capture
- ✅ **Track Opponent AI**: Include or exclude AI drivers
- ✅ **Poll Rate**: Adjust telemetry sampling frequency (Hz)
- ✅ **Auto-Update Preferences**: Control update checking behavior

**How to Access**:
- System Tray → Right-click → Settings
- Command line: `LMU_Telemetry_Logger.exe --settings`

**Persistence**: All settings are saved to `config.json` and loaded automatically on startup

---

### 3. Auto-Update System (Phases 6-7 Complete)

Never manually download releases again! The app now updates itself automatically.

**Features**:
- ✅ **Automatic Update Checking**: Checks GitHub for new releases on startup (configurable)
- ✅ **One-Click Updates**: Download and install updates with a single click
- ✅ **Security**: SHA256 checksum verification ensures download integrity
- ✅ **Smart Notifications**:
  - System tray notifications when updates are available
  - Dialog with release notes and options (Install Now, Skip This Version, Remind Later)
- ✅ **Seamless Installation**: Automatically backs up old version, installs new version, and relaunches app
- ✅ **Manual Check**: System Tray → Check for Updates

**How It Works**:
1. App checks GitHub releases API on startup
2. If newer version found, shows notification
3. Click "Install Now" to download update
4. App downloads .exe file and verifies checksum
5. External updater script replaces old .exe
6. App relaunches automatically with new version

**Settings Control**:
- Enable/disable automatic checking on startup
- View and manage skipped versions

---

### 4. Windows Installer (Phase 7 Complete)

Professional installation experience with custom output directory selection!

**Installer Features**:
- ✅ **Custom Output Directory**: Choose where telemetry files are saved during installation
- ✅ **Upgrade Detection**: Preserves your settings and data when upgrading
- ✅ **Uninstall Options**: Choose to keep or delete telemetry data when uninstalling
- ✅ **Start Menu Shortcuts**:
  - Launch LMU Telemetry Logger
  - Open Output Folder
  - User Guide
  - Uninstall
- ✅ **Optional Features**:
  - Desktop shortcut
  - Auto-start with Windows
- ✅ **Registry Integration**: Appears in Windows "Programs & Features"

**Installation Instructions**:
1. Download `LMU_Telemetry_Logger_Setup.exe` from GitHub releases
2. Run the installer
3. Choose installation directory
4. Choose output directory for telemetry files
5. Select optional features (desktop shortcut, auto-start)
6. Click Install

**Upgrade Instructions**:
1. Download new installer version
2. Run installer (detects existing installation automatically)
3. Settings and telemetry data are preserved
4. Old version is automatically replaced

---

## 🐛 Bug Fixes

### Terminal Window Visibility (Critical Fix)
- **Issue**: Console window appeared alongside tray icon in production builds
- **Fixed**: Console window now properly hidden in `--noconsole` builds
- **Impact**: Professional appearance, no more terminal windows cluttering your screen

### Opponent Lap Tracking Improvements
- **Fixed duplicate lap captures**: Prevents saving the same opponent lap multiple times
- **Fixed partial lap detection**: Only captures complete laps with valid data
- **Improved lap validation**: Better detection of lap start/end boundaries
- **Test coverage**: Added comprehensive tests to prevent regression

### Filename Format Consistency
- **Issue**: Player and opponent lap filenames used different formats
- **Fixed**: Standardized filename format across all lap types
- **Format**: `{date}_{time}_{track}_{car}_{driver}_lap{lap}_t{lap_time}s.csv`
- **Example**: `2025-11-20_14-30_bahrain-international-circuit_toyota-gr010_dean-davids_lap3_t125.234s.csv`

---

## 📊 Test Coverage

- **Total Tests**: 175 (all passing ✅)
- **New Tests Added**: 54 (auto-update system)
- **Coverage**: 100% of implemented modules
- **Test Files**: 20 test modules
- **TDD Approach**: All features developed test-first

**Test Breakdown by Module**:
- Auto-Update System: 54 tests
  - Version Manager: 11 tests
  - Update Checker: 16 tests
  - Update UI: 12 tests
  - Update Manager: 15 tests
- System Tray UI: 15 tests
- Settings UI: 13 tests
- Core Telemetry: 93 tests (existing)

---

## 📦 Installation & Usage

### Windows Users (Recommended)

#### Option 1: Installer (Easiest)
1. Download `LMU_Telemetry_Logger_Setup.exe` from [GitHub Releases](https://github.com/davedean/eztel-writer/releases)
2. Run the installer
3. Choose installation and output directories
4. Launch from Start Menu or Desktop
5. App runs in system tray, automatically starts logging when LMU launches

#### Option 2: Portable Executable
1. Download `LMU_Telemetry_Logger.zip` from [GitHub Releases](https://github.com/davedean/eztel-writer/releases)
2. Extract to any folder
3. Run `LMU_Telemetry_Logger.exe`
4. Configure settings via tray menu

#### Prerequisites (Important!)
Before first use, install LMU runtime dependencies:
1. Navigate to: `C:\Program Files (x86)\Steam\steamapps\common\Le Mans Ultimate\support\runtimes\`
2. Install `vc_redist.x64.exe` (Visual C++ Redistributable) - **Required!**
3. Restart your computer

**Note**: If you've already run LMU successfully, these are already installed.

---

### Developers (macOS/Linux)

```bash
# Clone repository
git clone https://github.com/davedean/eztel-writer.git
cd eztel-writer

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Windows-specific dependencies (when on Windows)
pip install -r requirements-windows.txt

# Run tests
pytest -v

# Run tray app
python tray_app.py

# Run with settings dialog
python tray_app.py --settings
```

---

## 🎯 How to Use

### First Launch
1. Start `LMU_Telemetry_Logger.exe` (it minimizes to system tray)
2. Right-click tray icon → Settings
3. Configure output directory and preferences
4. Click Save

### During Racing
1. Launch Le Mans Ultimate
2. Logger automatically detects LMU (icon turns yellow)
3. Start a session (icon turns green)
4. Drive laps - telemetry is captured automatically
5. CSV files saved to output directory after each lap

### Managing Files
- Right-click tray icon → Open Output Folder
- Files organized by session, lap, and driver
- Import CSV into your favorite analysis tool

### Updating
- Automatic check on startup (configurable)
- Manual check: Right-click → Check for Updates
- One-click installation when updates available

---

## 📋 Configuration File

Settings are stored in `config.json` (auto-created on first run):

```json
{
  "output_dir": "C:\\Users\\YourName\\Documents\\LMU_Telemetry",
  "target_process": "LMU.exe",
  "poll_interval": 0.01,
  "track_opponents": true,
  "track_opponent_ai": false,
  "check_updates_on_startup": true,
  "skipped_versions": []
}
```

You can edit this file manually or use the Settings dialog (recommended).

---

## 🔄 What Changed from v0.2.0

If you're upgrading from v0.2.0 (Opponent Lap Tracking release):

**New Features**:
- System Tray UI (completely new interface)
- Settings GUI (no more manual config editing)
- Auto-Update system (automatic updates from GitHub)
- Windows Installer (professional installation experience)

**Improvements**:
- 54 new tests (auto-update coverage)
- Bug fixes (terminal window, opponent laps, filenames)
- Better documentation

**Breaking Changes**:
- None! Your existing `config.json` and telemetry files work as-is

---

## 🐛 Known Issues

### Performance Notes
- **Capture Rate**: Currently achieving ~43Hz (target: 100Hz)
- **Impact**: Slightly lower resolution data, but sufficient for most analysis
- **Status**: Acceptable for v0.3.0, optimization planned for future release
- **Workaround**: None needed, data quality is good

### Platform Support
- **Windows**: Full support, tested with live LMU
- **macOS/Linux**: Development/testing only (uses mock telemetry, LMU not available)

---

## 🔮 What's Next (v1.1.0)

Planned features for next release:
- Performance optimization (improve capture rate 43Hz → 100Hz)
- Advanced opponent filtering (position-based, lap validity checks)
- Storage usage monitoring and cleanup tools
- Enhanced notifications (lap completion, session end)
- Optional code signing for installer

---

## 📚 Documentation

- **User Guide**: See `USER_GUIDE.md` for detailed usage instructions
- **Technical Spec**: See `TECHNICAL_SPEC.md` for architecture details
- **Changelog**: See `CHANGELOG.md` for complete version history
- **Auto-Update Plan**: See `AUTO_UPDATE_IMPLEMENTATION_PLAN.md` for technical details

---

## 🙏 Acknowledgments

This release represents the completion of Phases 5, 6, and 7 of the LMU Telemetry Logger roadmap. Special thanks to all contributors and testers!

---

## 📞 Support

**Questions or Issues?**
- GitHub Issues: https://github.com/davedean/eztel-writer/issues
- Documentation: See `USER_GUIDE.md` in installation folder

**Reporting Bugs**:
Please include:
1. Version number (check tray tooltip or About dialog)
2. Windows version
3. Steps to reproduce
4. Expected vs actual behavior
5. Log files if available

---

**Enjoy v0.3.0! Happy racing! 🏁**
