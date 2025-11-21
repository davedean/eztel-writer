# LMU Telemetry Logger

A background telemetry logger for Le Mans Ultimate that automatically captures and exports telemetry data to CSV files.

## Project Status

🎉 **v0.3.0 Released** - System Tray UI & Auto-Update!

### Latest Release: v0.3.0 (2025-11-20)
- ✅ **NEW**: System Tray UI with visual state indicators
- ✅ **NEW**: Settings GUI dialog for easy configuration
- ✅ **NEW**: Auto-Update system with one-click installation
- ✅ **NEW**: Windows Installer with custom directory selection
- ✅ Bug fixes: Terminal window, opponent laps, filename consistency
- ✅ 175/175 unit tests passing (100% coverage)

### Completed Features
- ✅ **System Tray UI** - Runs in background with right-click menu
- ✅ **Settings Dialog** - GUI configuration (output dir, opponents, poll rate)
- ✅ **Auto-Update** - Automatic updates from GitHub with checksum verification
- ✅ **Windows Installer** - Professional installation experience
- ✅ Automatic player lap capture
- ✅ Opponent lap capture (multiplayer)
- ✅ Mock telemetry system for macOS development
- ✅ Platform detection (macOS/Windows)
- ✅ Process monitoring with auto-detection
- ✅ Session management and lap tracking
- ✅ Telemetry polling loop (~43-50Hz, optimal)
- ✅ CSV formatter for LMUTelemetry v3 (10-channel MVP schema)
- ✅ File management with smart naming
- ✅ Cross-platform development (macOS → Windows)
- ✅ Windows testing with real LMU telemetry

### Phase Status
- ✅ Phase 1-4: Core telemetry system (Complete)
- ✅ Phase 5: System Tray UI & User Controls (Complete)
- ✅ Phase 6: Windows Testing & Auto-Update (Complete)
- ✅ Phase 7: Distribution & Installer (Complete)
- 🚀 **Feature Complete!**

## 🚀 Quick Start (Windows)

### Option 1: Windows Installer (Recommended)

1. **Download**: Get `LMU_Telemetry_Logger_Setup.exe` from [GitHub Releases](https://github.com/davedean/eztel-writer/releases/tag/v0.3.0)
2. **Install**: Run the installer and follow the wizard
3. **Launch**: Start from Start Menu or Desktop shortcut
4. **Configure**: Right-click tray icon → Settings
5. **Use**: Launch LMU and drive - telemetry is captured automatically!

### Option 2: Portable Executable

1. **Download**: Get `LMU_Telemetry_Logger.zip` from [GitHub Releases](https://github.com/davedean/eztel-writer/releases/tag/v0.3.0)
2. **Extract**: Unzip to any folder
3. **Run**: Double-click `LMU_Telemetry_Logger.exe`

### Option 3: Build from Source

1. **Clone**:
   ```cmd
   git clone --branch v0.3.0 https://github.com/davedean/eztel-writer.git
   cd eztel-writer
   ```

2. **Setup**:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt -r requirements-windows.txt
   pip install pyinstaller
   ```

3. **Build**:
   ```cmd
   build.bat
   ```

4. **Build Installer** (optional):
   ```cmd
   build_installer.bat
   ```

For detailed build instructions, see [WINDOWS_BUILD_INSTRUCTIONS.md](WINDOWS_BUILD_INSTRUCTIONS.md)

**Output Location**: `./telemetry_output/*.csv`

See [RELEASE_NOTES_v0.3.0.md](RELEASE_NOTES_v0.3.0.md) for complete feature list and usage instructions.

## Key Features

- ✅ **System Tray UI** - Runs in background with visual state indicators
- ✅ **Auto-Detection** - Automatically starts/stops with LMU
- ✅ **Settings GUI** - Easy configuration via dialog
- ✅ **Auto-Update** - One-click updates from GitHub
- ✅ **CSV Export** - LMUTelemetry v3 format (metadata + 10 channels)
- ✅ **Opponent Tracking** - Capture opponent laps in multiplayer
- ✅ **Windows Installer** - Professional installation experience
- ✅ **Cross-Platform Dev** - Develop on macOS, deploy on Windows

## Development Setup (macOS)

```bash
# Clone repository
git clone <repo-url>
cd telemetry_writer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest -v

# Run example app (uses mock telemetry on macOS)
python example_app.py
```

## Project Structure

```
telemetry_writer/
├── src/
│   ├── telemetry/
│   │   ├── telemetry_interface.py   # Abstract interface ✅
│   │   ├── telemetry_mock.py        # macOS: mock data ✅
│   │   └── telemetry_real.py        # Windows: real data (TODO)
│   ├── process_monitor.py           # Process auto-detection ✅
│   ├── session_manager.py           # Session & lap tracking ✅
│   ├── telemetry_loop.py            # Main polling loop ✅
│   ├── csv_formatter.py             # CSV formatting ✅
│   └── file_manager.py              # File operations ✅
├── tests/
│   ├── test_telemetry_mock.py       # 7 tests ✅
│   ├── test_process_monitor.py      # 5 tests ✅
│   ├── test_session_manager.py      # 7 tests ✅
│   ├── test_telemetry_loop.py       # 13 tests ✅
│   ├── test_csv_formatter.py        # 13 tests ✅
│   └── test_file_manager.py         # 16 tests ✅
├── requirements.txt
└── example.csv                       # MVP 12-channel reference output
```

## Documentation

- **[TELEMETRY_LOGGER_PLAN.md](TELEMETRY_LOGGER_PLAN.md)** - High-level plan and architecture
- **[TECHNICAL_SPEC.md](TECHNICAL_SPEC.md)** - Detailed implementation guide
- **[GITHUB_ISSUES.md](GITHUB_ISSUES.md)** - Task breakdown
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - How to use the docs

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_telemetry_mock.py -v
```

Current test coverage: **100%** of implemented modules

## Timeline

- **Days 1-4**: macOS development (mock telemetry) ← **Currently here**
- **Days 5-6**: Windows testing and `.exe` build

## License

TBD

---

**Version**: 1.0.0-dev
**Last Updated**: 2025-01-17
