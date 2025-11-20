# Feature: Windows Installer

**Status**: 🔄 Planned
**Priority**: High
**Category**: Distribution
**Related Phase**: Phase 7 (Distribution)

---

## Description

Create a professional Windows installer for the LMU Telemetry Logger that packages the executable, sets up directories, creates shortcuts, and provides a proper installation/uninstallation experience.

**Current**: Users must manually extract the .exe and create their own shortcuts
**Desired**: Users run an installer that sets everything up automatically with a familiar Windows installation wizard

## User Story

As a user, I want a professional installer so that:
- I can install the app like any other Windows application
- The app is added to my Start Menu and (optionally) Desktop
- Default directories are set up automatically
- I can easily uninstall the app through Windows Settings
- The app can optionally start with Windows
- I don't need to manually configure file paths or permissions

## Requirements

### Must Have

1. **Installation Wizard**
   - Welcome screen with app name and version
   - License agreement (MIT license display)
   - Installation directory selection (default: `C:\Program Files\LMU Telemetry Logger`)
   - Progress bar during installation
   - Completion screen with "Launch application" checkbox

2. **File Installation**
   - Copy `LMU_Telemetry_Logger.exe` to installation directory
   - Create default output directory: `%USERPROFILE%\Documents\LMU Telemetry`
   - Install default `config.json` with sensible defaults
   - Include `USER_GUIDE.md` in installation directory

3. **Shortcuts**
   - Start Menu entry: `LMU Telemetry Logger`
   - Start Menu folder with:
     - Launch application shortcut
     - Open Output Folder shortcut
     - Uninstall shortcut
     - User Guide shortcut (opens .md file)

4. **Registry Entries**
   - Add to Windows "Programs and Features" (Add/Remove Programs)
   - Store installation path in registry
   - Store version number for upgrade detection

5. **Uninstaller**
   - Remove all installed files
   - Remove Start Menu shortcuts
   - Remove registry entries
   - Ask user if they want to keep telemetry data and config
   - Clean uninstall leaves no artifacts

### Nice to Have

1. **Desktop Shortcut** (Optional)
   - Checkbox during installation: "Create Desktop shortcut"
   - Only create if user opts in

2. **Auto-Start Option** (Optional)
   - Checkbox during installation: "Start with Windows"
   - Add to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` if enabled
   - Can be toggled later in Settings UI

3. **Upgrade Detection**
   - Detect existing installation
   - Show "Upgrade" vs "Install" messaging
   - Preserve user's config.json during upgrade
   - Preserve existing telemetry data

4. **Custom Output Directory**
   - Let user choose telemetry output directory during installation
   - Pre-populate config.json with their choice

5. **Prerequisites Check**
   - Check for required Windows version (Windows 10+)
   - Check for disk space (~50 MB for app + space for telemetry)

6. **Digital Signature** (Future)
   - Sign installer with code signing certificate
   - Eliminates Windows SmartScreen warnings

## Technical Implementation

### Installer Technology

**Recommended: Inno Setup**
- Free and open-source
- Industry standard for Windows installers
- Script-based (easy to version control)
- Supports all required features
- Creates single .exe installer
- Small installer size
- Well-documented

**Alternatives Considered:**
- **NSIS**: Similar to Inno Setup, slightly more complex scripting
- **WiX Toolset**: Creates MSI files, very complex, overkill for this project
- **Advanced Installer**: Commercial, GUI-based, not suitable for open-source

### Inno Setup Script Structure

```iss
; LMU_Telemetry_Logger_Setup.iss

[Setup]
AppName=LMU Telemetry Logger
AppVersion=1.0.0
AppPublisher=Your Name/Organization
AppPublisherURL=https://github.com/yourusername/lmu-telemetry-logger
DefaultDirName={autopf}\LMU Telemetry Logger
DefaultGroupName=LMU Telemetry Logger
OutputDir=installer_output
OutputBaseFilename=LMU_Telemetry_Logger_Setup_v1.0.0
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\LMU_Telemetry_Logger.exe
LicenseFile=LICENSE
WizardStyle=modern

