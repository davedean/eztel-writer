# 1Lap - Installer

This directory contains the files needed to build a Windows installer for the 1Lap.

## Overview

The installer uses **Inno Setup**, a free and professional Windows installer creation tool. It packages the PyInstaller executable, creates shortcuts, sets up directories, and provides a proper Windows installation experience.

## Prerequisites

### Required Software

1. **Python 3.8+** with all project dependencies
   - Install dependencies: `pip install -r requirements.txt requirements-dev.txt requirements-windows.txt`

2. **PyInstaller** (for building the executable)
   - Should be installed via `requirements-dev.txt`
   - Verify: `pyinstaller --version`

3. **Inno Setup 6** (for building the installer)
   - Download: https://jrsoftware.org/isdl.php
   - Install to default location: `C:\Program Files (x86)\Inno Setup 6\`
   - Free download, ~2 MB installer

### System Requirements

- **Operating System**: Windows 10 or Windows 11
- **Disk Space**: ~500 MB free (for build process and outputs)
- **RAM**: 4 GB minimum

## Quick Start

### Option 1: Build Everything (Recommended)

This builds both the PyInstaller executable AND the installer:

```batch
build_installer.bat
```

This will:
1. Run PyInstaller to create `dist\1Lap\`
2. Verify the executable was created
3. Run Inno Setup to create the installer
4. Output: `installer\output\1Lap_Setup_v1.0.0.exe`

### Option 2: Build Only Executable

If you just want to rebuild the executable without creating an installer:

```batch
build_installer.bat --exe-only
```

Or use the original build script:

```batch
build.bat
```

### Option 3: Build Only Installer

If you already have a built executable and just want to rebuild the installer:

```batch
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\1Lap_Setup.iss
```

## File Structure

```
installer/
├── README.md                           # This file
├── 1Lap_Setup.iss      # Inno Setup script (main installer configuration)
├── config_default.json                 # Default configuration template
└── output/                             # Generated installers output here (gitignored)
    └── 1Lap_Setup_v1.0.0.exe
```

## Configuration Files

### 1Lap_Setup.iss

This is the main Inno Setup script that defines:
- Installation directory (default: `C:\Program Files\1Lap`)
- Files to include (executable, docs, config)
- Shortcuts to create (Start Menu, optional Desktop)
- Registry entries for Windows integration
- Custom installation pages (output directory selection)
- Upgrade detection logic
- Uninstall behavior

**Key Settings:**
- `AppVersion`: Change this when releasing new versions (currently `1.0.0`)
- `OutputBaseFilename`: Controls the installer filename
- `Compression`: LZMA2 ultra64 for smallest file size

### config_default.json

Default configuration file installed with the application. Contains:
- `output_dir`: Where telemetry files are saved
- `target_process`: Process name to monitor (LMU.exe)
- `poll_interval`: Telemetry polling rate (0.01 = 100Hz)
- `track_opponents`: Whether to track opponent telemetry
- `track_opponent_ai`: Whether to track AI opponents

During installation, the user can customize the output directory, and the installer will update this config file accordingly.

## Installation Features

### What the Installer Does

**Files:**
- Installs executable to `C:\Program Files\1Lap\`
- Creates default output directory in `Documents\1Lap Telemetry`
- Installs `USER_GUIDE.md` for user reference
- Creates `config.json` (preserves existing on upgrade)

**Shortcuts:**
- Start Menu folder with:
  - Launch application shortcut
  - Open Output Folder shortcut
  - User Guide shortcut
  - Uninstall shortcut
- Optional Desktop shortcut

**Registry:**
- Adds to "Programs and Features" for proper Windows integration
- Stores installation path and version for upgrade detection
- Optionally adds to Windows startup (if user selects)

**Custom Options:**
- User can choose telemetry output directory during installation
- Optional desktop shortcut (unchecked by default)
- Optional auto-start with Windows (unchecked by default)

### Upgrade Behavior

When a user runs a newer installer over an existing installation:
- Detects existing installation via registry
- Shows "Upgrade" messaging instead of "Install"
- **Preserves user's config.json** (doesn't overwrite)
- **Preserves existing telemetry data** (never deleted on upgrade)
- Updates executable to new version
- Updates version in registry

### Uninstall Behavior

When a user uninstalls:
- Removes all installed files from Program Files
- Removes Start Menu shortcuts
- Removes Desktop shortcut (if it was created)
- Removes registry entries
- **Prompts user** about keeping telemetry data and config
  - If YES: Deletes telemetry data and config
  - If NO: Preserves telemetry data and config for future installations

## Building the Installer

### Step-by-Step Process

1. **Build the PyInstaller executable first:**
   ```batch
   build.bat
   ```
   This creates: `dist\1Lap\1Lap.exe`

2. **Verify the executable works:**
   ```batch
   dist\1Lap\1Lap.exe --help
   ```

3. **Build the installer:**
   ```batch
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\1Lap_Setup.iss
   ```

4. **Find the installer:**
   - Location: `installer\output\1Lap_Setup_v1.0.0.exe`
   - Size: ~8-10 MB (compressed)

### Automated Build

For convenience, use the automated build script:

```batch
build_installer.bat
```

This runs all steps automatically and verifies everything.

## Testing the Installer

### Basic Testing

1. **Fresh Installation:**
   ```batch
   installer\output\1Lap_Setup_v1.0.0.exe
   ```
   - Follow the wizard
   - Verify shortcuts created
   - Launch app from Start Menu
   - Verify app runs correctly

2. **Upgrade Installation:**
   - Modify `config.json` with custom settings
   - Generate some telemetry files
   - Run a newer installer
   - Verify config and data preserved

3. **Uninstall:**
   - Open Windows Settings → Apps → 1Lap → Uninstall
   - Test both "keep data" and "delete data" options
   - Verify clean removal

### Silent Installation (for testing)

```batch
# Silent install to default location
1Lap_Setup_v1.0.0.exe /SILENT

