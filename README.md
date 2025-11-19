# LMU Telemetry Logger

A background telemetry logger for Le Mans Ultimate that automatically captures and exports telemetry data to CSV files.

## Project Status

🎉 **v0.2.0 Released** - Opponent Lap Tracking Now Available!

### Latest Release: v0.2.0 (2025-11-20)
- ✅ **NEW**: Opponent lap tracking for multiplayer sessions
- ✅ Fastest lap only per opponent (storage optimized)
- ✅ Configurable: remote players + optional AI tracking
- ✅ Consistent file naming with track, car, driver, lap time
- ✅ 91/91 unit tests passing

### Completed Features
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

### Testing Status
- ⏳ Windows multiplayer testing pending (you can help!)

## 🚀 Quick Start (Windows)

### Download & Build v0.2.0

1. **Download**: Get the latest release from [GitHub Releases](https://github.com/davedean/eztel-writer/releases/tag/v0.2.0)

2. **Build**: Follow [WINDOWS_BUILD_INSTRUCTIONS.md](WINDOWS_BUILD_INSTRUCTIONS.md) for step-by-step guide

3. **Quick Build**:
   ```cmd
   git clone --branch v0.2.0 https://github.com/davedean/eztel-writer.git
   cd eztel-writer
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt -r requirements-windows.txt
   pip install pyinstaller
   build.bat
   ```

4. **Run**: `dist\LMU_Telemetry_Logger.exe`

5. **Test**: Join a multiplayer session in LMU and complete laps!

**Output Location**: `./telemetry_output/*.csv`

## Features (Planned)

- 🎯 **Zero-Config** - Single `.exe` file, no installation required
- 🔄 **Auto-Detection** - Automatically starts/stops with LMU
- 🖥️ **Background Service** - Runs silently in system tray
- 📊 **CSV Export** - Emits LMUTelemetry v2 (metadata + 12 channels)
- 🍎 **Cross-Platform Dev** - Develop on macOS, deploy on Windows

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