[Files]
; Main executable
Source: "dist\LMU_Telemetry_Logger.exe"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "USER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; Default config (only install if doesn't exist)
Source: "config_default.json"; DestDir: "{app}"; DestName: "config.json"; Flags: onlyifdoesntexist

[Dirs]
; Create output directory in user's Documents
Name: "{userdocs}\LMU Telemetry"; Permissions: users-modify

[Icons]
; Start Menu shortcuts
Name: "{group}\LMU Telemetry Logger"; Filename: "{app}\LMU_Telemetry_Logger.exe"
Name: "{group}\Open Output Folder"; Filename: "{userdocs}\LMU Telemetry"
Name: "{group}\User Guide"; Filename: "{app}\USER_GUIDE.md"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"

; Optional desktop shortcut
Name: "{autodesktop}\LMU Telemetry Logger"; Filename: "{app}\LMU_Telemetry_Logger.exe"; Tasks: desktopicon

[Tasks]
; Optional tasks user can select
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "autostart"; Description: "Start with Windows"; GroupDescription: "Startup options:"; Flags: unchecked

[Registry]
; Add to Windows startup (if user selected)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "LMU Telemetry Logger"; ValueData: "{app}\LMU_Telemetry_Logger.exe"; Flags: uninsdeletevalue; Tasks: autostart

; Store installation info for future upgrades
Root: HKCU; Subkey: "Software\LMU Telemetry Logger"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\LMU Telemetry Logger"; ValueType: string; ValueName: "Version"; ValueData: "1.0.0"

[Code]
// Pascal script for custom behavior

// Function to check if upgrading
function IsUpgrade(): Boolean;
var
  InstallPath: String;
begin
  Result := RegQueryStringValue(HKCU, 'Software\LMU Telemetry Logger', 'InstallPath', InstallPath);
end;

// Custom page to set output directory
var
  OutputDirPage: TInputDirWizardPage;

procedure InitializeWizard;
begin
  // Create custom page for output directory
  OutputDirPage := CreateInputDirPage(wpSelectDir,
    'Select Telemetry Output Directory',
    'Where should telemetry files be saved?',
    'Select the folder where you want telemetry CSV files to be saved, then click Next.',
    False, '');
  OutputDirPage.Add('');
  OutputDirPage.Values[0] := ExpandConstant('{userdocs}\LMU Telemetry');
end;

// Update config.json with user's chosen output directory
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  ConfigContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigFile := ExpandConstant('{app}\config.json');
    // Load config.json and update output_dir
    // (Simplified - actual implementation would parse JSON properly)
    // Or use external Python script to update config
  end;
end;

// Custom uninstall confirmation
function UninstallPrompt(): Boolean;
begin
  Result := MsgBox('Do you also want to delete your telemetry data and settings?' + #13#10 +
                   'Choose No to keep your data.',
                   mbConfirmation, MB_YESNO) = IDYES;
end;

[UninstallDelete]
; Only delete data if user confirms
Type: filesandordirs; Name: "{userdocs}\LMU Telemetry"; Check: UninstallPrompt
Type: files; Name: "{app}\config.json"; Check: UninstallPrompt

[Run]
; Option to launch app after installation
Filename: "{app}\LMU_Telemetry_Logger.exe"; Description: "Launch LMU Telemetry Logger"; Flags: nowait postinstall skipifsilent
```

### Default Configuration File

Create `config_default.json` with sensible defaults:

```json
{
  "output_dir": "%USERPROFILE%\\Documents\\LMU Telemetry",
  "target_process": "LMU.exe",
  "poll_interval": 0.01,
  "track_opponents": false,
  "filename_format": "{session_id}_lap{lap}.csv"
}
```

Note: The installer script will replace `%USERPROFILE%` with the actual path during installation.

### Build Process Integration

Update `build.bat` or create `build_installer.bat`:

```batch
@echo off
REM Build the executable first
call build.bat