# Silent install to custom location
1Lap_Setup_v1.0.0.exe /SILENT /DIR="C:\CustomPath"

# Very silent (no UI at all)
1Lap_Setup_v1.0.0.exe /VERYSILENT /DIR="C:\CustomPath"

# Silent uninstall
"C:\Program Files\1Lap\unins000.exe" /SILENT
```

## Customizing the Installer

### Changing the Version

Edit `1Lap_Setup.iss`:

```pascal
#define MyAppVersion "1.1.0"  ; Change this line
```

This updates:
- Installer filename: `1Lap_Setup_v1.1.0.exe`
- Version in Windows "Programs and Features"
- Version stored in registry

### Adding/Removing Files

Edit the `[Files]` section in `1Lap_Setup.iss`:

```pascal
[Files]
Source: "..\dist\1Lap\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "..\USER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
; Add more files here
```

### Changing Default Settings

Edit `config_default.json` to change the defaults installed with the app.

### Adding a License File

1. Create `LICENSE` file in project root
2. Uncomment in `1Lap_Setup.iss`:
   ```pascal
   LicenseFile=..\LICENSE
   ```
   and
   ```pascal
   Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
   ```

## Troubleshooting

### Error: "PyInstaller executable not found"

**Problem:** `dist\1Lap\1Lap.exe` doesn't exist

**Solution:**
```batch
build.bat
```

### Error: "Inno Setup not found"

**Problem:** ISCC.exe not in expected location

**Solution:**
1. Install Inno Setup from https://jrsoftware.org/isdl.php
2. Verify installation path matches script
3. Or set path manually:
   ```batch
   "C:\Path\To\ISCC.exe" installer\1Lap_Setup.iss
   ```

### Error: "Error opening file for reading"

**Problem:** Script can't find a source file (USER_GUIDE.md, executable, etc.)

**Solution:**
- Verify all referenced files exist
- Check paths in `.iss` script (relative to `installer/` directory)
- Ensure PyInstaller build completed successfully

### Installer is too large (>20 MB)

**Problem:** Installer file size is unexpectedly large

**Solution:**
- Check PyInstaller bundle size: `dir dist\1Lap`
- Verify no unnecessary files included
- Compression setting: Ensure using `lzma2/ultra64`

### Antivirus False Positive

**Problem:** Windows Defender flags installer as potentially harmful

**Solution:**
- This is normal for unsigned installers
- User must click "More info" → "Run anyway"
- Future: Get code signing certificate to eliminate warnings (~$100-300/year)

## Distribution

Once the installer is built and tested:

1. **Upload to GitHub Releases:**
   ```bash
   gh release create v1.0.0 installer\output\1Lap_Setup_v1.0.0.exe
   ```

2. **Generate SHA256 checksum** (for security):
   ```batch
   certutil -hashfile installer\output\1Lap_Setup_v1.0.0.exe SHA256
   ```

3. **Create release notes:**
   - List new features
   - List bug fixes
   - Include installation instructions
   - Include SHA256 checksum

4. **Test on clean system:**
   - Preferably a fresh Windows 10/11 VM
   - Verify installation works without development tools

## Advanced: Code Signing (Future)

**Current Status:** Installer is not code-signed

**Impact:**
- Windows SmartScreen shows warning
- Users must click "More info" → "Run anyway"
- This is normal for open-source software

**Future Enhancement:**
1. Purchase code signing certificate (~$100-300/year)
   - Providers: DigiCert, Sectigo, etc.
   - EV certificate preferred (instant reputation)
2. Sign installer with `signtool.exe`
3. No more SmartScreen warnings

**Signing command** (when certificate available):
```batch
signtool sign /f "certificate.pfx" /p "password" /t http://timestamp.digicert.com installer\output\1Lap_Setup_v1.0.0.exe
```

## Version History

- **v1.0.0** (2025-11-20)
  - Initial installer implementation
  - Inno Setup 6 script
  - Custom output directory selection
  - Upgrade detection and data preservation
  - Optional desktop shortcut and auto-start

## Resources

- **Inno Setup Documentation:** https://jrsoftware.org/ishelp/
- **Inno Setup Examples:** `C:\Program Files (x86)\Inno Setup 6\Examples\`
- **Pascal Scripting Reference:** https://jrsoftware.org/ishelp/index.php?topic=scriptintro
- **Project Repository:** https://github.com/davedean/eztel-writer

## Support

For installer-related issues:
1. Check this README's Troubleshooting section
2. Review Inno Setup compiler output for specific errors
3. Open an issue on GitHub with:
   - Installer version
   - Windows version
   - Error message or unexpected behavior
   - Steps to reproduce
