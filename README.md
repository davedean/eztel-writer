# LMU Telemetry Logger

A background telemetry logger for Le Mans Ultimate that automatically captures and exports telemetry data to CSV files.

## Project Status

🚧 **In Development** - Phases 1-4 Complete (Core System Implemented)

### Completed
- ✅ Project structure setup
- ✅ Mock telemetry system for macOS development
- ✅ Platform detection (macOS/Windows)
- ✅ Process monitoring with auto-detection
- ✅ Session management and lap tracking
- ✅ Telemetry polling loop (~100Hz)
- ✅ CSV formatter matching reference format
- ✅ File management for saving lap data
- ✅ 61/61 unit tests passing

### In Progress
- 🔄 Phase 5: Integration testing and example app

## Features (Planned)

- 🎯 **Zero-Config** - Single `.exe` file, no installation required
- 🔄 **Auto-Detection** - Automatically starts/stops with LMU
- 🖥️ **Background Service** - Runs silently in system tray
- 📊 **CSV Export** - Matches standard telemetry format
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
└── example.csv                       # Reference output format
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