REM Build the installer (requires Inno Setup installed)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\LMU_Telemetry_Logger_Setup.iss

echo.
echo Installer created: installer\output\LMU_Telemetry_Logger_Setup_v1.0.0.exe
pause
```

## Testing Requirements

### Manual Testing Checklist

**Fresh Installation:**
- [ ] Download installer .exe
- [ ] Run installer, verify welcome screen
- [ ] Accept license, verify it displays correctly
- [ ] Choose installation directory (test custom path)
- [ ] Select optional tasks (desktop shortcut, auto-start)
- [ ] Verify installation completes without errors
- [ ] Verify Start Menu shortcuts created
- [ ] Verify desktop shortcut created (if selected)
- [ ] Verify output directory created in Documents
- [ ] Launch app from Start Menu
- [ ] Verify app runs correctly
- [ ] Generate a test telemetry file
- [ ] Verify file saved to correct output directory

**Upgrade Installation:**
- [ ] Install v1.0.0
- [ ] Modify config.json with custom settings
- [ ] Generate some telemetry files
- [ ] Run v1.1.0 installer
- [ ] Verify "Upgrade" messaging shown
- [ ] Verify config.json preserved with user settings
- [ ] Verify existing telemetry files not deleted
- [ ] Verify app runs with new version

**Uninstallation:**
- [ ] Open Windows Settings → Apps
- [ ] Find "LMU Telemetry Logger" in list
- [ ] Click Uninstall
- [ ] Verify uninstall wizard appears
- [ ] Choose to delete data (test both Yes/No)
- [ ] Verify app files removed
- [ ] Verify Start Menu shortcuts removed
- [ ] Verify desktop shortcut removed (if it existed)
- [ ] If chose Yes: verify telemetry data deleted
- [ ] If chose No: verify telemetry data preserved
- [ ] Verify registry entries cleaned up

**Auto-Start:**
- [ ] Fresh install with "Start with Windows" checked
- [ ] Restart computer
- [ ] Verify app launches automatically
- [ ] Verify system tray icon appears
- [ ] Disable auto-start (via Settings UI or uninstall/reinstall)
- [ ] Restart computer
- [ ] Verify app does NOT launch

**Edge Cases:**
- [ ] Install without admin privileges (should work - uses user directories)
- [ ] Install with very long custom path
- [ ] Install on Windows 10 (minimum supported version)
- [ ] Install on Windows 11
- [ ] Install when app is already running (should prompt to close)
- [ ] Uninstall when app is running (should prompt to close)

### Automated Testing

**Pre-build Validation:**
- Script to validate Inno Setup script syntax
- Verify all referenced files exist (exe, docs, etc.)

**Post-build Validation:**
- Silent install test: `Setup.exe /SILENT /DIR="C:\Test"`
- Verify installation completed
- Verify files copied correctly
- Silent uninstall test: `unins000.exe /SILENT`
- Verify clean removal

## Dependencies

### Development Dependencies
- **Inno Setup 6**: Download from https://jrsoftware.org/isdl.php
  - Free download, ~2 MB installer
  - Install on development machine (Windows only)
  - Command-line compiler: `ISCC.exe`

### Runtime Dependencies
- None (all dependencies bundled in PyInstaller .exe)

## Files to Create

```
installer/
├── LMU_Telemetry_Logger_Setup.iss    # Main Inno Setup script
├── config_default.json                # Default configuration template
├── icon.ico                           # App icon (if not already in project)
└── output/                            # Generated installers output here
    └── LMU_Telemetry_Logger_Setup_v1.0.0.exe
```

**Additional Files:**
- `build_installer.bat` - Build script for installer
- `installer/README.md` - Instructions for building installer
- Update `USER_GUIDE.md` - Add installation section

## Files to Modify

- `build.bat` - Update to mention installer build process
- `USER_GUIDE.md` - Add "Installation" section
- `.gitignore` - Ignore installer output directory
- `CLAUDE.md` - Update Phase 7 checklist

## Implementation Steps

### Phase 1: Setup & Basic Installer (2-3 hours)

1. **Install Inno Setup**
   - Download and install Inno Setup 6
   - Verify `ISCC.exe` in PATH or note location

2. **Create installer directory structure**
   - Create `installer/` folder
   - Create `config_default.json`
   - Copy app icon if needed

3. **Create basic Inno Setup script**
   - Start with minimal working script
   - Install exe only
   - Test successful build and installation

4. **Test basic install/uninstall**
   - Build installer
   - Run installer on test machine
   - Verify exe copied
   - Test uninstall

### Phase 2: Shortcuts & Registry (2-3 hours)

1. **Add Start Menu shortcuts**
   - Launch app shortcut
   - Open Output Folder shortcut
   - Uninstall shortcut

2. **Add registry entries**
   - Installation path
   - Version number
   - Add/Remove Programs integration

3. **Test shortcuts**
   - Verify all shortcuts work
   - Test uninstall removes shortcuts

### Phase 3: Configuration & Directories (2-3 hours)

1. **Create output directory**
   - Add `[Dirs]` section
   - Create `Documents\LMU Telemetry`
   - Set proper permissions

2. **Install default config**
   - Copy `config_default.json` → `config.json`
   - Only if doesn't exist (preserve on upgrade)

3. **Add custom output directory page**
   - Implement `InitializeWizard` procedure
   - Let user choose telemetry output location
   - Update config.json with choice

### Phase 4: Optional Features (2-4 hours)

1. **Desktop shortcut task**
   - Add optional task
   - Create shortcut only if selected

2. **Auto-start with Windows**
   - Add optional task
   - Add registry entry if selected

3. **Upgrade detection**
   - Check for existing installation
   - Preserve config.json
   - Show upgrade messaging

### Phase 5: Polish & Testing (3-5 hours)

1. **Add User Guide to install**
   - Copy `USER_GUIDE.md`
   - Add Start Menu shortcut to guide

2. **Uninstall data preservation**
   - Prompt user about keeping data
   - Conditionally delete telemetry files

3. **Build script automation**
   - Create `build_installer.bat`
   - Integrate with existing build process

4. **Comprehensive testing**
   - Test all scenarios above
   - Test on fresh Windows 10/11 VMs
   - Document any issues

### Phase 6: Documentation (1-2 hours)

1. **Update USER_GUIDE.md**
   - Add "Installation" section
   - Include screenshots of installer
   - Document Start Menu shortcuts

2. **Create installer README**
   - How to build installer
   - Prerequisites (Inno Setup)
   - Build commands

3. **Update CLAUDE.md**
   - Mark Phase 7 installer task complete
   - Add installer to file listing

## Acceptance Criteria

**Installation:**
- [ ] Installer .exe runs without errors
- [ ] Welcome screen shows app name and version
- [ ] License displays correctly
- [ ] User can choose installation directory
- [ ] Default output directory created in Documents
- [ ] Start Menu shortcuts created and working
- [ ] Desktop shortcut created (if selected)
- [ ] Auto-start registry entry added (if selected)
- [ ] config.json created with correct defaults
- [ ] App appears in Windows "Programs and Features"
- [ ] "Launch application" checkbox works

**Upgrade:**
- [ ] Installer detects existing installation
- [ ] User's config.json preserved
- [ ] Existing telemetry data not deleted
- [ ] Version number updated in registry

**Uninstallation:**
- [ ] Uninstaller accessible from Start Menu and Windows Settings
- [ ] User prompted about keeping data
- [ ] App files removed correctly
- [ ] Shortcuts removed
- [ ] Registry entries cleaned up
- [ ] Telemetry data preserved/deleted based on user choice

**Quality:**
- [ ] Installer size reasonable (<10 MB)
- [ ] No antivirus false positives
- [ ] Works on Windows 10 and 11
- [ ] Silent install works: `/SILENT /DIR="path"`
- [ ] Silent uninstall works: `/SILENT`
- [ ] Professional appearance (modern wizard style)

## Installation Size Breakdown

Estimated installed size: ~40-50 MB

- `LMU_Telemetry_Logger.exe`: ~35 MB (PyInstaller bundle)
- `config.json`: <1 KB
- `USER_GUIDE.md`: ~10 KB
- `LICENSE`: ~1 KB
- Shortcuts/Registry: negligible

Installer size: ~8-10 MB (compressed with LZMA2)

## Versioning Strategy

**Format**: `MAJOR.MINOR.PATCH` (Semantic Versioning)

**Installer Filename**:
```
LMU_Telemetry_Logger_Setup_v1.0.0.exe
LMU_Telemetry_Logger_Setup_v1.1.0.exe
LMU_Telemetry_Logger_Setup_v2.0.0.exe
```

**Version Sources**:
1. Inno Setup script: `AppVersion=1.0.0`
2. Python app: Update `__version__` in main module
3. Build script: Could read from single source file

**Upgrade Path**:
- Installer checks registry for existing version
- Compares with current installer version
- Shows "Upgrade from v1.0.0 to v1.1.0" messaging
- Preserves user data by default

## Notes

### Inno Setup Advantages
- **Free**: No licensing costs
- **Mature**: 25+ years of development, very stable
- **Professional**: Used by many major applications
- **Small**: Installers are highly compressed
- **Scriptable**: Easy to customize and version control
- **Well-documented**: Excellent documentation and examples

### Windows Compatibility
- Minimum: Windows 10 (2015+)
- Tested: Windows 10, Windows 11
- Architecture: 64-bit only (matches PyInstaller build)

### Code Signing (Future Enhancement)
Current: Unsigned installer
- May show Windows SmartScreen warning
- Users must click "More info" → "Run anyway"
- This is normal for open-source software without code signing certificate

Future: Code signing certificate
- Cost: ~$100-300/year
- Eliminates SmartScreen warnings
- Required for: EV certificates can skip reputation check

### Distribution
Once installer is built:
1. Upload to GitHub Releases
2. Provide direct download link
3. Include SHA256 checksum for security
4. Optionally: Host on project website

## Related Features

- `feature_auto_update.md` - Auto-update feature (could check for new installer versions)
- `feature_settings_ui.md` - Settings UI (already implemented, installer includes it)
- Phase 7 in `CLAUDE.md` - Distribution and packaging

## References

- **Inno Setup**: https://jrsoftware.org/isinfo.php
- **Documentation**: https://jrsoftware.org/ishelp/
- **Examples**: `C:\Program Files (x86)\Inno Setup 6\Examples\`
- **PyInstaller + Inno Setup**: Common pattern, many examples online

## Estimated Total Time

- **Phase 1**: 2-3 hours (basic installer)
- **Phase 2**: 2-3 hours (shortcuts & registry)
- **Phase 3**: 2-3 hours (configuration)
- **Phase 4**: 2-4 hours (optional features)
- **Phase 5**: 3-5 hours (polish & testing)
- **Phase 6**: 1-2 hours (documentation)

**Total**: 12-20 hours depending on complexity and testing thoroughness

## Success Metrics

Post-implementation, we should see:
- ✅ 90%+ of users successfully install without issues
- ✅ Zero manual configuration required for basic usage
- ✅ Clean uninstall with no leftover files (except user data if requested)
- ✅ Professional appearance matching Windows installer conventions
- ✅ Positive user feedback about installation experience
